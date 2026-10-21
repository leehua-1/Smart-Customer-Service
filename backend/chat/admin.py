from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.html import format_html
from .models import FAQ, ChatLog, DialogueState

# 修改系统标题
admin.site.site_header = "智能客服系统"
admin.site.site_title = "客服管控中心"
admin.site.index_title = "数据总览"

# ================= 注入自定义首页数据 =================
original_index = admin.site.index

def custom_index(request, extra_context=None):
    extra_context = extra_context or {}
    pending_states = DialogueState.objects.filter(is_human_mode=True).order_by('-updated_at')
    
    pending_users = []
    for state in pending_states:
        latest_log = ChatLog.objects.filter(session_id=state.session_id).order_by('-created_at').first()
        if latest_log:
            pending_users.append({
                'session_id': state.session_id,
                'current_intent': state.current_intent,
                'turn_count': state.turn_count,
                'latest_log_id': latest_log.id
            })
            
    extra_context['pending_users'] = pending_users
    extra_context['pending_count'] = len(pending_users)
    extra_context['total_logs'] = ChatLog.objects.count()
    extra_context['faq_count'] = FAQ.objects.count()
    
    return original_index(request, extra_context)

admin.site.index = custom_index
# ======================================================


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'short_question', 'intent_label', 'created_at')
    search_fields = ('question', 'answer')
    list_filter = ('intent_label',)

    def short_question(self, obj):
        return obj.question[:40]
    short_question.short_description = '问题'


@admin.register(DialogueState)
class DialogueStateAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'current_intent', 'human_status', 'turn_count', 'updated_at', 'action_buttons')
    list_filter = ('is_human_mode', 'current_intent')
    search_fields = ('session_id',)
    actions = ['release_to_ai']

    def human_status(self, obj):
        if obj.is_human_mode:
            return format_html('<span style="color:#fff; background:#f56c6c; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:bold;">🟠 等待人工</span>')
        return format_html('<span style="color:#fff; background:#67c23a; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:bold;">🟢 AI 处理中</span>')
    human_status.short_description = '接待状态'

    def action_buttons(self, obj):
        if obj.is_human_mode:
            latest_log = ChatLog.objects.filter(session_id=obj.session_id).order_by('-created_at').first()
            if latest_log:
                url = f'/admin/chat/chatlog/{latest_log.id}/reply/'
                return format_html(f'<a href="{url}" target="_blank" style="background:#4f8cff; color:white; padding:6px 14px; border-radius:6px; text-decoration:none; font-size:13px; font-weight:bold;">💬 立即回复</a>')
        return '-'
    action_buttons.short_description = '快捷操作'

    @admin.action(description='🔓 强制释放：交还给 AI 处理')
    def release_to_ai(self, request, queryset):
        updated = queryset.filter(is_human_mode=True).update(is_human_mode=False)
        self.message_user(request, f'成功释放 {updated} 个会话。', level='success')

    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-is_human_mode', '-updated_at')


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_id', 'role_tag', 'short_input', 'short_reply', 'intent_tag', 'created_at', 'quick_reply_btn')
    search_fields = ('user_input', 'bot_reply', 'session_id')
    list_filter = ('is_from_human', 'intent', 'emotion')
    list_per_page = 30

    def role_tag(self, obj):
        if obj.is_from_human or obj.user_input == '[人工回复]':
            return format_html('<span style="background:#ff9f43; color:white; padding:4px 8px; border-radius:6px; font-size:12px; font-weight:bold;">真人客服</span>')
        return format_html('<span style="background:#4f8cff; color:white; padding:4px 8px; border-radius:6px; font-size:12px; font-weight:bold;">AI 助手</span>')
    role_tag.short_description = '发送者'

    def intent_tag(self, obj):
        if not obj.intent: return '-'
        colors = {'complaint': '#f56c6c', 'refund_return': '#e6a23c', 'human_agent': '#909399'}
        bg_colors = {'complaint': '#fef0f0', 'refund_return': '#fdf6ec', 'human_agent': '#f4f4f5'}
        color = colors.get(obj.intent, '#67c23a')
        bg = bg_colors.get(obj.intent, '#f0f9eb')
        return format_html(f'<span style="color:{color}; background:{bg}; padding:4px 8px; border-radius:6px; font-weight:bold; font-size:12px;">{obj.intent}</span>')
    intent_tag.short_description = '意图'

    def short_input(self, obj):
        return obj.user_input[:20]

    def short_reply(self, obj):
        return obj.bot_reply[:20]

    def quick_reply_btn(self, obj):
        url = f'/admin/chat/chatlog/{obj.id}/reply/'
        return format_html(f'<a href="{url}" target="_blank" style="background:#e6f0ff; color:#4f8cff; border:1px solid #4f8cff; padding:4px 12px; border-radius:6px; text-decoration:none; font-size:12px; font-weight:bold; transition: 0.3s;">回复</a>')
    quick_reply_btn.short_description = '操作'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:log_id>/reply/', self.admin_site.admin_view(self.reply_view), name='chatlog-reply'),
        ]
        return custom_urls + urls

    def reply_view(self, request, log_id):
        log = ChatLog.objects.get(id=log_id)
        context_logs = list(reversed(ChatLog.objects.filter(session_id=log.session_id).order_by('-created_at')[:10]))

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
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'ok', 'message': message})
                self.message_user(request, f'已回复用户。', level='success')
                # 【关键修改】这里跳回数据看板，而不是难看的表格列表
                return HttpResponseRedirect('/admin/')
        return render(request, 'admin/chatlog_reply.html', {'log': log, 'context_logs': context_logs})