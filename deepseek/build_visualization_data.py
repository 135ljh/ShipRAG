from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "deepseek" / "outputs" / "graph"
VIS_DIR = ROOT / "deepseek" / "visualization"

TYPE_ORDER = [
    "Chapter",
    "Process",
    "ProcessObject",
    "Component",
    "Operation",
    "ToolEquipment",
    "Measurement",
    "Parameter",
    "QualityRequirement",
    "Defect",
    "Material",
    "StandardSafety",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    entities = read_jsonl(GRAPH_DIR / "entities.jsonl")
    relations = read_jsonl(GRAPH_DIR / "relations.jsonl")
    degree = Counter()
    for rel in relations:
        degree[rel["head_id"]] += 1
        degree[rel["tail_id"]] += 1

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entity in entities:
        by_type[entity.get("type", "Unknown")].append(entity)

    nodes = []
    type_count = len([typ for typ in TYPE_ORDER if by_type.get(typ)]) or 1
    type_index = 0
    for typ in TYPE_ORDER:
        items = sorted(by_type.get(typ, []), key=lambda item: (-degree[item["id"]], item["name"]))
        if not items:
            continue
        center_angle = (2 * math.pi * type_index) / type_count
        cx = math.cos(center_angle) * 900
        cy = math.sin(center_angle) * 650
        for idx, entity in enumerate(items):
            ring = 80 + 38 * math.sqrt(idx + 1)
            angle = center_angle + idx * 2.399963229728653
            nodes.append(
                {
                    "id": entity["id"],
                    "name": entity["name"],
                    "type": entity.get("type", "Unknown"),
                    "definition": entity.get("definition", ""),
                    "source_pages": entity.get("source_pages", []),
                    "confidence": entity.get("confidence", 0),
                    "degree": degree[entity["id"]],
                    "x": round(cx + math.cos(angle) * ring, 2),
                    "y": round(cy + math.sin(angle) * ring, 2),
                }
            )
        type_index += 1

    edges = [
        {
            "source": rel["head_id"],
            "target": rel["tail_id"],
            "relation": rel.get("relation", ""),
            "relation_zh": rel.get("relation_zh", rel.get("relation", "")),
            "evidence": rel.get("evidence", ""),
            "source_pages": rel.get("source_pages", []),
            "confidence": rel.get("confidence", 0),
            "head": rel.get("head", ""),
            "tail": rel.get("tail", ""),
        }
        for rel in relations
    ]

    summary = json.loads((GRAPH_DIR / "summary.json").read_text(encoding="utf-8"))
    payload = {
        "nodes": nodes,
        "edges": edges,
        "summary": summary,
    }
    VIS_DIR.mkdir(parents=True, exist_ok=True)
    (VIS_DIR / "graph_data.js").write_text(
        "window.DEEPSEEK_GRAPH = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    print(json.dumps({"nodes": len(nodes), "edges": len(edges), "out": str(VIS_DIR / "graph_data.js")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
