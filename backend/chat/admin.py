from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from .models import FAQ, ChatLog, DialogueState


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_question', 'intent_label', 'created_at')
    search_fields = ('question', 'answer')
    list_filter = ('intent_label',)
    list_per_page = 20

    def short_question(self, obj):
        return obj.question[:40]
    short_question.short_description = '问题'


@admin.register(DialogueState)
class DialogueStateAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'current_intent', 'is_human_mode', 'turn_count', 'updated_at')
    list_filter = ('is_human_mode', 'current_intent')
    search_fields = ('session_id',)
    actions = ['close_human_mode']

    @admin.action(description='关闭人工模式（交还给 AI）')
    def close_human_mode(self, request, queryset):
        queryset.update(is_human_mode=False)
        self.message_user(request, '已切回 AI 模式')


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_id', 'short_input', 'short_reply',
                    'intent', 'emotion', 'short_entities', 'is_from_human', 'created_at')
    search_fields = ('user_input', 'bot_reply')
    list_filter = ('intent', 'emotion', 'is_from_human')
    list_per_page = 20
    actions = ['reply_as_human']

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

    @admin.action(description='以人工身份回复')
    def reply_as_human(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, '请只选择一条记录')
            return
        log = queryset.first()
        return redirect(f'/admin/chat/chatlog/{log.id}/reply/')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:log_id>/reply/', self.admin_site.admin_view(self.reply_view), name='chatlog-reply'),
        ]
        return custom_urls + urls

    def reply_view(self, request, log_id):
        log = ChatLog.objects.get(id=log_id)

        if request.method == 'POST':
            message = request.POST.get('message', '').strip()
            if message:
                ChatLog.objects.create(
                    session_id=log.session_id,
                    user_input='[人工回复]',
                    bot_reply=message,
                    intent=log.intent,
                    emotion='',
                    entities={},
                    is_from_human=True
                )
                self.message_user(request, f'已回复会话 {log.session_id[:8]}')
                return HttpResponseRedirect('/admin/chat/chatlog/')

        return render(request, 'admin/chatlog_reply.html', {'log': log})