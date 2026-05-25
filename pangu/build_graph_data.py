from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PANGU_DIR = ROOT / "pangu"
DEFAULT_RAW = PANGU_DIR / "outputs" / "raw_extractions.jsonl"
DEFAULT_OUT_DIR = PANGU_DIR / "outputs" / "graph"

ALLOWED_ENTITY_TYPES = {
    "Chapter",
    "ProcessObject",
    "Component",
    "Process",
    "Operation",
    "ToolEquipment",
    "Measurement",
    "Parameter",
    "Material",
    "QualityRequirement",
    "Defect",
    "StandardSafety",
}

ALLOWED_RELATIONS = {
    "contains",
    "belongs_to",
    "used_for",
    "uses_tool",
    "operates_on",
    "precedes",
    "follows",
    "measures",
    "controls",
    "provides_basis_for",
    "composed_of",
    "assembled_with",
    "located_at",
    "causes",
    "checks",
    "repairs",
}

PUBLISHING_TERMS = {
    "ISBN",
    "出版社",
    "责任编辑",
    "出版发行",
    "定价",
    "CIP",
    "哈尔滨工程大学出版社",
}

RELATION_ZH = {
    "contains": "包含",
    "belongs_to": "属于",
    "used_for": "用于",
    "uses_tool": "使用工具",
    "operates_on": "操作对象",
    "precedes": "前置工序",
    "follows": "后续工序",
    "measures": "测量指标",
    "controls": "控制指标",
    "provides_basis_for": "产生依据",
    "composed_of": "由……组成",
    "assembled_with": "连接/装配",
    "located_at": "位置关系",
    "causes": "导致",
    "checks": "检查/评估",
    "repairs": "修理对象",
}

OCR_NORMALIZATION = {
    "航侧分段": "舷侧分段",
    "触侧分段": "舷侧分段",
    "炫侧分段": "舷侧分段",
    "眩侧分段": "舷侧分段",
    "助骨": "肋骨",
    "助位": "肋位",
    "肋位线": "肋骨线",
    "鞘舰": "艏艉",
    "鞘、舰": "艏、艉",
    "船广": "船厂",
    "面线": "画线",
    "放祥": "放样",
    "胎粱": "胎架",
}


def norm_name(name: Any) -> str:
    value = str(name or "").strip()
    value = re.sub(r"\s+", "", value)
    value = value.strip(".,;:，。；：、()（）[]【】")
    for src, dst in OCR_NORMALIZATION.items():
        value = value.replace(src, dst)
    return value


def norm_relation(relation: Any) -> str:
    rel = str(relation or "").strip()
    zh_to_en = {v: k for k, v in RELATION_ZH.items()}
    return zh_to_en.get(rel, rel)


def clean_conf(value: Any, default: float = 0.75) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    if number > 1:
        number = number / 100
    return max(0.0, min(1.0, number))


def is_bad_entity(name: str) -> bool:
    if not name or len(name) < 2:
        return True
    if len(name) > 40:
        return True
    if any(term in name for term in PUBLISHING_TERMS):
        return True
    if re.fullmatch(r"[\d.\-_/]+", name):
        return True
    return False


