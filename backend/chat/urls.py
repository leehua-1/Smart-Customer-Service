from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat, name='chat'),
    path('chat/poll/', views.poll_messages, name='poll_messages'),
    path('chat/cancel_human/', views.cancel_human, name='cancel_human'), # 新增
]