from nlp.intent import get_intent_classifier

clf = get_intent_classifier()

queries = ['不合适', '我不需要了', '太慢了不要了', '算了不用了', '我要退货', '什么破服务']
for q in queries:
    print(f'{q:10s} -> {clf.predict_topk(q, 3)}')