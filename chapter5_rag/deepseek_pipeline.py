from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

import json5
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "deepseek_outputs"
GRAPH_DIR = OUTPUT_DIR / "graph"

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
ALLOWED_RELATIONS = set(RELATION_ZH)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def compact_name(value: Any) -> str:
    text = re.sub(r"\s+", "", str(value or ""))
    return text.strip(".,;:，。；：、（）()[]【】")[:80]


def entity_id(name: str, typ: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", f"{typ}_{name}")
    return safe.strip("_")[:120]


def is_bad_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 42:
        return True
    return bool(re.fullmatch(r"[\d.\-_/]+", name))


def clean_conf(value: Any, default: float = 0.78) -> float:
    try:
        number = float(value)
    except Exception:
        number = default
    if number > 1:
        number /= 100
    return max(0.0, min(1.0, number))


def extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("No JSON object found.")
    candidate = re.sub(r",\s*([}\]])", r"\1", match.group(0))
    try:
        return json.loads(candidate)
    except Exception:
        return json5.loads(candidate)


class DeepSeekClient:
    def __init__(self) -> None:
        load_dotenv(ROOT / ".env")
        load_dotenv(BASE_DIR / ".env", override=False)
        self.api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("CHAPTER5_DEEPSEEK_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY.")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "180"))

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 900, temperature: float = 0.0) -> str:
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def extraction_messages(chunk: dict[str, Any]) -> list[dict[str, str]]:
    system = """你是船体分段装配工艺知识图谱抽取专家。只依据输入文本抽取实体和知识三元组。
只输出合法 JSON，不要 Markdown，不要解释。
实体类型只能使用：Chapter, ProcessObject, Component, Process, Operation, ToolEquipment, Measurement, Parameter, Material, QualityRequirement, Defect, StandardSafety。
关系类型只能使用：contains, belongs_to, used_for, uses_tool, operates_on, precedes, follows, measures, controls, provides_basis_for, composed_of, assembled_with, located_at, causes, checks, repairs。
每个文本块最多输出 5 个实体、6 条三元组。优先保留能形成工艺网络的知识：装配方式、适用条件、步骤、构件、工具、测量、质量控制、焊接变形控制。
每条三元组必须有 evidence、source_page、source_chunk、confidence。confidence 为 0 到 1。"""
    user = f"""source_chunk: {chunk["id"]}
source_page: {chunk["page_start"]}
chapter_hint: {chunk.get("chapter_hint", "")}

text:
{chunk["text"]}

JSON 格式：
{{
  "entities": [
    {{"name": "实体名", "type": "实体类型", "aliases": [], "definition": "基于原文的一句话定义", "source_page": {chunk["page_start"]}, "source_chunk": "{chunk["id"]}", "confidence": 0.9}}
  ],
  "triples": [
    {{"head": "头实体", "head_type": "头实体类型", "relation": "关系类型", "tail": "尾实体", "tail_type": "尾实体类型", "evidence": "原文证据短句", "source_page": {chunk["page_start"]}, "source_chunk": "{chunk["id"]}", "confidence": 0.9}}
  ]
}}"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def load_done(path: Path) -> set[str]:
    return {row.get("source_chunk", "") for row in load_jsonl(path) if not row.get("error")}


def command_extract(args: argparse.Namespace) -> None:
    chunks = load_jsonl(DATA_DIR / "chapter5_chunks.jsonl")
    if args.limit:
        chunks = chunks[: args.limit]
    out = OUTPUT_DIR / "raw_extractions.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(out)
    client = DeepSeekClient()
    print(f"DeepSeek model: {client.model}")
    with out.open("a", encoding="utf-8") as fh:
        for index, chunk in enumerate(chunks, start=1):
            if chunk["id"] in done:
                print(f"skip {chunk['id']} ({index}/{len(chunks)})")
                continue
            raw = ""
            last_error: Exception | None = None
            for attempt in range(1, args.retries + 1):
                try:
                    raw = client.chat(extraction_messages(chunk), max_tokens=args.max_tokens, temperature=0.0)
                    parsed = extract_json(raw)
                    row = {
                        "source_chunk": chunk["id"],
                        "source_page": chunk["page_start"],
                        "chapter_hint": chunk.get("chapter_hint", ""),
                        "text": chunk["text"],
                        "raw_response": raw,
                        "entities": parsed.get("entities", []),
                        "triples": parsed.get("triples", []),
                    }
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                    fh.flush()
                    print(f"done {chunk['id']} entities={len(row['entities'])} triples={len(row['triples'])}")
                    break
                except Exception as exc:
                    last_error = exc
                    print(f"retry {chunk['id']} attempt={attempt} error={type(exc).__name__}: {exc}")
                    time.sleep(args.sleep * attempt + 1)
            else:
                fh.write(json.dumps({
                    "source_chunk": chunk["id"],
                    "source_page": chunk["page_start"],
                    "chapter_hint": chunk.get("chapter_hint", ""),
                    "text": chunk["text"],
                    "raw_response": raw,
                    "error": repr(last_error),
                    "entities": [],
                    "triples": [],
                }, ensure_ascii=False) + "\n")
                fh.flush()
                print(f"failed {chunk['id']}: {last_error!r}")
            time.sleep(args.sleep)


def add_entity(entities: dict[tuple[str, str], dict[str, Any]], name: Any, typ: Any, page: Any, chunk: str, definition: str, confidence: float) -> None:
    name = compact_name(name)
    typ = str(typ) if typ in ALLOWED_ENTITY_TYPES else "ProcessObject"
    if is_bad_name(name):
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
    if page:
        entities[key]["source_pages"].add(int(page))
    if chunk:
        entities[key]["source_chunks"].add(chunk)
    if definition and not entities[key]["definition"]:
        entities[key]["definition"] = definition
    entities[key]["confidence_values"].append(confidence)


def add_relation(relations: dict[tuple[str, str, str, str, str], dict[str, Any]], row: dict[str, Any], page: Any, chunk: str, confidence: float) -> None:
    head = compact_name(row.get("head") or row.get("subject"))
    tail = compact_name(row.get("tail") or row.get("object"))
    relation = str(row.get("relation") or row.get("predicate") or "").strip()
    head_type = row.get("head_type") or row.get("subject_type") or "ProcessObject"
    tail_type = row.get("tail_type") or row.get("object_type") or "ProcessObject"
    head_type = head_type if head_type in ALLOWED_ENTITY_TYPES else "ProcessObject"
    tail_type = tail_type if tail_type in ALLOWED_ENTITY_TYPES else "ProcessObject"
    if relation not in ALLOWED_RELATIONS or is_bad_name(head) or is_bad_name(tail) or head == tail:
        return
    key = (head, head_type, relation, tail, tail_type)
    if key not in relations:
        relations[key] = {
            "head": head,
            "head_type": head_type,
            "relation": relation,
            "relation_zh": RELATION_ZH[relation],
            "tail": tail,
            "tail_type": tail_type,
            "evidence": row.get("evidence", ""),
            "source_pages": set(),
            "source_chunks": set(),
            "confidence_values": [],
        }
    if page:
        relations[key]["source_pages"].add(int(page))
    if chunk:
        relations[key]["source_chunks"].add(chunk)
    evidence = row.get("evidence", "")
    if evidence and len(evidence) > len(relations[key]["evidence"]):
        relations[key]["evidence"] = evidence
    relations[key]["confidence_values"].append(confidence)


def command_build_graph(args: argparse.Namespace) -> None:
    raw_rows = load_jsonl(OUTPUT_DIR / "raw_extractions.jsonl")
    entities: dict[tuple[str, str], dict[str, Any]] = {}
    relations: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    document = "第五章船体分段的装配"
    add_entity(entities, document, "Chapter", 1, "", "第五章知识单元", 1.0)
    for raw in raw_rows:
        if raw.get("error"):
            continue
        page = raw.get("source_page")
        chunk = raw.get("source_chunk", "")
        chapter = raw.get("chapter_hint") or document
        add_entity(entities, chapter, "Chapter", page, chunk, "", 0.95)
        add_relation(relations, {"head": document, "head_type": "Chapter", "relation": "contains", "tail": chapter, "tail_type": "Chapter", "evidence": "第五章包含该知识单元"}, page, chunk, 0.95)
        for item in raw.get("entities", []) or []:
            conf = clean_conf(item.get("confidence"))
            if conf < args.min_confidence:
                continue
            add_entity(entities, item.get("name"), item.get("type"), item.get("source_page") or page, item.get("source_chunk") or chunk, item.get("definition", ""), conf)
            add_relation(relations, {"head": chapter, "head_type": "Chapter", "relation": "contains", "tail": item.get("name"), "tail_type": item.get("type"), "evidence": "实体出现在该章节文本块中"}, page, chunk, min(conf, 0.82))
        for triple in raw.get("triples", []) or []:
            conf = clean_conf(triple.get("confidence"))
            if conf < args.min_confidence:
                continue
            head_type = triple.get("head_type") or "ProcessObject"
            tail_type = triple.get("tail_type") or "ProcessObject"
            add_entity(entities, triple.get("head"), head_type, triple.get("source_page") or page, triple.get("source_chunk") or chunk, "", conf)
            add_entity(entities, triple.get("tail"), tail_type, triple.get("source_page") or page, triple.get("source_chunk") or chunk, "", conf)
            add_relation(relations, triple, triple.get("source_page") or page, triple.get("source_chunk") or chunk, conf)

    entity_rows: list[dict[str, Any]] = []
    for item in entities.values():
        confs = item.pop("confidence_values")
        item["aliases"] = sorted(item["aliases"])
        item["source_pages"] = sorted(item["source_pages"])
        item["source_chunks"] = sorted(item["source_chunks"])
        item["confidence"] = round(sum(confs) / len(confs), 4) if confs else 0.75
        entity_rows.append(item)

    id_lookup = {(item["name"], item["type"]): item["id"] for item in entity_rows}
    relation_rows: list[dict[str, Any]] = []
    for item in relations.values():
        confs = item.pop("confidence_values")
        item["source_pages"] = sorted(item["source_pages"])
        item["source_chunks"] = sorted(item["source_chunks"])
        item["confidence"] = round(sum(confs) / len(confs), 4) if confs else 0.75
        item["head_id"] = id_lookup.get((item["head"], item["head_type"]), entity_id(item["head"], item["head_type"]))
        item["tail_id"] = id_lookup.get((item["tail"], item["tail_type"]), entity_id(item["tail"], item["tail_type"]))
        relation_rows.append(item)

    entity_rows.sort(key=lambda item: (item["type"], item["name"]))
    relation_rows.sort(key=lambda item: (item["relation"], item["head"], item["tail"]))
    write_jsonl(GRAPH_DIR / "entities.jsonl", entity_rows)
    write_jsonl(GRAPH_DIR / "relations.jsonl", relation_rows)
    degree = Counter()
    for rel in relation_rows:
        degree[rel["head_id"]] += 1
        degree[rel["tail_id"]] += 1
    summary = {
        "provider": "deepseek",
        "raw_rows": len(raw_rows),
        "failed_rows": sum(1 for row in raw_rows if row.get("error")),
        "entities": len(entity_rows),
        "relations": len(relation_rows),
        "isolated_entities": sum(1 for row in entity_rows if degree[row["id"]] == 0),
        "entity_type_counts": Counter(row["type"] for row in entity_rows),
        "relation_type_counts": Counter(row["relation"] for row in relation_rows),
        "top_connected_entities": [{"id": key, "degree": value} for key, value in degree.most_common(15)],
    }
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    (GRAPH_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Chapter 5 DeepSeek KG extraction pipeline.")
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("--limit", type=int, default=0)
    extract.add_argument("--retries", type=int, default=2)
    extract.add_argument("--sleep", type=float, default=0.2)
    extract.add_argument("--max-tokens", type=int, default=1100)
    extract.set_defaults(func=command_extract)
    graph = sub.add_parser("build-graph")
    graph.add_argument("--min-confidence", type=float, default=0.55)
    graph.set_defaults(func=command_build_graph)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
