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

    # 情感分析（用于回复前缀）
    emotion_clf = get_emotion_classifier()
    emotion, _ = emotion_clf.predict(user_input)

    # 走多轮对话管理器
    reply, state = handle_turn(session_id, user_input)

    # 情绪前缀
    prefix = EMOTION_PREFIX.get(emotion, '')
    if prefix and not reply.startswith(prefix):
        reply = prefix + reply

    # 记录日志
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
        'turn_count': state.turn_count
    })