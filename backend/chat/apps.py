from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        # 预加载检索器，避免首次请求卡顿
        from nlp.retrieve import get_retriever
        get_retriever()