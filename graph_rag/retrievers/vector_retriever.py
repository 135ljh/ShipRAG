from __future__ import annotations

from graph_rag.db.qdrant_client import ShipQdrantClient
from graph_rag.llm import OpenAIService


class VectorRetriever:
    def __init__(self, qdrant: ShipQdrantClient, llm: OpenAIService) -> None:
        self.qdrant = qdrant
        self.llm = llm

    def retrieve(self, query: str, top_k: int = 8) -> list[dict]:
        vector = self.llm.embed([query])[0]
        return self.qdrant.search(vector, top_k=top_k)

