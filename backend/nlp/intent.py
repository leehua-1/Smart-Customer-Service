"""
零样本意图识别
- 复用 BGE 句向量模型
- 将用户输入与预定义的意图描述做语义匹配
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = 'BAAI/bge-base-zh-v1.5'

# 意图定义：key 是意图标签，value 是语义描述（可多个）
INTENT_DESCRIPTIONS = {
    'greeting': [
        '问候语，打招呼，你好',
    ],
    'order_query': [
        '查询订单状态，订单进度，订单到哪里了',
    ],
    'logistics': [
        '查询物流信息，快递进度，什么时候送到',
    ],
    'refund_return': [
        '退货，换货，退款，申请售后',
    ],
    'product_info': [
        '咨询产品信息，产品功能，产品价格',
    ],
    'complaint': [
        '投诉，抱怨，表达不满，服务质量差',
    ],
    'account': [
        '账户问题，密码，登录，绑定手机号',
    ],
    'payment': [
        '支付问题，付款失败，扣款异常',
    ],
    'human_agent': [
        '转人工，找人工客服，联系真人',
    ],
    'thanks': [
        '表达感谢，谢谢',
    ],
    'farewell': [
        '告别，再见，结束对话',
    ],
    'cancel': [
    '取消操作，取消订单，我要取消',
    '算了不问了，退出，结束',
    ],
}


class IntentClassifier:
    """零样本意图分类器"""

    def __init__(self):
        print('加载意图识别模型...')
        self.model = SentenceTransformer(MODEL_NAME)

        # 把所有意图描述编码为向量，构建意图向量库
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
        """
        返回 (意图标签, 置信度)
        置信度低于阈值时返回 ('unknown', 分数)
        """
        vec = self.model.encode([query], normalize_embeddings=True)
        # 余弦相似度（向量已归一化，内积即为余弦相似度）
        scores = np.dot(self.intent_vectors, vec[0])
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        best_label = self.intent_labels[best_idx]

        # 阈值可调，低于此值认为意图不明确
        if best_score < 0.5:
            return 'unknown', best_score

        return best_label, best_score


# ---------- 单例 ----------
_classifier_instance = None


def get_intent_classifier():
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
    return _classifier_instance


if __name__ == '__main__':
    clf = get_intent_classifier()

    test_queries = [
        '你好',
        '我的订单到哪了',
        '怎么退货',
        '我要投诉',
        '转人工',
        '谢谢',
        '你们有什么产品',
        '今天天气怎么样',
    ]

    for q in test_queries:
        label, score = clf.predict(q)
        print(f'{q:15s} → {label:15s} ({score:.3f})')