"""
零样本意图识别
- 复用 BGE 句向量模型
- 支持 Top-K 候选和相对判定仲裁
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = 'BAAI/bge-base-zh-v1.5'

# 意图定义：每个意图多条描述，覆盖真实用户表达
INTENT_DESCRIPTIONS = {
    'greeting': [
        '问候语，打招呼，你好',
        '在吗，有人吗',
        '嗨，您好',
    ],
    'order_query': [
        '查询订单状态，订单进度，订单到哪里了',
        '看看我的订单，订单现在什么情况',
        '订单查询，订单什么时候到',
        '我的订单怎么样了',
    ],
    'logistics': [
        '查询物流信息，快递进度，什么时候送到',
        '快递到哪了，为什么还没到',
        '物流信息，发货了吗',
        '什么时候能收到',
    ],
    'refund_return': [
        '退货，换货，退款，申请售后',
        '我要退，怎么退',
        '退钱，申请退款',
        '商品不合适想退货',
    ],
    'product_info': [
        '咨询产品信息，产品功能，产品价格',
        '有什么产品，价格多少',
        '这个产品怎么样',
        '介绍下产品',
    ],
    'complaint': [
        '投诉，抱怨，表达不满，服务质量差',
        '服务太差了，我要投诉',
        '什么垃圾服务',
        '我要投诉你们',
    ],
    'account': [
        '账户问题，密码，登录，绑定手机号',
        '改密码，账号异常',
        '登不上，忘记密码',
        '账号被锁了',
    ],
    'payment': [
        '支付问题，付款失败，扣款异常',
        '付不了款，支付出问题',
        '钱扣了但没到账',
        '支付失败',
    ],
    'human_agent': [
        '转人工，找人工客服，联系真人',
        '和真人说话，人工服务',
        '我要找客服',
        '有没有人工',
    ],
    'thanks': [
        '表达感谢，谢谢',
        '感谢，辛苦了',
        '谢了',
    ],
    'farewell': [
        '告别，再见，结束对话',
        '拜拜，下次再聊',
        '没别的事了',
    ],
    'cancel': [
        '取消操作，取消订单，我要取消',
        '算了不问了，退出，结束',
        '不需要了，不用了',
        '我不需要了',
        '不想弄了',
        '不弄了，算了',
    ],
}


class IntentClassifier:
    """零样本意图分类器"""

    def __init__(self):
        print('加载意图识别模型...')
        self.model = SentenceTransformer(MODEL_NAME)

        self.intent_labels = []
        descriptions = []
        for label, descs in INTENT_DESCRIPTIONS.items():
            for d in descs:
                self.intent_labels.append(label)
                descriptions.append(d)

        self.intent_vectors = self.model.encode(
            descriptions, normalize_embeddings=True
        )
        print(f'意图分类器就绪，共 {len(INTENT_DESCRIPTIONS)} 类意图')

    def predict(self, query):
        """返回 (意图, 分数)，分数低于 0.5 视为 unknown"""
        vec = self.model.encode([query], normalize_embeddings=True)
        scores = np.dot(self.intent_vectors, vec[0])
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        best_label = self.intent_labels[best_idx]

        if best_score < 0.5:
            return 'unknown', best_score
        return best_label, best_score

    def predict_topk(self, query, k=3):
        """返回 Top-K 候选意图及分数，同意图只保留最高分"""
        vec = self.model.encode([query], normalize_embeddings=True)
        scores = np.dot(self.intent_vectors, vec[0])
        sorted_indices = np.argsort(scores)[::-1]

        results = []
        seen_labels = set()
        for idx in sorted_indices:
            label = self.intent_labels[idx]
            if label in seen_labels:
                continue
            seen_labels.add(label)
            results.append((label, float(scores[idx])))
            if len(results) >= k:
                break
        return results

    def arbitrate(self, query, current_intent='', missing_slots=None):
        """
        相对判定仲裁：结合 Top-1/Top-2 差距和上下文，决定最终意图
        增加：本地大模型兜底（BGE 置信度不足时）
        """
        missing_slots = missing_slots or []
        candidates = self.predict_topk(query, k=3)

        if not candidates:
            return current_intent, False, False

        top1_intent, top1_score = candidates[0]
        top2_intent, top2_score = candidates[1] if len(candidates) > 1 else ('', 0.0)
        gap = top1_score - top2_score

        # 判断本地置信度是否足够（分数高，或者分数中等但拉开差距）
        local_confident = (top1_score > 0.75 or (top1_score > 0.6 and gap > 0.1))

        # ---------- 本地置信度不足，调用本地大模型 ----------
        if not local_confident:
            try:
                from nlp.local_llm import get_local_llm
                llm = get_local_llm()
                if llm.is_available():
                    print(f'[arbitrate] BGE 置信度不足(top1={top1_score:.2f}, gap={gap:.2f})，调用本地大模型')
                    ai_intent, ai_score, _ = llm.classify_intent(
                        query,
                        list(INTENT_DESCRIPTIONS.keys())
                    )
                    if ai_intent != 'unknown' and ai_score > 0.7:
                        print(f'[arbitrate] 大模型判定: {ai_intent} ({ai_score:.2f})')
                        
                        # 大模型结果直接决定行为
                        if ai_intent == 'cancel':
                            # 追问自由文本槽位时，必须极高分才取消
                            if missing_slots and missing_slots[0] in ('reason', 'description'):
                                if ai_score > 0.85:
                                    return 'cancel', False, True
                                return current_intent, False, False
                            return 'cancel', False, True

                        # 在追问状态，且问的是订单号，如果里面有数字，保持当前意图填槽
                        if missing_slots and missing_slots[0] == 'order_id':
                            import re
                            if re.search(r'\d{8,20}', query):
                                return current_intent, False, False
                        
                        # 自由文本槽位追问时，大模型如果判定是别的业务意图，不打断追问
                        if missing_slots and missing_slots[0] in ('reason', 'description'):
                            return current_intent, False, False

                        # 正常意图切换
                        if ai_intent != current_intent:
                            return ai_intent, True, False
                        return current_intent, False, False
            except Exception as e:
                print(f'[arbitrate] 大模型调用异常: {e}')

        # ---------- 原版相对判定逻辑（BGE 置信度足够时走这里）----------
        if missing_slots and missing_slots[0] in ('reason', 'description'):
            if top1_intent == 'cancel' and gap > 0.15 and top1_score > 0.65:
                return 'cancel', False, True
            return current_intent, False, False

        if missing_slots and missing_slots[0] == 'order_id':
            import re
            if re.search(r'\d{8,20}', query):
                if top1_intent == 'cancel' and gap > 0.15 and top1_score > 0.65:
                    return 'cancel', False, True
                return current_intent, False, False

        if not current_intent or current_intent == 'unknown':
            if gap > 0.08 and top1_score > 0.55:
                return top1_intent, True, top1_intent == 'cancel'
            return current_intent, False, False

        if top1_intent == current_intent:
            return current_intent, False, False

        if gap > 0.08 and top1_score > 0.55:
            return top1_intent, True, top1_intent == 'cancel'

        return current_intent, False, False


_classifier_instance = None


def get_intent_classifier():
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
    return _classifier_instance


if __name__ == '__main__':
    clf = get_intent_classifier()

    print('\n===== 基础意图识别 =====')
    for q in ['你好', '我的订单到哪了', '怎么退货', '我要投诉', '转人工', '谢谢']:
        print(f'{q:15s} -> {clf.predict_topk(q, 3)}')

    print('\n===== 无当前意图下的判定 =====')
    for q in ['我要退货', '什么破服务', '不合适', '算了不用了']:
        intent, switched, cancel = clf.arbitrate(q)
        print(f'{q:15s} -> 意图={intent:15s} 切换={switched} 取消={cancel}')

    print('\n===== 追问 reason 状态下 =====')
    for q in ['不合适', '我不需要了', '算了不用了', '太慢了不要了', '因为质量太差']:
        intent, switched, cancel = clf.arbitrate(q, current_intent='refund_return', missing_slots=['reason'])
        print(f'{q:15s} -> 意图={intent:15s} 切换={switched} 取消={cancel}')

    print('\n===== 追问 order_id 状态下 =====')
    for q in ['订单 1234567890123', '不要了', '太慢了']:
        intent, switched, cancel = clf.arbitrate(q, current_intent='refund_return', missing_slots=['order_id'])
        print(f'{q:15s} -> 意图={intent:15s} 切换={switched} 取消={cancel}')