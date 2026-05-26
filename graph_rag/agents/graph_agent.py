from __future__ import annotations

from graph_rag.retrievers.graph_retriever import GraphRetriever


class GraphAgent:
    def __init__(self, retriever: GraphRetriever) -> None:
        self.retriever = retriever

    def run(self, entities: list[dict], hops: int) -> list[dict]:
        return self.retriever.retrieve(entities, hops=hops)
