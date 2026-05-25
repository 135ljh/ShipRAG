from __future__ import annotations

from openai import OpenAI

from graph_rag.config import settings


class OpenAIService:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured. Please set it in .env.")
        self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=settings.openai_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def answer(self, question: str, graph_context: str, document_context: str) -> str:
        prompt = f"""你是一个严谨的船体装配知识图谱问答助手。
请只基于给定的知识图谱事实和教材原文证据回答用户问题。
不要使用外部知识。
如果证据不足，请回答“根据当前知识库无法确定”。
回答必须包含“结论”“依据”“引用”。

用户问题：
{question}

知识图谱事实：
{graph_context or "无"}

教材原文证据：
{document_context or "无"}
"""
        response = self.client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": "你是严谨的船体装配知识问答助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

