from django.db import models


class FAQ(models.Model):
    question = models.TextField(verbose_name='标准问题')
    answer = models.TextField(verbose_name='标准答案')
    intent_label = models.CharField(max_length=50, blank=True, verbose_name='意图标签')
    entity_tags = models.JSONField(default=list, blank=True, verbose_name='实体标签')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'faq'
        verbose_name = 'FAQ 知识'
        verbose_name_plural = 'FAQ 知识'

    def __str__(self):
        return self.question[:30]


class ChatLog(models.Model):
    session_id = models.CharField(max_length=64, db_index=True)
    user_input = models.TextField()
    bot_reply = models.TextField()
    intent = models.CharField(max_length=50, blank=True)
    emotion = models.CharField(max_length=20, blank=True)
    entities = models.JSONField(default=dict, blank=True, verbose_name='提取实体')   # 新增
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_log'
        verbose_name = '对话记录'
        verbose_name_plural = '对话记录'

    def __str__(self):
        return f'{self.session_id[:8]} - {self.user_input[:20]}'

class DialogueState(models.Model):
    """多轮对话状态，每个 session 一条记录"""

    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    current_intent = models.CharField(max_length=50, blank=True, verbose_name='当前意图')
    slots = models.JSONField(default=dict, blank=True, verbose_name='已填槽位')
    turn_count = models.IntegerField(default=0, verbose_name='对话轮次')
    last_input = models.TextField(blank=True, verbose_name='上轮输入')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dialogue_state'
        verbose_name = '对话状态'
        verbose_name_plural = '对话状态'

    def __str__(self):
        return f'{self.session_id[:8]} - {self.current_intent}'