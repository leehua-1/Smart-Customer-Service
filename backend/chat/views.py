import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChatLog
from nlp.intent import get_intent_classifier
from nlp.emotion import get_emotion_classifier
from nlp.entity import extract_entities
from nlp.dialogue_manager import handle_turn


EMOTION_PREFIX = {
    'anger': '非常抱歉给您带来不好的体验。',
    'confusion': '我来为您详细说明：',
    'satisfaction': '',
    'neutral': '',
}


@api_view(['POST'])
def chat(request):
    user_input = request.data.get('message', '').strip()
    session_id = request.data.get('session_id') or str(uuid.uuid4())

    if not user_input:
        return Response({'error': '消息不能为空'}, status=400)

    # 1. 情感分析（用于回复前缀）
    emotion_clf = get_emotion_classifier()
    emotion, _ = emotion_clf.predict(user_input)

    # 2. 走多轮对话管理器（内部已经处理了人工模式拦截）
    reply, state = handle_turn(session_id, user_input)

    # 3. 情绪前缀（注意：人工模式排队中就不加前缀了）
    if not state.is_human_mode:
        prefix = EMOTION_PREFIX.get(emotion, '')
        if prefix and not reply.startswith(prefix):
            reply = prefix + reply

    # 4. 记录日志
    # 防重判断：如果当前是排队状态，并且回复文本是排队提示，说明 handle_turn 里已经存过日志了
    is_waiting_reply = state.is_human_mode and '排队' in reply
    if not is_waiting_reply:
        ChatLog.objects.create(
            session_id=session_id,
            user_input=user_input,
            bot_reply=reply,
            intent=state.current_intent,
            emotion=emotion,
            entities=state.slots
        )

    return Response({
        'session_id': session_id,
        'reply': reply,
        'intent': state.current_intent,
        'emotion': emotion,
        'entities': state.slots,
        'turn_count': state.turn_count,
        'is_human_mode': state.is_human_mode
    })


@api_view(['GET'])
def poll_messages(request):
    """前端轮询获取人工回复"""
    session_id = request.query_params.get('session_id')
    if not session_id:
        return Response({'replies': []})

    # 获取该会话最近 5 条人工回复
    logs = ChatLog.objects.filter(
        session_id=session_id,
        is_from_human=True
    ).order_by('-created_at')[:5]

    # 倒序排列，保证时间线正确
    replies = [log.bot_reply for log in reversed(logs)]
    return Response({'replies': replies})
    
    # 在文件末尾追加取消人工接口

@api_view(['POST'])
def cancel_human(request):
    """用户点击按钮取消人工排队"""
    from .models import DialogueState
    session_id = request.data.get('session_id')
    
    if session_id:
        state = DialogueState.objects.filter(session_id=session_id).first()
        if state and state.is_human_mode:
            state.is_human_mode = False
            state.current_intent = ''
            state.slots = {}
            state.save()
            return Response({'status': 'ok', 'message': '已取消人工排队，交还给 AI 助手。'})
    
    return Response({'status': 'error', 'message': '当前未处于人工状态'})