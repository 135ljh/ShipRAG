from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
ROUND2_DIR = BASE_DIR / "outputs" / "round2"
EVAL_DIR = BASE_DIR / "eval"
REPORT_DIR = BASE_DIR / "reports"

GENERIC_RELATIONS = {"相关", "相关于", "有关", "属于", "包含", "包括", "是", "影响", "作用"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def find_file(model: str, preferred_name: str) -> Path | None:
    preferred = ROUND2_DIR / model / preferred_name
    if preferred.exists():
        return preferred
    model_dir = ROUND2_DIR / model
    if not model_dir.exists():
        return None
    candidates = sorted(model_dir.glob("*.jsonl")) + sorted(model_dir.glob("*.json"))
    for path in candidates:
        if "triple" in path.name or "relation" in path.name:
            return path
    return candidates[0] if candidates else None


def relation(row: dict[str, Any]) -> str:
    return str(row.get("relation") or row.get("predicate") or "").strip()


def head(row: dict[str, Any]) -> str:
    return str(row.get("head") or row.get("subject") or "").strip()


def tail(row: dict[str, Any]) -> str:
    return str(row.get("tail") or row.get("object") or "").strip()


def connected_components(nodes: set[str], edges: set[tuple[str, str]]) -> list[set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        if a == b:
            graph[a].add(b)
        else:
            graph[a].add(b)
            graph[b].add(a)
    seen = set()
    components = []
    for node in nodes:
        if node in seen:
            continue
        comp = set()
        queue = deque([node])
        seen.add(node)
        while queue:
            current = queue.popleft()
            comp.add(current)
            for nxt in graph.get(current, set()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        components.append(comp)
    return components


def evaluate_model(model: str) -> dict[str, Any]:
    triple_path = find_file(model, "kg_triples.jsonl")
    entity_path = find_file(model, "kg_entities.jsonl")
    if not triple_path:
        return {"available": False, "reason": f"No triple file found under {ROUND2_DIR / model}"}

    triples = read_jsonl(triple_path)
    entity_rows = read_jsonl(entity_path) if entity_path else []
    entities = {str(row.get("name", "")).strip() for row in entity_rows if str(row.get("name", "")).strip()}
    triple_keys = []
    edges = set()
    relation_counter = Counter()
    self_loops = 0
    generic = 0
    for row in triples:
        h = head(row)
        t = tail(row)
        r = relation(row)
        if not (h and r and t):
            continue
        entities.add(h)
        entities.add(t)
        triple_keys.append((h, r, t))
        edges.add((h, t))
        relation_counter[r] += 1
        if h == t:
            self_loops += 1
        if r in GENERIC_RELATIONS:
            generic += 1

    entity_count = len(entities)
    triple_count = len(triple_keys)
    unique_triples = set(triple_keys)
    duplicate_count = triple_count - len(unique_triples)
    degree = Counter()
    for h, t in edges:
        if h == t:
            degree[h] += 2
        else:
            degree[h] += 1
            degree[t] += 1
    isolated = [node for node in entities if degree[node] == 0]
    components = connected_components(entities, edges) if entities else []
    largest = max((len(comp) for comp in components), default=0)
    return {
        "available": True,
        "triple_file": str(triple_path),
        "entity_file": str(entity_path) if entity_path else None,
        "entity_count": entity_count,
        "triple_count": triple_count,
        "relation_type_count": len(relation_counter),
        "average_degree": round(sum(degree.values()) / entity_count, 4) if entity_count else 0.0,
        "largest_component_ratio": round(largest / entity_count, 4) if entity_count else 0.0,
        "isolated_entity_ratio": round(len(isolated) / entity_count, 4) if entity_count else 0.0,
        "duplicate_triple_ratio": round(duplicate_count / triple_count, 4) if triple_count else 0.0,
        "self_loop_ratio": round(self_loops / triple_count, 4) if triple_count else 0.0,
        "generic_relation_ratio": round(generic / triple_count, 4) if triple_count else 0.0,
        "relation_counts": dict(relation_counter),
    }


def render_report(metrics: dict[str, Any]) -> str:
    lines = [
        "# 第五章 Round2 图谱结构质量报告",
        "",
        "本报告读取 `outputs/round2/pangu/kg_triples.jsonl` 与 `outputs/round2/deepseek/kg_triples.jsonl`，评估 Pangu 与 DeepSeek 第二轮抽取结果形成的图谱结构质量。",
        "",
        "| 方案 | 实体数 | 三元组数 | 关系类型数 | 平均度数 | 最大连通子图比例 | 孤立实体比例 | 重复三元组比例 | 自环比例 | 泛化关系比例 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    label = {"pangu": "B_pangu_graph_rag", "deepseek": "C_deepseek_graph_rag"}
    for model in ("pangu", "deepseek"):
        row = metrics.get(model, {})
        if not row.get("available"):
            lines.append(f"| {label[model]} | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 |")
            continue
        lines.append(
            f"| {label[model]} | {row['entity_count']} | {row['triple_count']} | {row['relation_type_count']} | {row['average_degree']:.4f} | {row['largest_component_ratio']:.2%} | {row['isolated_entity_ratio']:.2%} | {row['duplicate_triple_ratio']:.2%} | {row['self_loop_ratio']:.2%} | {row['generic_relation_ratio']:.2%} |"
        )
    lines.extend(
        [
            "",
            "说明：泛化关系包括“相关、相关于、有关、属于、包含、包括、是、影响、作用”。该比例过高不一定表示错误，但说明关系语义可能不够具体，图谱可能较松散。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    metrics = {model: evaluate_model(model) for model in ("pangu", "deepseek")}
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "graph_quality_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (REPORT_DIR / "graph_quality_report.md").write_text(render_report(metrics), encoding="utf-8")
    print(json.dumps({"metrics": str(EVAL_DIR / "graph_quality_metrics.json"), "report": str(REPORT_DIR / "graph_quality_report.md")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
