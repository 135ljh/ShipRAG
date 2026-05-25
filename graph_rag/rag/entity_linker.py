from __future__ import annotations

from graph_rag.db.neo4j_client import Neo4jClient


class EntityLinker:
    def __init__(self, neo4j: Neo4jClient) -> None:
        self.neo4j = neo4j

    def link(self, question: str, limit: int = 8) -> list[dict]:
        entities = self.neo4j.find_entities(question, limit=limit)
        if entities:
            return entities
        tokens = [token for token in question.replace("？", " ").replace("，", " ").split() if len(token) >= 2]
        found: list[dict] = []
        seen: set[str] = set()
        for token in tokens[:5]:
            for entity in self.neo4j.keyword_entities(token, limit=3):
                if entity["id"] not in seen:
                    seen.add(entity["id"])
                    found.append(entity)
        if found:
            return found[:limit]
        return self.neo4j.fuzzy_entities(question, limit=limit)
