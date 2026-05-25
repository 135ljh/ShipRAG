from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from graph_rag.config import settings


class ShipQdrantClient:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection

    def ensure_collection(self, vector_size: int | None = None) -> None:
        vector_size = vector_size or settings.embedding_dim
        collections = self.client.get_collections().collections
        if any(item.name == self.collection for item in collections):
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def search(self, vector: list[float], top_k: int = 8) -> list[dict]:
        results = self.client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            with_payload=True,
        ).points
        return [
            {
                "type": "document",
                "score": float(point.score),
                **(point.payload or {}),
            }
            for point in results
        ]

