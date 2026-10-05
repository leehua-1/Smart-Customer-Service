from django.contrib import admin
from .models import FAQ, ChatLog


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_question', 'intent_label', 'created_at')
    search_fields = ('question', 'answer')
    list_filter = ('intent_label',)
    list_per_page = 20

    def short_question(self, obj):
        return obj.question[:40]
    short_question.short_description = '问题'


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_id', 'short_input', 'short_reply',
                    'intent', 'emotion', 'short_entities', 'created_at')
    search_fields = ('user_input', 'bot_reply')
    list_filter = ('intent', 'emotion')
    list_per_page = 20

    def short_input(self, obj):
        return obj.user_input[:20]
    short_input.short_description = '用户输入'

    def short_reply(self, obj):
        return obj.bot_reply[:20]
    short_reply.short_description = '机器人回复'

    def short_entities(self, obj):
        if not obj.entities:
            return '-'
        return ', '.join(f'{k}:{v}' for k, v in obj.entities.items())[:30]
    short_entities.short_description = '实体'