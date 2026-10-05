"""
规则法实体抽取
- 提取订单号、手机号、金额、日期
- 产品名通过关键词匹配
"""

import re
from datetime import datetime


# 正则模式
PATTERNS = {
    'order_id': re.compile(r'(?<!\d)(\d{10,20})(?!\d)'),       # 10-20 位纯数字
    'phone': re.compile(r'(?<!\d)(1[3-9]\d{9})(?!\d)'),        # 手机号
    'amount': re.compile(r'(\d+(?:\.\d{1,2})?)\s*元'),          # 金额
    'date': re.compile(
    r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?'      # 2026-10-06、2026年10月6日
    r'|\d{1,2}[-/月]\d{1,2}日?)'                # 10月6日、10-06
),
}

# 产品关键词表（可后续从 FAQ 数据动态提取）
PRODUCT_KEYWORDS = [
    '手机', '电脑', '平板', '耳机', '充电器', '数据线',
    '会员卡', '优惠券', '套餐', '流量包',
]


def extract_entities(text):
    entities = {}

    # 先提取手机号
    phone_matches = PATTERNS['phone'].findall(text)
    if phone_matches:
        entities['phone'] = list(set(phone_matches))

    # 剔除手机号后再匹配订单号，避免重复
    text_for_order = text
    for phone in phone_matches:
        text_for_order = text_for_order.replace(phone, '')

    order_matches = PATTERNS['order_id'].findall(text_for_order)
    if order_matches:
        entities['order_id'] = list(set(order_matches))

    # 金额、日期
    for name in ['amount', 'date']:
        matches = PATTERNS[name].findall(text)
        if matches:
            entities[name] = list(set(matches))

    # 产品名
    products = [kw for kw in PRODUCT_KEYWORDS if kw in text]
    if products:
        entities['product'] = products

    return entities


if __name__ == '__main__':
    test_inputs = [
        '我的订单 1234567890123 到哪了',
        '请打 13812345678 联系我',
        '这个东西 199 元什么时候发货',
        '2026年10月6日下的单',
        '我想买手机，多少钱',
        '我的快递在哪里',
        '你好，在吗',
    ]

    for text in test_inputs:
        ents = extract_entities(text)
        print(f'{text:35s} → {ents}')