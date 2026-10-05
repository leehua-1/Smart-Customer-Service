from django.contrib import admin
from .models import FAQ, ChatLog

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'intent_label', 'created_at')
    search_fields = ('question', 'answer')
    list_filter = ('intent_label',)

@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_id', 'short_input', 'short_reply', 'intent', 'emotion', 'created_at')
    search_fields = ('user_input', 'bot_reply')
    list_filter = ('intent', 'emotion')

    def short_input(self, obj):
        return obj.user_input[:20]
    short_input.short_description = '用户输入'

    def short_reply(self, obj):
        return obj.bot_reply[:20]
    short_reply.short_description = '机器人回复'