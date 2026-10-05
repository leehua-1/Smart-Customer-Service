from django.contrib import admin
from .models import FAQ, ChatLog

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'intent_label', 'created_at')
    search_fields = ('question', 'answer')
    list_filter = ('intent_label',)

@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_id', 'intent', 'emotion', 'created_at')
    search_fields = ('user_input', 'bot_reply')
    list_filter = ('intent', 'emotion')