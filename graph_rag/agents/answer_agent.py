from __future__ import annotations

from graph_rag.rag.answer_generator import AnswerGenerator


class AnswerAgent:
    def __init__(self, generator: AnswerGenerator) -> None:
        self.generator = generator

    def run(self, question: str, evidence: dict) -> str:
        return self.generator.generate(question, evidence)
