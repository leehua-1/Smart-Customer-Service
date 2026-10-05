import json
from pathlib import Path
from django.core.management.base import BaseCommand
from chat.models import FAQ


class Command(BaseCommand):
    help = '从 JSON 文件批量导入 FAQ 数据'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            nargs='?',
            default='data/faq_seed.json',
            help='FAQ JSON 文件路径'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='导入前清空现有 FAQ 数据'
        )

    def handle(self, *args, **options):
        json_path = Path(options['json_file'])

        if not json_path.exists():
            self.stdout.write(self.style.ERROR(f'文件不存在: {json_path}'))
            return

        if options['clear']:
            count = FAQ.objects.count()
            FAQ.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'已清空 {count} 条旧数据'))

        with open(json_path, encoding='utf-8') as f:
            data = json.load(f)

        created = 0
        for item in data:
            FAQ.objects.create(
                question=item['question'],
                answer=item['answer'],
                intent_label=item.get('intent', ''),
                entity_tags=item.get('entities', [])
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'成功导入 {created} 条 FAQ'))