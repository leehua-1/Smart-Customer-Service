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

    def __str__(self):
        return self.question[:30]


class ChatLog(models.Model):
    session_id = models.CharField(max_length=64, db_index=True)
    user_input = models.TextField()
    bot_reply = models.TextField()
    intent = models.CharField(max_length=50, blank=True)
    emotion = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_log'
        verbose_name = '对话记录'