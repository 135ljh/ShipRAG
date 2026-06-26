from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
GRAPH_DIR = BASE_DIR / "outputs" / "graph"
VIS_DIR = BASE_DIR / "visualization"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    entities = read_jsonl(GRAPH_DIR / "entities.jsonl")
    relations = read_jsonl(GRAPH_DIR / "relations.jsonl")
    summary = json.loads((GRAPH_DIR / "summary.json").read_text(encoding="utf-8"))
    degree = Counter()
    for rel in relations:
        degree[rel["head_id"]] += 1
        degree[rel["tail_id"]] += 1

    type_order = sorted({entity["type"] for entity in entities})
    type_index = {typ: idx for idx, typ in enumerate(type_order)}
    nodes = []
    for idx, entity in enumerate(entities):
        group = type_index.get(entity["type"], 0)
        angle = (idx * 137.508 + group * 31) * math.pi / 180
        radius = 180 + group * 95 + (idx % 13) * 12
        nodes.append(
            {
                "id": entity["id"],
                "name": entity["name"],
                "type": entity["type"],
                "definition": entity.get("definition", ""),
                "source_pages": entity.get("source_pages", []),
                "degree": degree[entity["id"]],
                "x": round(math.cos(angle) * radius, 2),
                "y": round(math.sin(angle) * radius, 2),
            }
        )
    edges = [
        {
            "source": rel["head_id"],
            "target": rel["tail_id"],
            "relation": rel["relation"],
            "relation_zh": rel.get("relation_zh") or rel["relation"],
            "evidence": rel.get("evidence", ""),
            "source_chunks": rel.get("source_chunks", []),
            "source_pages": rel.get("source_pages", []),
            "confidence": rel.get("confidence", 0),
        }
        for rel in relations
    ]
    payload = {
        "title": "第五章 船体分段的装配知识图谱",
        "summary": summary,
        "nodes": nodes,
        "edges": edges,
    }
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    (VIS_DIR / "graph_data.js").write_text(
        "window.CHAPTER5_GRAPH = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(json.dumps({"nodes": len(nodes), "edges": len(edges), "out": str(VIS_DIR / "graph_data.js")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
