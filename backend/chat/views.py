import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ChatLog


@api_view(['POST'])
def chat(request):
    user_input = request.data.get('message', '').strip()
    session_id = request.data.get('session_id') or str(uuid.uuid4())

    if not user_input:
        return Response({'error': '消息不能为空'}, status=400)

    # 当前阶段先返回固定回复，后续接入 NLP 模块后替换
    reply = f'收到你的消息：{user_input}'

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