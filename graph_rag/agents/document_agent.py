from __future__ import annotations

from graph_rag.retrievers.vector_retriever import VectorRetriever


class DocumentAgent:
    def __init__(self, retriever: VectorRetriever) -> None:
        self.retriever = retriever

    def run(self, question: str, entities: list[dict], graph_facts: list[dict], top_k: int) -> list[dict]:
        entity_terms = " ".join(item["name"] for item in entities)
        graph_terms = " ".join(f"{item['head']} {item['tail']}" for item in graph_facts[:10])
        query = f"{question} {entity_terms} {graph_terms}".strip()
        return self.retriever.retrieve(query or question, top_k=top_k)
