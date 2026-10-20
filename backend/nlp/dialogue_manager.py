"""
多轮对话管理器
- 维护每个 session 的对话状态
- 用仲裁器判定意图，槽位填充后追问或执行
- 支持人工接管（is_human_mode）
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
    'cancel': [],
    'unknown': [],
}

# 自由文本槽位
FREE_TEXT_SLOTS = ('reason', 'description')

# 槽位追问模板
SLOT_QUESTIONS = {
    'order_id': '请提供您的订单号，我帮您查询。',
    'reason': '请说明退货原因，方便我为您处理。',
    'description': '请描述您遇到的具体问题。',
}

# 意图完成回复模板
INTENT_COMPLETION = {
    'order_query': '您的订单 {order_id} 正在运输中，预计明天送达。',
    'logistics': '您的订单 {order_id} 物流信息：已到达本地分拨中心，预计明天派送。',
    'refund_return': '已收到您的退货申请（订单 {order_id}，原因：{reason}），我们会尽快处理。',
    'complaint': '已记录您的投诉（订单 {order_id}，问题：{description}），客服会在 24 小时内联系您。',
    'payment': '已查询订单 {order_id} 的支付状态，支付成功，请放心。',
    'human_agent': '正在为您转接人工客服，请稍等片刻...',
}


def handle_turn(session_id, user_input):
    """
    处理一轮对话
    返回 (reply, state)
    """
    from chat.models import DialogueState, ChatLog

    state, _ = DialogueState.objects.get_or_create(session_id=session_id)

    # ---------- 拦截：当前处于人工模式 ----------
    if state.is_human_mode:
        ChatLog.objects.create(
            session_id=session_id,
            user_input=user_input,
            bot_reply='[等待人工回复]',
            intent='human_agent',
            emotion='',
            entities={}
        )
        return '人工客服正在赶来，请稍等片刻哦~（您正在排队中）', state
    # -----------------------------------------

    intent_clf = get_intent_classifier()
    entities = extract_entities(user_input)

    # 计算当前意图缺失的槽位
    required = INTENT_SLOTS.get(state.current_intent, [])
    missing = [s for s in required if not state.slots.get(s)]

    # 用仲裁器判定意图
    final_intent, switched, is_cancel = intent_clf.arbitrate(
        query=user_input,
        current_intent=state.current_intent,
        missing_slots=missing
    )

    # 分支 1：取消
    if is_cancel:
        state.current_intent = ''
        state.slots = {}
        reply = '好的，已为您取消当前操作。'

    # 分支 2：切换意图
    elif switched:
        _switch_intent(state, final_intent, entities)
        
        # 如果切换到了人工客服，开启人工接管模式
        if state.current_intent == 'human_agent':
            state.is_human_mode = True
            state.save()
            reply = '正在为您转接人工客服，请稍等片刻...'
        else:
            reply = _next_reply(state, user_input)

    # 分支 3：保持当前意图，填槽或追问
    else:
        if missing:
            target_slot = missing[0]
            if target_slot in entities:
                value = entities[target_slot]
                state.slots[target_slot] = value[0] if isinstance(value, list) and value else value
            elif target_slot in FREE_TEXT_SLOTS:
                state.slots[target_slot] = user_input
        else:
            # 覆盖已填槽位（P0 修复）
            for k, v in entities.items():
                if k in required:
                    state.slots[k] = v[0] if isinstance(v, list) and v else v

        reply = _next_reply(state, user_input)

    state.turn_count += 1
    state.last_input = user_input
    state.save()

    return reply, state


def _next_reply(state, user_input):
    """根据当前状态生成回复"""
    required = INTENT_SLOTS.get(state.current_intent, [])
    missing = [s for s in required if not state.slots.get(s)]

    if not state.current_intent or state.current_intent == 'unknown':
        return '抱歉，我没有完全理解您的问题。您可以换个说法，或输入“转人工”联系客服。'

    if missing:
        # 如果追问的是订单号，但用户发了一大段抱怨的话（没数字）
        if missing[0] == 'order_id' and len(user_input) > 8:
            import re
            if not re.search(r'\d', user_input):
                return '非常理解您的焦急。为了更快解决您的问题，请提供一下订单号，或者输入“转人工”。'
                
        return SLOT_QUESTIONS.get(missing[0], '请补充更多信息。')

    return execute_intent(state, user_input)


def _switch_intent(state, intent, entities):
    """切换意图并清理无关槽位"""
    if intent in ('unknown', '') or intent == state.current_intent:
        return

    new_required = INTENT_SLOTS.get(intent, [])
    state.slots = {k: v for k, v in state.slots.items() if k in new_required}
    state.current_intent = intent

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
    """重置会话状态"""
    from chat.models import DialogueState
    DialogueState.objects.filter(session_id=session_id).delete()


# ---------- 本地测试 ----------
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()

    def run_scenario(name, session, dialogue):
        print(f'\n===== {name} =====')
        reset_state(session)
        for user_input in dialogue:
            reply, state = handle_turn(session, user_input)
            print(f'用户：{user_input}')
            print(f'AI  ：{reply}')
            print(f'     [意图={state.current_intent}, 槽位={state.slots}, 轮次={state.turn_count}, 人工模式={state.is_human_mode}]')

    run_scenario('场景 1：完整退货', 'test-1',
                 ['我要退货', '订单 1234567890123', '不合适'])
    run_scenario('场景 2：追问取消', 'test-2',
                 ['我要退货', '我不需要了'])
    run_scenario('场景 3：订单覆盖', 'test-3',
                 ['订单 1234567890123 到哪了', '订单 1234567891011'])
    run_scenario('场景 4：复合表达', 'test-4',
                 ['订单 1234567890123 到哪了', '太慢了不要了'])
    
    # 新增场景：转人工
    run_scenario('场景 5：转人工拦截', 'test-5',
                 ['有没有真人客服', '人呢', '快点啊'])