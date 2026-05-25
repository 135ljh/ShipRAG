from __future__ import annotations

from graph_rag.db.neo4j_client import Neo4jClient


class GraphRetriever:
    def __init__(self, neo4j: Neo4jClient) -> None:
        self.neo4j = neo4j

    def retrieve(self, entities: list[dict], hops: int = 2, limit: int = 80) -> list[dict]:
        return self.neo4j.neighborhood([item["id"] for item in entities], hops=hops, limit=limit)

