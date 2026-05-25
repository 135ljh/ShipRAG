from __future__ import annotations

from collections.abc import Iterable
from difflib import SequenceMatcher

from neo4j import GraphDatabase

from graph_rag.config import settings


class Neo4jClient:
    def __init__(self) -> None:
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        self.database = settings.neo4j_database

    def close(self) -> None:
        self.driver.close()

    def find_entities(self, question: str, limit: int = 8) -> list[dict]:
        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                MATCH (e:Entity)
                WHERE $question CONTAINS e.name AND size(e.name) >= 2
                RETURN e.id AS id, e.name AS name, e.type AS type, e.definition AS definition
                ORDER BY size(e.name) DESC
                LIMIT $limit
                """,
                question=question,
                limit=limit,
            )
            return [dict(record) for record in records]

    def keyword_entities(self, keyword: str, limit: int = 10) -> list[dict]:
        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                MATCH (e:Entity)
                WHERE e.name CONTAINS $keyword
                RETURN e.id AS id, e.name AS name, e.type AS type, e.definition AS definition
                ORDER BY size(e.name) ASC
                LIMIT $limit
                """,
                keyword=keyword,
                limit=limit,
            )
            return [dict(record) for record in records]

    def fuzzy_entities(self, mention: str, limit: int = 5) -> list[dict]:
        def best_score(text: str, name: str) -> float:
            base = SequenceMatcher(None, text, name).ratio()
            compact = "".join(ch for ch in text if ch.strip())
            windows = []
            for size in range(max(2, len(name) - 2), min(len(compact), len(name) + 2) + 1):
                windows.extend(compact[i : i + size] for i in range(0, max(0, len(compact) - size + 1)))
            window_score = max((SequenceMatcher(None, item, name).ratio() for item in windows), default=0.0)
            common = len(set(text) & set(name)) / max(len(set(name)), 1)
            return max(base, window_score, common * 0.85)

        with self.driver.session(database=self.database) as session:
            records = session.run(
                """
                MATCH (e:Entity)
                WHERE size(e.name) >= 2
                RETURN e.id AS id, e.name AS name, e.type AS type, e.definition AS definition
                LIMIT 2000
                """
            )
            candidates = []
            for record in records:
                row = dict(record)
                score = best_score(mention, row["name"])
                if mention in row["name"] or row["name"] in mention:
                    score += 0.2
                if score >= 0.58:
                    row["match_score"] = round(score, 4)
                    candidates.append(row)
            candidates.sort(key=lambda item: item["match_score"], reverse=True)
            return candidates[:limit]

    def neighborhood(self, entity_ids: Iterable[str], hops: int = 2, limit: int = 80) -> list[dict]:
        entity_ids = list(entity_ids)
        if not entity_ids:
            return []
        hops = max(1, min(hops, 2))
        query = f"""
        MATCH path=(n:Entity)-[*1..{hops}]-(m:Entity)
        WHERE n.id IN $entity_ids
        RETURN path
        LIMIT $limit
        """
        facts: list[dict] = []
        seen: set[tuple[str, str, str]] = set()
        with self.driver.session(database=self.database) as session:
            for record in session.run(query, entity_ids=entity_ids, limit=limit):
                path = record["path"]
                for rel in path.relationships:
                    start = rel.start_node
                    end = rel.end_node
                    key = (start.get("id"), rel.type, end.get("id"))
                    if key in seen:
                        continue
                    seen.add(key)
                    facts.append(
                        {
                            "type": "graph",
                            "head": start.get("name"),
                            "head_type": start.get("type"),
                            "relation": rel.get("relation") or rel.type,
                            "relation_type": rel.type,
                            "relation_zh": rel.get("relation_zh") or "",
                            "tail": end.get("name"),
                            "tail_type": end.get("type"),
                            "evidence": rel.get("evidence") or "",
                            "source_pages": rel.get("source_pages") or [],
                            "source_chunks": rel.get("source_chunks") or [],
                            "path": f"({start.get('name')})-[:{rel.type}]->({end.get('name')})",
                            "score": float(rel.get("confidence") or 0.75),
                        }
                    )
        return facts
