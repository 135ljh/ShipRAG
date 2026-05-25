import requests
import json

BASE_URL = "http://10.21.77.7:8000"
GENERATE_URL = f"{BASE_URL}/generate"

print("正在测试 Pangu 服务...")

try:
    health = requests.get(f"{BASE_URL}/health", timeout=10)
    print("health 状态码:", health.status_code)
    print("health 返回:", health.text)
except Exception as e:
    print("health 请求失败:", repr(e))
    raise SystemExit(1)

prompt = """
你是一个面向船体装配工艺领域的知识图谱信息抽取助手。

请从以下文本中抽取知识三元组。

要求：
1. 只返回 JSON，不要解释。
2. 不要编造原文中不存在的信息。
3. 三元组格式为 subject、predicate、object、evidence。

文本：
船体装配前，应检查胎架、样板、型线和构件编号，确保构件位置准确。

输出格式：
{
  "triples": [
    {
      "subject": "...",
      "predicate": "...",
      "object": "...",
      "evidence": "..."
    }
  ]
}

/no_think
"""

payload = {
    "prompt": prompt,
    "max_new_tokens": 512,
    "temperature": 0
}

print("正在请求 /generate ...")

try:
    response = requests.post(
        GENERATE_URL,
        json=payload,
        timeout=180
    )

    print("generate 状态码:", response.status_code)
    print("generate 原始返回:")
    print(response.text)

    response.raise_for_status()

    data = response.json()
    print("\n模型输出 content:")
    print(data.get("content"))

except Exception as e:
    print("generate 请求失败:", repr(e))