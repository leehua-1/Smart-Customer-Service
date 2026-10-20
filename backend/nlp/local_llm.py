"""
本地大模型客户端
- 通过 Ollama 调用 Qwen2.5
- 用于意图识别和复杂语义理解
"""

import json
import re
import requests


OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL_NAME = 'qwen2.5:1.5b'
TIMEOUT = 30


class LocalLLMClient:
    def __init__(self):
        self.url = OLLAMA_URL
        self.model = MODEL_NAME
        self.timeout = TIMEOUT

    def _call(self, prompt, max_tokens=100, temperature=0.1):
        """调用 Ollama API"""
        try:
            response = requests.post(
                self.url,
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'keep_alive': '30m',   # 保持模型加载
                    'options': {
                        'temperature': temperature,
                        'num_predict': max_tokens,
                    },
                },
                timeout=self.timeout,
            )
            if response.status_code == 200:
                return response.json().get('response', '').strip()
            else:
                print(f'[LocalLLM] HTTP {response.status_code}')
                return ''
        except requests.Timeout:
            print('[LocalLLM] 请求超时')
            return ''
        except requests.ConnectionError:
            print('[LocalLLM] 无法连接 Ollama，服务未启动？')
            return ''
        except Exception as e:
            print(f'[LocalLLM] 调用失败: {e}')
            return ''

    def classify_intent(self, user_input, intent_labels):
        """
        调用本地大模型对用户输入分类
        返回 (intent, confidence, raw)
        """
        labels_str = '、'.join(intent_labels)

        prompt = f"""你是客服意图分类助手。从以下意图中选一个最匹配用户输入的：
{labels_str}

严格按以下 JSON 格式输出，不要其他文字：
{{"intent": "选中的标签", "confidence": 0.0到1.0之间的数字}}

用户输入：{user_input}
输出："""

        raw = self._call(prompt, max_tokens=80, temperature=0.1)
        if not raw:
            return 'unknown', 0.0, ''

        try:
            cleaned = raw.replace('```json', '').replace('```', '').strip()
            match = re.search(r'\{.*?\}', cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                intent = data.get('intent', 'unknown')
                if intent not in intent_labels:
                    intent = 'unknown'
                confidence = float(data.get('confidence', 0.0))
                return intent, confidence, raw
        except (json.JSONDecodeError, ValueError):
            pass

        for label in intent_labels:
            if label in raw:
                return label, 0.7, raw

        return 'unknown', 0.0, raw

    def is_available(self):
        """检查 Ollama 服务是否可用"""
        try:
            resp = requests.get('http://localhost:11434/api/tags', timeout=3)
            return resp.status_code == 200
        except Exception:
            return False


_client_instance = None


def get_local_llm():
    global _client_instance
    if _client_instance is None:
        _client_instance = LocalLLMClient()
    return _client_instance


if __name__ == '__main__':
    client = get_local_llm()

    print(f'Ollama 服务可用: {client.is_available()}')

    test_labels = ['greeting', 'order_query', 'refund_return', 'complaint',
                   'human_agent', 'cancel', 'payment', 'logistics']

    test_queries = [
        '我想退钱',
        '你们服务真烂',
        '有没有真人客服',
        '订单到哪里了',
        '不弄了，算了',
    ]

    for q in test_queries:
        intent, score, raw = client.classify_intent(q, test_labels)
        print(f'{q:15s} -> intent={intent:15s} score={score:.2f}')