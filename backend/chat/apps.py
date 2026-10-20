import os
import sys
from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        # 只在 runserver 时预加载
        if 'runserver' not in sys.argv:
            return

        # 只在子进程（真正处理请求的进程）预加载
        # 父进程只负责文件监控，不加载模型
        if os.environ.get('RUN_MAIN') != 'true':
            return

        from nlp.retrieve import get_retriever
        from nlp.intent import get_intent_classifier
        from nlp.emotion import get_emotion_classifier

        get_retriever()
        get_intent_classifier()
        get_emotion_classifier()