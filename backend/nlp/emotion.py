"""
零样本情感分析
- 复用 BGE 句向量模型
- 识别用户情绪：满意、愤怒、困惑、中性
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = 'BAAI/bge-base-zh-v1.5'

EMOTION_DESCRIPTIONS = {
    'satisfaction': [
        '我很满意，很开心，谢谢你的帮助',
        '服务很好，解决问题了，点赞',
    ],
    'anger': [
        '我很生气，非常不满，要投诉',
        '太差了，什么破服务，气死了',
    ],
    'confusion': [
        '我不太明白，这是什么意思',
        '有点困惑，搞不清楚怎么做',
    ],
    'neutral': [
        '我想咨询一个问题，请问怎么操作',
        '普通的询问，陈述事实',
    ],
}


class EmotionClassifier:
    def __init__(self):
        print('加载情感分析模型...')
        self.model = SentenceTransformer(MODEL_NAME)

        self.labels = []
        descriptions = []
        for label, descs in EMOTION_DESCRIPTIONS.items():
            for d in descs:
                self.labels.append(label)
                descriptions.append(d)

        self.vectors = self.model.encode(descriptions, normalize_embeddings=True)
        print(f'情感分类器就绪，共 {len(EMOTION_DESCRIPTIONS)} 类情绪')

    def predict(self, query):
        vec = self.model.encode([query], normalize_embeddings=True)
        scores = np.dot(self.vectors, vec[0])
        best_idx = int(np.argmax(scores))
        return self.labels[best_idx], float(scores[best_idx])


_emotion_instance = None


def get_emotion_classifier():
    global _emotion_instance
    if _emotion_instance is None:
        _emotion_instance = EmotionClassifier()
    return _emotion_instance


if __name__ == '__main__':
    clf = get_emotion_classifier()

    test_queries = [
        '谢谢，你们的服务真好',
        '我要投诉，太气人了',
        '这个我不太懂，能解释一下吗',
        '我想问一下订单状态',
        '等了三天还没发货，什么垃圾服务',
        '解决了，非常感谢',
    ]

    for q in test_queries:
        label, score = clf.predict(q)
        print(f'{q:20s} → {label:15s} ({score:.3f})')