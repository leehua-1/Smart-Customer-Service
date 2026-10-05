import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChatLog
from nlp.retrieve import get_retriever


@api_view(['POST'])
def chat(request):
    user_input = request.data.get('message', '').strip()
    session_id = request.data.get('session_id') or str(uuid.uuid4())

    if not user_input:
        return Response({'error': '消息不能为空'}, status=400)

    retriever = get_retriever()
    answer = retriever.best_answer(user_input, threshold=0.6)

    if answer:
        reply = answer
    else:
        reply = '抱歉，我没有完全理解您的问题。您可以换个说法，或输入“转人工”联系客服。'

    ChatLog.objects.create(
        session_id=session_id,
        user_input=user_input,
        bot_reply=reply,
        intent='',
        emotion=''
    )

    return Response({
        'session_id': session_id,
        'reply': reply
    })