def entity_id(name: str, typ: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", f"{typ}_{name}")
    return safe.strip("_")[:120]


def load_raw(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Raw extraction file not found: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_entity(
    entities: dict[tuple[str, str], dict[str, Any]],
    name: str,
    typ: str,
    source_page: Any = None,
    source_chunk: str = "",
    definition: str = "",
    confidence: float = 0.75,
) -> None:
    name = norm_name(name)
    typ = typ if typ in ALLOWED_ENTITY_TYPES else "ProcessObject"
    if is_bad_entity(name):
        return
    key = (name, typ)
    if key not in entities:
        entities[key] = {
            "id": entity_id(name, typ),
            "name": name,
            "type": typ,
            "aliases": set(),
            "definition": definition or "",
            "source_pages": set(),
            "source_chunks": set(),
            "confidence_values": [],
        }
    if source_page:
        entities[key]["source_pages"].add(int(source_page))
    if source_chunk:
        entities[key]["source_chunks"].add(source_chunk)
    if definition and not entities[key]["definition"]:
        entities[key]["definition"] = definition
    entities[key]["confidence_values"].append(confidence)


def add_relation(
    relations: dict[tuple[str, str, str, str, str], dict[str, Any]],
    head: str,
    head_type: str,
    relation: str,
    tail: str,
    tail_type: str,
    evidence: str = "",
    source_page: Any = None,
    source_chunk: str = "",
    confidence: float = 0.75,
) -> None:
    head = norm_name(head)
    tail = norm_name(tail)
    relation = norm_relation(relation)
    if relation not in ALLOWED_RELATIONS:
        return
    if is_bad_entity(head) or is_bad_entity(tail) or head == tail:
        return
    key = (head, head_type, relation, tail, tail_type)
    if key not in relations:
        relations[key] = {
            "head": head,
            "head_type": head_type,
            "relation": relation,
            "relation_zh": RELATION_ZH.get(relation, relation),
            "tail": tail,
            "tail_type": tail_type,
            "evidence": evidence or "",
            "source_pages": set(),
            "source_chunks": set(),
            "confidence_values": [],
        }
    if source_page:
        relations[key]["source_pages"].add(int(source_page))
    if source_chunk:
        relations[key]["source_chunks"].add(source_chunk)
    if evidence and len(evidence) > len(relations[key]["evidence"]):
        relations[key]["evidence"] = evidence
    relations[key]["confidence_values"].append(confidence)


def build_graph(raw_rows: list[dict[str, Any]], min_confidence: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    entities: dict[tuple[str, str], dict[str, Any]] = {}
    relations: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    document_name = "中级船体装配工工艺学"
    add_entity(entities, document_name, "Chapter", confidence=1.0)

    for row in raw_rows:
        chunk = row.get("source_chunk", "")
        page = row.get("source_page")
        chapter = norm_name(row.get("chapter_hint", ""))
        if chapter:
            add_entity(entities, chapter, "Chapter", page, chunk, confidence=0.95)
            add_relation(relations, document_name, "Chapter", "contains", chapter, "Chapter", "教材章节", page, chunk, 0.95)

        for ent in row.get("entities", []) or []:
            name = norm_name(ent.get("name"))
            typ = ent.get("type")
            conf = clean_conf(ent.get("confidence"))
            if conf < min_confidence:
                continue
            add_entity(
                entities,
                name,
                typ,
                ent.get("source_page") or page,
                ent.get("source_chunk") or chunk,
                ent.get("definition", ""),
                conf,
            )
            if chapter and name:
                add_relation(relations, chapter, "Chapter", "contains", name, typ, "实体出现在该章节文本块中", page, chunk, 0.8)

        for tri in row.get("triples", []) or []:
            head = norm_name(tri.get("head") or tri.get("subject"))
            tail = norm_name(tri.get("tail") or tri.get("object"))
            head_type = tri.get("head_type") or tri.get("subject_type") or "ProcessObject"
            tail_type = tri.get("tail_type") or tri.get("object_type") or "ProcessObject"
            conf = clean_conf(tri.get("confidence"))
            if conf < min_confidence:
                continue
            add_entity(entities, head, head_type, tri.get("source_page") or page, tri.get("source_chunk") or chunk, confidence=conf)
            add_entity(entities, tail, tail_type, tri.get("source_page") or page, tri.get("source_chunk") or chunk, confidence=conf)
            add_relation(
                relations,
                head,
                head_type,
                tri.get("relation") or tri.get("predicate"),
                tail,
                tail_type,
                tri.get("evidence", ""),
                tri.get("source_page") or page,
                tri.get("source_chunk") or chunk,
                conf,
            )
            if chapter:
                add_relation(relations, chapter, "Chapter", "contains", head, head_type, "三元组头实体出现在该章节", page, chunk, 0.8)
                add_relation(relations, chapter, "Chapter", "contains", tail, tail_type, "三元组尾实体出现在该章节", page, chunk, 0.8)

    entity_rows = []
    for item in entities.values():
        confs = item.pop("confidence_values")
        item["source_pages"] = sorted(item["source_pages"])
        item["source_chunks"] = sorted(item["source_chunks"])
        item["aliases"] = sorted(item["aliases"])
        item["confidence"] = round(sum(confs) / len(confs), 4) if confs else 0.75
        entity_rows.append(item)

    relation_rows = []
    for item in relations.values():
        confs = item.pop("confidence_values")
        item["source_pages"] = sorted(item["source_pages"])
        item["source_chunks"] = sorted(item["source_chunks"])
        item["confidence"] = round(sum(confs) / len(confs), 4) if confs else 0.75
        item["head_id"] = entity_id(item["head"], item["head_type"])
        item["tail_id"] = entity_id(item["tail"], item["tail_type"])
        relation_rows.append(item)

    entity_rows.sort(key=lambda x: (x["type"], x["name"]))
    relation_rows.sort(key=lambda x: (x["relation"], x["head"], x["tail"]))
    return entity_rows, relation_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            converted = dict(row)
            for key, value in converted.items():
                if isinstance(value, (list, dict)):
                    converted[key] = json.dumps(value, ensure_ascii=False)
            writer.writerow(converted)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize Pangu extraction results into graph-ready data.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    args = parser.parse_args()

    raw_rows = load_raw(args.raw)
    entities, relations = build_graph(raw_rows, args.min_confidence)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(args.out_dir / "entities.jsonl", entities)
    write_jsonl(args.out_dir / "relations.jsonl", relations)
    write_csv(
        args.out_dir / "entities.csv",
        entities,
        ["id", "name", "type", "aliases", "definition", "source_pages", "source_chunks", "confidence"],
    )
    write_csv(
        args.out_dir / "relations.csv",
        relations,
        [
            "head_id",
            "tail_id",
            "head",
            "head_type",
            "relation",
            "relation_zh",
            "tail",
            "tail_type",
            "evidence",
            "source_pages",
            "source_chunks",
            "confidence",
        ],
    )

    degree = Counter()
    for rel in relations:
        degree[rel["head_id"]] += 1
        degree[rel["tail_id"]] += 1
    isolated = [e for e in entities if degree[e["id"]] == 0]
    summary = {
        "raw_rows": len(raw_rows),
        "entities": len(entities),
        "relations": len(relations),
        "isolated_entities": len(isolated),
        "top_connected_entities": [
            {"id": eid, "degree": deg} for eid, deg in degree.most_common(20)
        ],
        "relation_type_counts": Counter(rel["relation"] for rel in relations),
        "entity_type_counts": Counter(ent["type"] for ent in entities),
    }
    (args.out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

