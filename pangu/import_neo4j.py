from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parents[1]
PANGU_DIR = ROOT / "pangu"
DEFAULT_GRAPH = PANGU_DIR / "outputs" / "graph"

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


def get_driver():
    load_dotenv(PANGU_DIR / ".env")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    database = os.getenv("NEO4J_DATABASE", "neo4j")
    return GraphDatabase.driver(uri, auth=(user, password)), database


def ensure_schema(session) -> None:
    session.run("CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
    session.run("CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)")
    session.run("CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.type)")


def clear_graph(session) -> None:
    session.run("MATCH (n) DETACH DELETE n")


def import_entities(session, entities: list[dict[str, Any]], batch_size: int = 500) -> None:
    for start in range(0, len(entities), batch_size):
        batch = entities[start : start + batch_size]
        session.run(
            """
            UNWIND $batch AS row
            MERGE (e:Entity {id: row.id})
            SET e.name = row.name,
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
            MATCH (e:Entity {{type: $typ}})
            SET e:{label}
            """,
            typ=typ,
        )


def import_relations(session, relations: list[dict[str, Any]], batch_size: int = 500) -> None:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in relations:
        rel_type = RELATION_LABELS.get(row["relation"])
        if rel_type:
            grouped.setdefault(rel_type, []).append(row)

    for rel_type, rows in grouped.items():
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            session.run(
                f"""
                UNWIND $batch AS row
                MATCH (h:Entity {{id: row.head_id}})
                MATCH (t:Entity {{id: row.tail_id}})
                MERGE (h)-[r:{rel_type}]->(t)
                SET r.relation = row.relation,
                    r.relation_zh = row.relation_zh,
                    r.evidence = row.evidence,
                    r.source_pages = row.source_pages,
                    r.source_chunks = row.source_chunks,
                    r.confidence = row.confidence
                """,
                batch=batch,
            )


def fallback_add_labels(session) -> None:
    for typ, label in TYPE_LABELS.items():
        session.run(
            f"""
            MATCH (e:Entity {{type: $typ}})
            SET e:{label}
            """,
            typ=typ,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import ShipRAG Pangu KG into Neo4j.")
    parser.add_argument("--graph-dir", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument("--clear", action="store_true", help="Clear existing Neo4j graph before import.")
    parser.add_argument("--clear-only", action="store_true", help="Only clear existing Neo4j graph, then exit.")
    args = parser.parse_args()

    driver, database = get_driver()

    with driver:
        with driver.session(database=database) as session:
            if args.clear or args.clear_only:
                print("Clearing existing Neo4j graph...")
                clear_graph(session)
            if args.clear_only:
                print("Neo4j graph cleared.")
                return
            entities = load_jsonl(args.graph_dir / "entities.jsonl")
            relations = load_jsonl(args.graph_dir / "relations.jsonl")
            ensure_schema(session)
            print(f"Importing {len(entities)} entities...")
            import_entities(session, entities)
            print(f"Importing {len(relations)} relations...")
            import_relations(session, relations)
            stats = session.run(
                """
                MATCH (n)
                WITH count(n) AS nodes
                MATCH ()-[r]->()
                RETURN nodes, count(r) AS relationships
                """
            ).single()
            print({"nodes": stats["nodes"], "relationships": stats["relationships"]})


if __name__ == "__main__":
    main()
