import sys
import os
from pathlib import Path

# 把项目根目录加入 sys.path，让 Python 能找到 config 模块
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from chat.models import FAQ


MODEL_NAME = 'BAAI/bge-base-zh-v1.5'
INDEX_DIR = BASE_DIR / 'nlp' / 'models'
INDEX_PATH = INDEX_DIR / 'faq.index'
ID_MAP_PATH = INDEX_DIR / 'faq_ids.npy'


def build():
    print('加载句向量模型...')
    model = SentenceTransformer(MODEL_NAME)

    print('读取 FAQ 数据...')
    faqs = list(FAQ.objects.all())
    questions = [f.question for f in faqs]
    ids = np.array([f.id for f in faqs], dtype=np.int64)

    print(f'共 {len(questions)} 条，开始编码...')
    embeddings = model.encode(questions, normalize_embeddings=True)

    print('构建 FAISS 索引...')
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings.astype('float32'))

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    np.save(str(ID_MAP_PATH), ids)

    print(f'索引已保存：{INDEX_PATH}')
    print(f'ID 映射已保存：{ID_MAP_PATH}')


if __name__ == '__main__':
    build()