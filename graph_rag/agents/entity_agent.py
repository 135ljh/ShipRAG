from __future__ import annotations

from graph_rag.rag.entity_linker import EntityLinker


class EntityAgent:
    def __init__(self, linker: EntityLinker) -> None:
        self.linker = linker

    def run(self, question: str) -> list[dict]:
        return self.linker.link(question)
