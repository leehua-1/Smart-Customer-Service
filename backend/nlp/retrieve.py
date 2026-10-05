"""
FAQ 语义检索模块
- 使用 text2vec-base-chinese 编码用户查询
- 在 FAISS 索引中检索最相似的 FAQ
- 支持相似度阈值过滤
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# 仅当直接运行本脚本时，才手动初始化 Django
# 被 Django 项目 import 时，Django 已初始化，无需重复
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from chat.models import FAQ


# ---------- 配置 ----------
MODEL_NAME = 'BAAI/bge-base-zh-v1.5'
INDEX_PATH = BASE_DIR / 'nlp' / 'models' / 'faq.index'
ID_MAP_PATH = BASE_DIR / 'nlp' / 'models' / 'faq_ids.npy'


class FAQRetriever:
    """FAQ 语义检索器"""

    def __init__(self):
        print('加载句向量模型...')
        self.model = SentenceTransformer(MODEL_NAME)

        print('加载 FAISS 索引...')
        self.index = faiss.read_index(str(INDEX_PATH))
        self.ids = np.load(str(ID_MAP_PATH))

        print(f'就绪，共 {self.index.ntotal} 条 FAQ')

    def search(self, query, top_k=3, threshold=0.6):
        """
        检索与 query 最相似的 FAQ

        参数：
            query     : 用户输入
            top_k     : 返回候选数量
            threshold : 相似度阈值，低于此值不返回

        返回：
            [(FAQ 对象, 相似度 float), ...]
        """
        vec = self.model.encode([query], normalize_embeddings=True)
        scores, indices = self.index.search(vec.astype('float32'), top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if score < threshold:
                continue
            faq_id = int(self.ids[idx])
            try:
                faq = FAQ.objects.get(id=faq_id)
            except FAQ.DoesNotExist:
                continue
            results.append((faq, float(score)))
        return results

    def best_answer(self, query, threshold=0.6):
        """
        返回最佳匹配的答案，未命中返回 None
        """
        results = self.search(query, top_k=1, threshold=threshold)
        if results:
            return results[0][0].answer
        return None


# ---------- 单例（供 views.py 复用，避免重复加载模型） ----------
_retriever_instance = None


def get_retriever():
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = FAQRetriever()
    return _retriever_instance


# ---------- 本地测试 ----------
if __name__ == '__main__':
    retriever = get_retriever()

    test_queries = [
        '我的订单到哪里了',
        '怎么退货',
        '我要投诉',
        '能不能转人工',
        '支付失败怎么办',
        '你们有什么产品',
        '怎么修改密码',
        '快递什么时候到',
    ]

    for q in test_queries:
        print(f'\n查询：{q}')
        results = retriever.search(q, top_k=3)
        if not results:
            print('  未命中（相似度低于阈值）')
        else:
            for faq, score in results:
                answer_preview = faq.answer[:40].replace('\n', ' ')
                print(f'  [{score:.3f}] {faq.question} → {answer_preview}...')