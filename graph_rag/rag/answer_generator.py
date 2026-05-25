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
        return self.llm.answer(question, graph_context, document_context)

