from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        from nlp.retrieve import get_retriever
        from nlp.intent import get_intent_classifier
        get_retriever()
        get_intent_classifier()