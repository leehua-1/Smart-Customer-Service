"""
多轮对话管理器
- 维护每个 session 的对话状态
- 意图识别 → 实体抽取 → 槽位填充 → 追问或执行
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from nlp.intent import get_intent_classifier
from nlp.entity import extract_entities


# ---------- 意图-槽位映射 ----------
INTENT_SLOTS = {
    'order_query': ['order_id'],
    'logistics': ['order_id'],
    'refund_return': ['order_id', 'reason'],
    'complaint': ['order_id', 'description'],
    'payment': ['order_id'],
    'account': [],
    'human_agent': [],
    'greeting': [],
    'thanks': [],
    'farewell': [],
    'product_info': [],
    'cancel': [],                # 新增：取消意图
    'unknown': [],
}

# 自由文本槽位：无法用正则实体提取，需要用整句填充
FREE_TEXT_SLOTS = ('reason', 'description')

# ---------- 槽位追问模板 ----------
SLOT_QUESTIONS = {
    'order_id': '请提供您的订单号，我帮您查询。',
    'reason': '请说明退货原因，方便我为您处理。',
    'description': '请描述您遇到的具体问题。',
}

# ---------- 各意图的完成回复模板 ----------
INTENT_COMPLETION = {
    'order_query': '您的订单 {order_id} 正在运输中，预计明天送达。',
    'logistics': '您的订单 {order_id} 物流信息：已到达本地分拨中心，预计明天派送。',
    'refund_return': '已收到您的退货申请（订单 {order_id}，原因：{reason}），我们会尽快处理。',
    'complaint': '已记录您的投诉（订单 {order_id}，问题：{description}），客服会在 24 小时内联系您。',
    'payment': '已查询订单 {order_id} 的支付状态，支付成功，请放心。',
}


def handle_turn(session_id, user_input):
    from chat.models import DialogueState

    state, _ = DialogueState.objects.get_or_create(session_id=session_id)

    # 1. 意图识别
    intent_clf = get_intent_classifier()
    intent, intent_score = intent_clf.predict(user_input)

    # 2. 检查是否处于追问状态
    required = INTENT_SLOTS.get(state.current_intent, [])
    missing = [s for s in required if not state.slots.get(s)]

    # 3. cancel 优先处理，但只在非追问状态，或追问的是非自由文本槽位时
    if intent == 'cancel' and intent_score > 0.75:
        if not missing or missing[0] not in FREE_TEXT_SLOTS:
            state.current_intent = ''
            state.slots = {}
            state.turn_count += 1
            state.last_input = user_input
            state.save()
            return '好的，已为您取消当前操作。', state

    # 4. 实体抽取
    entities = extract_entities(user_input)

    # 5. P0 修复：实体覆盖槽位
    if not missing and intent == state.current_intent:
        for k, v in entities.items():
            if k in required:
                state.slots[k] = v[0] if isinstance(v, list) and v else v

    # 6. 追问或切换
    if missing:
        _handle_followup(state, user_input, intent, intent_score, entities, missing)
    else:
        _switch_intent(state, intent, entities)

    # 7. 重算缺失
    required = INTENT_SLOTS.get(state.current_intent, [])
    missing = [s for s in required if not state.slots.get(s)]

    # 8. 生成回复
    if not state.current_intent or state.current_intent == 'unknown':
        reply = '抱歉，我没有完全理解您的问题。您可以换个说法，或输入“转人工”联系客服。'
    elif missing:
        reply = SLOT_QUESTIONS.get(missing[0], '请补充更多信息。')
    else:
        reply = execute_intent(state, user_input)

    # 9. 更新状态
    state.turn_count += 1
    state.last_input = user_input
    state.save()

    return reply, state


def _handle_followup(state, user_input, intent, intent_score, entities, missing):
    """处理追问状态下的用户输入"""
    target_slot = missing[0]
    required = INTENT_SLOTS.get(state.current_intent, [])

    # 情况 A：目标槽位能被实体直接填充
    if target_slot in entities:
        value = entities[target_slot]
        state.slots[target_slot] = value[0] if isinstance(value, list) and value else value

        # 同时把其他属于当前意图的实体也填上
        for k, v in entities.items():
            if k in required and k != target_slot:
                state.slots[k] = v[0] if isinstance(v, list) and v else v
        return

    # 情况 B：目标槽位是自由文本（reason / description）
    if target_slot in FREE_TEXT_SLOTS:
        has_other_slot = any(k in entities for k in required if k != target_slot)

        if has_other_slot:
            # 本轮提供了其他槽位的信息，先填上，继续追问当前槽位
            for k, v in entities.items():
                if k in required:
                    state.slots[k] = v[0] if isinstance(v, list) and v else v
            return

        # 若本轮无实体、且新意图置信度极高，才允许切换意图
        if (not entities
                and intent_score > 0.85
                and intent not in ('unknown', state.current_intent)):
            _switch_intent(state, intent, entities)
            return

        # 否则把整句作为自由文本槽位的回答
        state.slots[target_slot] = user_input
        return

    # 情况 C：其他槽位，尝试切换意图
    _switch_intent(state, intent, entities)


def _switch_intent(state, intent, entities):
    """切换意图并清理无关槽位"""
    if intent in ('unknown', '') or intent == state.current_intent:
        return

    new_required = INTENT_SLOTS.get(intent, [])
    state.slots = {k: v for k, v in state.slots.items() if k in new_required}
    state.current_intent = intent

    # 把本轮实体填进新意图的槽位
    for k, v in entities.items():
        if k in new_required:
            state.slots[k] = v[0] if isinstance(v, list) and v else v


def execute_intent(state, user_input=''):
    """槽位齐全后执行具体动作"""
    intent = state.current_intent
    slots = state.slots

    template = INTENT_COMPLETION.get(intent)
    if template:
        try:
            return template.format(**slots)
        except KeyError as e:
            return f'处理时缺少信息：{e}'

    # 未定义完成模板的意图，走 FAQ 检索兜底
    from nlp.retrieve import get_retriever
    retriever = get_retriever()
    query = user_input or state.last_input
    answer = retriever.best_answer(query, threshold=0.6)
    return answer or '已收到您的请求，我们会尽快处理。'


def reset_state(session_id):
    """重置会话状态（用于测试或用户主动清空）"""
    from chat.models import DialogueState
    DialogueState.objects.filter(session_id=session_id).delete()


# ---------- 本地测试 ----------
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()

    session = 'test-session-001'
    reset_state(session)

    test_dialogue = [
        '我要退货',              # 切 refund_return，缺 order_id
        '订单 1234567890123',    # 填 order_id，缺 reason
        '不合适',                # 填 reason，完成
        '订单 1234567891011',    # 覆盖 order_id（测试 P0）
    ]

    for user_input in test_dialogue:
        reply, state = handle_turn(session, user_input)
        print(f'用户：{user_input}')
        print(f'AI  ：{reply}')
        print(f'     [意图={state.current_intent}, 槽位={state.slots}, 轮次={state.turn_count}]')
        print()