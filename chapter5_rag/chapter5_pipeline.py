from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import json5
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
GRAPH_DIR = OUTPUT_DIR / "graph"
PROMPT_PATH = BASE_DIR / "prompts" / "kg_extraction_prompt.md"

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


def read_text_auto(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def find_source() -> Path:
    files = sorted(BASE_DIR.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt source file found in {BASE_DIR}")
    return files[0]


def compact(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_chunks(text: str, max_chars: int = 900, overlap: int = 120) -> list[dict[str, Any]]:
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    chunks: list[dict[str, Any]] = []
    buffer = ""
    section = ""
    page = 1
    expanded: list[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            expanded.append(para)
            continue
        start = 0
        while start < len(para):
            end = min(start + max_chars, len(para))
            expanded.append(para[start:end])
            if end == len(para):
                break
            start = max(end - overlap, start + 1)

    for para in expanded:
        if para.startswith("#"):
            section = re.sub(r"^#+\s*", "", para).strip() or section
            continue
        if len(buffer) + len(para) + 2 <= max_chars:
            buffer = f"{buffer}\n\n{para}".strip()
            continue
        if buffer:
            chunks.append(make_chunk(buffer, section, page, len(chunks) + 1))
            page += 1
            buffer = buffer[-overlap:] + "\n\n" + para if overlap else para
        else:
            chunks.append(make_chunk(para[:max_chars], section, page, len(chunks) + 1))
            page += 1
            buffer = para[max_chars - overlap :]
    if buffer:
        chunks.append(make_chunk(buffer, section, page, len(chunks) + 1))
    return chunks


def make_chunk(text: str, section: str, page: int, index: int) -> dict[str, Any]:
    return {
        "id": f"chapter5_{index:03d}",
        "source": find_source().name,
        "page_start": page,
        "page_end": page,
        "chapter_hint": section or "第五章 船体分段的装配",
        "text": text.strip(),
        "char_count": len(text.strip()),
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    text = text.replace("[unused16]", "").replace("[unused17]", "").replace("[unused10]", "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("No JSON object found in model output.")
    candidate = match.group(0)
    try:
        return json.loads(candidate)
    except Exception:
        repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json5.loads(repaired)
        except Exception:
            salvaged = salvage_partial_json(candidate)
            if salvaged["entities"] or salvaged["triples"]:
                return salvaged
            raise


def salvage_partial_json(text: str) -> dict[str, Any]:
    def objects_after(marker: str) -> list[dict[str, Any]]:
        index = text.find(marker)
        if index < 0:
            return []
        section = text[index:]
        objs = []
        depth = 0
        start = None
        in_string = False
        escaped = False
        for pos, ch in enumerate(section):
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                continue
            if ch == "{":
                if depth == 0:
                    start = pos
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    raw_obj = section[start : pos + 1]
                    try:
                        objs.append(json.loads(raw_obj))
                    except Exception:
                        try:
                            objs.append(json5.loads(raw_obj))
                        except Exception:
                            pass
                    start = None
        return objs

    entities = objects_after('"entities"')
    triples = objects_after('"triples"')
    entity_keys = {"name", "type"}
    triple_keys = {"head", "relation", "tail"}
    entities = [obj for obj in entities if entity_keys <= set(obj)]
    triples = [obj for obj in triples if triple_keys <= set(obj)]
    return {"entities": entities, "triples": triples}


class PanguClient:
    def __init__(self) -> None:
        load_dotenv(ROOT / "pangu" / ".env")
        load_dotenv(BASE_DIR / ".env")
        self.base_url = os.getenv("PANGU_BASE_URL", "http://10.21.77.7:8000").rstrip("/")
        self.generate_path = os.getenv("PANGU_GENERATE_PATH", "/generate")
        self.health_path = os.getenv("PANGU_HEALTH_PATH", "/health")
        self.timeout = int(os.getenv("PANGU_TIMEOUT", "240"))

    def health(self) -> str:
        response = requests.get(f"{self.base_url}{self.health_path}", timeout=20)
        response.raise_for_status()
        return response.text

    def generate(self, prompt: str, max_new_tokens: int = 1000, temperature: float = 0.0) -> str:
        response = requests.post(
            f"{self.base_url}{self.generate_path}",
            json={"prompt": prompt, "max_new_tokens": max_new_tokens, "temperature": temperature},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("content") or data.get("text") or data.get("response") or json.dumps(data, ensure_ascii=False)


def build_prompt(template: str, chunk: dict[str, Any]) -> str:
    return f"""{template}

现在请抽取下面第五章教材片段。
source_chunk: {chunk["id"]}
source_page: {chunk["page_start"]}
chapter_hint: {chunk.get("chapter_hint", "")}

text:
{chunk["text"]}

请只返回合法 JSON。/no_think
"""


def load_done(path: Path) -> set[str]:
    done = set()
    for row in read_jsonl(path):
        if not row.get("error"):
            done.add(row.get("source_chunk", ""))
            continue
        if row.get("raw_response"):
            try:
                parsed = extract_json(row["raw_response"])
                if parsed.get("entities") or parsed.get("triples"):
                    done.add(row.get("source_chunk", ""))
            except Exception:
                pass
    return done


def normalize_name(value: Any) -> str:
    text = re.sub(r"\s+", "", str(value or "")).strip(".,;:，。；：、（）()[]【】")
    return text[:80]


def normalize_relation(value: Any) -> str:
    rel = str(value or "").strip()
    zh_to_en = {v: k for k, v in RELATION_ZH.items()}
    return zh_to_en.get(rel, rel)


def clean_conf(value: Any, default: float = 0.75) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    if number > 1:
        number /= 100
    return max(0.0, min(1.0, number))


def is_bad_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 40:
        return True
    if re.fullmatch(r"[\d.\-_/]+", name):
        return True
    return False


def entity_id(name: str, typ: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", f"{typ}_{name}")
    return safe.strip("_")[:120]


def add_entity(entities: dict, name: str, typ: str, page: Any, chunk: str, definition: str, confidence: float) -> None:
    name = normalize_name(name)
    typ = typ if typ in ALLOWED_ENTITY_TYPES else "ProcessObject"
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


def add_relation(relations: dict, head: str, head_type: str, relation: str, tail: str, tail_type: str, evidence: str, page: Any, chunk: str, confidence: float) -> None:
    head = normalize_name(head)
    tail = normalize_name(tail)
    relation = normalize_relation(relation)
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
            "relation_zh": RELATION_ZH.get(relation, relation),
            "tail": tail,
            "tail_type": tail_type,
            "evidence": evidence or "",
            "source_pages": set(),
            "source_chunks": set(),
            "confidence_values": [],
        }
    if page:
        relations[key]["source_pages"].add(int(page))
    if chunk:
        relations[key]["source_chunks"].add(chunk)
    if evidence and len(evidence) > len(relations[key]["evidence"]):
        relations[key]["evidence"] = evidence
    relations[key]["confidence_values"].append(confidence)


def command_chunk(args: argparse.Namespace) -> None:
    source = Path(args.source) if args.source else find_source()
    text = compact(read_text_auto(source))
    chunks = split_chunks(text, max_chars=args.max_chars, overlap=args.overlap)
    out = DATA_DIR / "chapter5_chunks.jsonl"
    write_jsonl(out, chunks)
    (DATA_DIR / "chapter5.cleaned.md").write_text(text, encoding="utf-8")
    print(json.dumps({"source": str(source), "chunks": len(chunks), "out": str(out)}, ensure_ascii=False))


def command_extract(args: argparse.Namespace) -> None:
    chunks_path = DATA_DIR / "chapter5_chunks.jsonl"
    chunks = read_jsonl(chunks_path)
    if args.limit:
        chunks = chunks[: args.limit]
    out = OUTPUT_DIR / "raw_extractions.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(out)
    template = PROMPT_PATH.read_text(encoding="utf-8")
    client = PanguClient()
    print(f"Pangu service: {client.base_url}")
    print(f"Health: {client.health()[:200]}")
    with out.open("a", encoding="utf-8") as fh:
        for index, chunk in enumerate(chunks, start=1):
            if chunk["id"] in done:
                print(f"skip {chunk['id']} ({index}/{len(chunks)})")
                continue
            raw = ""
            last_error = None
            for attempt in range(1, args.retries + 1):
                try:
                    raw = client.generate(build_prompt(template, chunk), args.max_new_tokens, 0.0)
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
                    time.sleep(2 * attempt)
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


def command_build_graph(args: argparse.Namespace) -> None:
    raw_rows = read_jsonl(OUTPUT_DIR / "raw_extractions.jsonl")
    entities: dict[tuple[str, str], dict[str, Any]] = {}
    relations: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    document = "第五章 船体分段的装配"
    add_entity(entities, document, "Chapter", 1, "", "第五章知识单元", 1.0)
    for row in raw_rows:
        if (not row.get("entities") and not row.get("triples")) and row.get("raw_response"):
            try:
                parsed = extract_json(row["raw_response"])
                row["entities"] = parsed.get("entities", [])
                row["triples"] = parsed.get("triples", [])
            except Exception:
                pass
        page = row.get("source_page")
        chunk = row.get("source_chunk", "")
        chapter = row.get("chapter_hint") or document
        add_entity(entities, chapter, "Chapter", page, chunk, "", 0.95)
        add_relation(relations, document, "Chapter", "contains", chapter, "Chapter", "第五章包含该知识单元", page, chunk, 0.95)
        for item in row.get("entities", []) or []:
            conf = clean_conf(item.get("confidence"))
            if conf < args.min_confidence:
                continue
            add_entity(
                entities,
                item.get("name"),
                item.get("type"),
                item.get("source_page") or page,
                item.get("source_chunk") or chunk,
                item.get("definition", ""),
                conf,
            )
            add_relation(relations, chapter, "Chapter", "contains", item.get("name"), item.get("type"), "实体出现在该章节文本块中", page, chunk, min(conf, 0.8))
        for tri in row.get("triples", []) or []:
            conf = clean_conf(tri.get("confidence"))
            if conf < args.min_confidence:
                continue
            head_type = tri.get("head_type") or tri.get("subject_type") or "ProcessObject"
            tail_type = tri.get("tail_type") or tri.get("object_type") or "ProcessObject"
            head = tri.get("head") or tri.get("subject")
            tail = tri.get("tail") or tri.get("object")
            add_entity(entities, head, head_type, tri.get("source_page") or page, tri.get("source_chunk") or chunk, "", conf)
            add_entity(entities, tail, tail_type, tri.get("source_page") or page, tri.get("source_chunk") or chunk, "", conf)
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

    entity_rows = []
    for item in entities.values():
        confs = item.pop("confidence_values")
        item["aliases"] = sorted(item["aliases"])
        item["source_pages"] = sorted(item["source_pages"])
        item["source_chunks"] = sorted(item["source_chunks"])
        item["confidence"] = round(sum(confs) / len(confs), 4) if confs else 0.75
        entity_rows.append(item)
    id_lookup = {(row["name"], row["type"]): row["id"] for row in entity_rows}
    relation_rows = []
    for item in relations.values():
        confs = item.pop("confidence_values")
        item["source_pages"] = sorted(item["source_pages"])
        item["source_chunks"] = sorted(item["source_chunks"])
        item["confidence"] = round(sum(confs) / len(confs), 4) if confs else 0.75
        item["head_id"] = id_lookup.get((item["head"], item["head_type"]), entity_id(item["head"], item["head_type"]))
        item["tail_id"] = id_lookup.get((item["tail"], item["tail_type"]), entity_id(item["tail"], item["tail_type"]))
        relation_rows.append(item)
    entity_rows.sort(key=lambda row: (row["type"], row["name"]))
    relation_rows.sort(key=lambda row: (row["relation"], row["head"], row["tail"]))
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(GRAPH_DIR / "entities.jsonl", entity_rows)
    write_jsonl(GRAPH_DIR / "relations.jsonl", relation_rows)
    degree = Counter()
    for rel in relation_rows:
        degree[rel["head_id"]] += 1
        degree[rel["tail_id"]] += 1
    summary = {
        "raw_rows": len(raw_rows),
        "entities": len(entity_rows),
        "relations": len(relation_rows),
        "isolated_entities": sum(1 for row in entity_rows if degree[row["id"]] == 0),
        "entity_type_counts": Counter(row["type"] for row in entity_rows),
        "relation_type_counts": Counter(row["relation"] for row in relation_rows),
        "top_connected_entities": [{"id": key, "degree": value} for key, value in degree.most_common(15)],
    }
    (GRAPH_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Chapter 5 Pangu KG/RAG pipeline.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("chunk")
    p.add_argument("--source", default="")
    p.add_argument("--max-chars", type=int, default=900)
    p.add_argument("--overlap", type=int, default=120)
    p.set_defaults(func=command_chunk)
    p = sub.add_parser("extract")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--sleep", type=float, default=0.2)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--max-new-tokens", type=int, default=1000)
    p.set_defaults(func=command_extract)
    p = sub.add_parser("build-graph")
    p.add_argument("--min-confidence", type=float, default=0.55)
    p.set_defaults(func=command_build_graph)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
