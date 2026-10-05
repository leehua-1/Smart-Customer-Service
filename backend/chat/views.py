import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChatLog
from nlp.retrieve import get_retriever
from nlp.intent import get_intent_classifier


@api_view(['POST'])
def chat(request):
    user_input = request.data.get('message', '').strip()
    session_id = request.data.get('session_id') or str(uuid.uuid4())

    if not user_input:
        return Response({'error': '消息不能为空'}, status=400)

    # 1. 意图识别
    intent_clf = get_intent_classifier()
    intent, intent_score = intent_clf.predict(user_input)

    # 2. 语义检索
    retriever = get_retriever()
    answer = retriever.best_answer(user_input, threshold=0.6)

    if answer:
        reply = answer
    else:
        reply = '抱歉，我没有完全理解您的问题。您可以换个说法，或输入“转人工”联系客服。'

    # 3. 记录日志
    ChatLog.objects.create(
        session_id=session_id,
        user_input=user_input,
        bot_reply=reply,
        intent=intent,
        emotion=''
    )

    return Response({
        'session_id': session_id,
        'reply': reply,
        'intent': intent,
        'intent_score': round(intent_score, 3)
    })