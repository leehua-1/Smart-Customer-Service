import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChatLog
from nlp.retrieve import get_retriever
from nlp.intent import get_intent_classifier
from nlp.emotion import get_emotion_classifier
from nlp.entity import extract_entities      # 新增


# 情绪到回复前缀的映射
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

    # 1. 意图识别
    intent_clf = get_intent_classifier()
    intent, intent_score = intent_clf.predict(user_input)

    # 2. 情感分析
    emotion_clf = get_emotion_classifier()
    emotion, emotion_score = emotion_clf.predict(user_input)

    # 3. 实体抽取（新增）
    entities = extract_entities(user_input)

    # 4. 语义检索
    retriever = get_retriever()
    answer = retriever.best_answer(user_input, threshold=0.6)

    if answer:
        reply = answer
    else:
        reply = '抱歉，我没有完全理解您的问题。您可以换个说法，或输入“转人工”联系客服。'

    # 5. 根据情绪调整回复
    prefix = EMOTION_PREFIX.get(emotion, '')
    if prefix and not reply.startswith(prefix):
        reply = prefix + reply

    # 6. 记录日志（含 entities）
    ChatLog.objects.create(
        session_id=session_id,
        user_input=user_input,
        bot_reply=reply,
        intent=intent,
        emotion=emotion,
        entities=entities
    )

    return Response({
        'session_id': session_id,
        'reply': reply,
        'intent': intent,
        'emotion': emotion,
        'entities': entities      # 新增
    })