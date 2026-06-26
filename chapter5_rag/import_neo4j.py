from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parents[1]
CHAPTER5_DIR = ROOT / "chapter5_rag"
DEFAULT_GRAPH = CHAPTER5_DIR / "outputs" / "graph"
SCOPE = "chapter5"
ID_PREFIX = f"{SCOPE}::"

RELATION_LABELS = {
    "contains": "CONTAINS",
    "belongs_to": "BELONGS_TO",
    "used_for": "USED_FOR",
    "uses_tool": "USES_TOOL",
    "operates_on": "OPERATES_ON",
    "precedes": "PRECEDES",
    "follows": "FOLLOWS",
    "measures": "MEASURES",
    "controls": "CONTROLS",
    "provides_basis_for": "PROVIDES_BASIS_FOR",
    "composed_of": "COMPOSED_OF",
    "assembled_with": "ASSEMBLED_WITH",
    "located_at": "LOCATED_AT",
    "causes": "CAUSES",
    "checks": "CHECKS",
    "repairs": "REPAIRS",
}

TYPE_LABELS = {
    "Chapter": "Chapter",
    "ProcessObject": "ProcessObject",
    "Component": "Component",
    "Process": "Process",
    "Operation": "Operation",
    "ToolEquipment": "ToolEquipment",
    "Measurement": "Measurement",
    "Parameter": "Parameter",
    "Material": "Material",
    "QualityRequirement": "QualityRequirement",
    "Defect": "Defect",
    "StandardSafety": "StandardSafety",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def scoped_id(entity_id: str) -> str:
    return entity_id if entity_id.startswith(ID_PREFIX) else f"{ID_PREFIX}{entity_id}"


def load_env() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / "pangu" / ".env", override=False)
    load_dotenv(CHAPTER5_DIR / ".env", override=False)


def get_driver():
    load_env()
    uri = os.getenv("CHAPTER5_NEO4J_URI") or os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("CHAPTER5_NEO4J_USER") or os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("CHAPTER5_NEO4J_PASSWORD") or os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("CHAPTER5_NEO4J_DATABASE") or os.getenv("NEO4J_DATABASE", "neo4j")
    return GraphDatabase.driver(uri, auth=(user, password)), database


def prepare_entities(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared = []
    for row in rows:
        item = dict(row)
        item["original_id"] = row["id"]
        item["id"] = scoped_id(row["id"])
        item["scope"] = SCOPE
        item["source"] = "chapter5_pangu"
        prepared.append(item)
    return prepared


def prepare_relations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared = []
    for row in rows:
        rel_type = RELATION_LABELS.get(row.get("relation"))
        if not rel_type:
            continue
        item = dict(row)
        item["rel_type"] = rel_type
        item["head_id"] = scoped_id(row["head_id"])
        item["tail_id"] = scoped_id(row["tail_id"])
        item["scope"] = SCOPE
        item["source"] = "chapter5_pangu"
        prepared.append(item)
    return prepared


def ensure_schema(session) -> None:
    session.run("CREATE CONSTRAINT chapter5_entity_id_unique IF NOT EXISTS FOR (e:Chapter5Entity) REQUIRE e.id IS UNIQUE")
    session.run("CREATE INDEX chapter5_entity_name IF NOT EXISTS FOR (e:Chapter5Entity) ON (e.name)")
    session.run("CREATE INDEX chapter5_entity_type IF NOT EXISTS FOR (e:Chapter5Entity) ON (e.type)")
    session.run("CREATE INDEX chapter5_entity_scope IF NOT EXISTS FOR (e:Chapter5Entity) ON (e.scope)")


def clear_chapter5(session) -> None:
    session.run("MATCH (n:Chapter5Entity) DETACH DELETE n")


def import_entities(session, entities: list[dict[str, Any]], batch_size: int = 300) -> None:
    for start in range(0, len(entities), batch_size):
        batch = entities[start : start + batch_size]
        session.run(
            """
            UNWIND $batch AS row
            MERGE (e:Chapter5Entity {id: row.id})
            SET e.original_id = row.original_id,
                e.scope = row.scope,
                e.source = row.source,
                e.name = row.name,
                e.type = row.type,
                e.aliases = row.aliases,
                e.definition = row.definition,
                e.source_pages = row.source_pages,
                e.source_chunks = row.source_chunks,
                e.confidence = row.confidence
            """,
            batch=batch,
        )
    for typ, label in TYPE_LABELS.items():
        session.run(
            f"""
            MATCH (e:Chapter5Entity {{type: $typ}})
            SET e:{label}
            """,
            typ=typ,
        )


def import_relations(session, relations: list[dict[str, Any]], batch_size: int = 300) -> int:
    imported = 0
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in relations:
        grouped.setdefault(row["rel_type"], []).append(row)

    for rel_type, rows in grouped.items():
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            result = session.run(
                f"""
                UNWIND $batch AS row
                MATCH (h:Chapter5Entity {{id: row.head_id}})
                MATCH (t:Chapter5Entity {{id: row.tail_id}})
                MERGE (h)-[r:{rel_type} {{scope: row.scope, source: row.source}}]->(t)
                SET r.relation = row.relation,
                    r.relation_zh = row.relation_zh,
                    r.evidence = row.evidence,
                    r.source_pages = row.source_pages,
                    r.source_chunks = row.source_chunks,
                    r.confidence = row.confidence
                RETURN count(r) AS imported
                """,
                batch=batch,
            )
            imported += result.single()["imported"]
    return imported


def collect_stats(session) -> dict[str, int]:
    stats = session.run(
        """
        MATCH (n:Chapter5Entity)
        WITH count(n) AS nodes
        MATCH (:Chapter5Entity)-[r {scope: $scope}]->(:Chapter5Entity)
        RETURN nodes, count(r) AS relationships
        """,
        scope=SCOPE,
    ).single()
    return {"chapter5_nodes": stats["nodes"], "chapter5_relationships": stats["relationships"]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import chapter 5 KG into Neo4j without touching the full-book KG.")
    parser.add_argument("--graph-dir", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--clear-chapter5", action="store_true", help="Delete only Chapter 5 nodes before import.")
    parser.add_argument("--stats-only", action="store_true", help="Only print Chapter 5 graph stats in Neo4j.")
    args = parser.parse_args()

    driver, database = get_driver()
    with driver:
        with driver.session(database=database) as session:
            ensure_schema(session)
            if args.clear_chapter5:
                print("Clearing only Chapter 5 Neo4j subgraph...")
                clear_chapter5(session)
            if args.stats_only:
                print(collect_stats(session))
                return

            entities = prepare_entities(load_jsonl(args.graph_dir / "entities.jsonl"))
            relations = prepare_relations(load_jsonl(args.graph_dir / "relations.jsonl"))
            print(f"Importing Chapter 5 entities: {len(entities)}")
            import_entities(session, entities)
            print(f"Importing Chapter 5 relations: {len(relations)}")
            import_relations(session, relations)
            print(collect_stats(session))


if __name__ == "__main__":
    main()
