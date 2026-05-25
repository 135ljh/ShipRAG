from __future__ import annotations

from graph_rag.llm import OpenAIService
from graph_rag.rag.context_builder import ContextBuilder


class AnswerGenerator:
    def __init__(self, llm: OpenAIService, context_builder: ContextBuilder) -> None:
        self.llm = llm
        self.context_builder = context_builder

    def generate(self, question: str, evidence: dict) -> str:
        graph_context = self.context_builder.build_graph_context(evidence.get("graph", []))
        document_context = self.context_builder.build_document_context(evidence.get("documents", []))
        try:
            return self.llm.answer(question, graph_context, document_context)
        except Exception as exc:
            graph_lines = graph_context.splitlines()[:5]
            doc_lines = document_context.splitlines()[:8]
            basis = "\n".join([*graph_lines, *doc_lines]).strip()
            return (
                "结论：\n"
                "当前语言模型接口不可用，系统已返回基于检索证据的摘要。请检查 OPENAI_API_KEY 和 OPENAI_BASE_URL 后重新生成答案。\n\n"
                "依据：\n"
                f"{basis or '未检索到足够证据。'}\n\n"
                "引用：\n"
                f"- LLM 调用错误：{type(exc).__name__}"
            )
