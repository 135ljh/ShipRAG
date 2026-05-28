from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CURATED_PATH = ROOT / "data" / "evaluation" / "rag_eval_dataset.jsonl"
CHUNKS_PATH = ROOT / "data" / "processed" / "ship_textbook_chunks.jsonl"
RELATIONS_PATH = ROOT / "pangu" / "outputs" / "graph" / "relations.jsonl"

STOP_TERMS = {
    "教材",
    "原文",
    "知识",
    "问题",
    "内容",
    "一般",
    "主要",
    "进行",
    "可以",
    "应该",
    "包括",
    "如下",
    "图中",
    "图示",
    "由于",
    "所以",
    "然后",
    "以及",
    "船体",
    "船舶",
    "装配",
}

TERM_PATTERNS = (
    r"[\u4e00-\u9fff]{2,8}(?:分段|构件|装配|定位|焊接|放样|胎架|样板|测量|检验|修理|变形|基准|标杆|编码|接缝|余量|甲板|舱壁|外板|肋骨|龙骨|线图|型线|工艺)",
    r"(?:分段|构件|装配|定位|焊接|放样|胎架|样板|测量|检验|修理|变形|基准|标杆|编码|接缝|余量|甲板|舱壁|外板|肋骨|龙骨|线图|型线|工艺)[\u4e00-\u9fff]{2,8}",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def normalize_term(term: str) -> str:
    return re.sub(r"\s+", "", term).strip("，。；：、（）()[]【】")


def extract_terms(text: str, limit: int = 6) -> list[str]:
    candidates: list[str] = []
    for pattern in TERM_PATTERNS:
        candidates.extend(normalize_term(match.group(0)) for match in re.finditer(pattern, text))
    ranked: dict[str, int] = {}
    for term in candidates:
        if len(term) < 3 or len(term) > 12:
            continue
        if term in STOP_TERMS or any(stop == term for stop in STOP_TERMS):
            continue
        if re.fullmatch(r"[一二三四五六七八九十]+", term):
            continue
        ranked[term] = ranked.get(term, 0) + len(term)
    return [term for term, _ in sorted(ranked.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def build_question(terms: list[str], page: int) -> str:
    topic = terms[0]
    return f"教材第{page}页中关于“{topic}”的内容主要说明了什么？"


def build_chunk_cases(chunks: list[dict[str, Any]], existing_ids: set[str], needed: int) -> list[dict[str, Any]]:
    usable = []
    for chunk in chunks:
        page = int(chunk.get("page_start") or 0)
        text = str(chunk.get("text") or "")
        if page < 8 or len(text) < 160:
            continue
        terms = extract_terms(text)
        if len(terms) < 3:
            continue
        usable.append((page, chunk, terms))

    # Evenly cover the whole textbook instead of taking the first N chunks.
    step = max(len(usable) / needed, 1)
    selected = []
    used_pages: set[int] = set()
    idx = 0.0
    while len(selected) < needed and int(idx) < len(usable):
        page, chunk, terms = usable[int(idx)]
        idx += step
        if page in used_pages and len(usable) - len(selected) > needed:
            continue
        used_pages.add(page)
        selected.append((page, chunk, terms))
    for page, chunk, terms in usable:
        if len(selected) >= needed:
            break
        selected.append((page, chunk, terms))

    cases = []
    for page, chunk, terms in selected[:needed]:
        case_id = f"auto_chunk_{chunk['id']}"
        if case_id in existing_ids:
            continue
        pages = list(range(int(chunk["page_start"]), int(chunk.get("page_end") or chunk["page_start"]) + 1))
        cases.append(
            {
                "id": case_id,
                "question": build_question(terms, int(chunk.get("page_start") or 0)),
                "category": "graph_rag_auto",
                "expected_mode_prefix": "multi_agent_graph_rag",
                "expected_keywords": terms[:5],
                "expected_pages": pages,
                "top_k": 6,
                "graph_hops": 2,
                "require_graph": True,
                "is_preset": False,
                "source": "auto_textbook_chunk",
            }
        )
    return cases


def clean_name(name: str) -> str:
    return re.sub(r"\s+", "", name or "").strip("，。；：、（）()[]【】")


def is_good_entity_name(name: str) -> bool:
    name = clean_name(name)
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", name))
    if not 2 <= len(name) <= 12 or chinese_count < 2:
        return False
    if re.search(r"[A-Za-z0-9~*_=<>]", name):
        return False
    bad_terms = ("图", "表", "页", "第", "某", "如下", "上述", "进行", "以及", "这种")
    return not any(term in name for term in bad_terms)


def build_relation_cases(relations: list[dict[str, Any]], existing_ids: set[str], needed: int) -> list[dict[str, Any]]:
    candidates = []
    for rel in relations:
        pages = rel.get("source_pages") or []
        if not pages:
            continue
        head = clean_name(rel.get("head", ""))
        tail = clean_name(rel.get("tail", ""))
        relation_zh = clean_name(rel.get("relation_zh", rel.get("relation", "")))
        evidence = str(rel.get("evidence") or "")
        if not is_good_entity_name(head) or not is_good_entity_name(tail):
            continue
        if len(evidence) < 12:
            continue
        page = int(pages[0])
        if page < 8:
            continue
        confidence = float(rel.get("confidence") or 0)
        candidates.append((page, -confidence, head, tail, relation_zh, rel))

    candidates.sort()
    selected = []
    used_pairs: set[tuple[str, str]] = set()
    used_pages: dict[int, int] = {}
    for page, _neg_confidence, head, tail, relation_zh, rel in candidates:
        if len(selected) >= needed:
            break
        pair = (head, tail)
        if pair in used_pairs:
            continue
        if used_pages.get(page, 0) >= 2:
            continue
        case_id = f"auto_relation_{len(selected) + 1:03d}"
        if case_id in existing_ids:
            continue
        used_pairs.add(pair)
        used_pages[page] = used_pages.get(page, 0) + 1
        selected.append(
            {
                "id": case_id,
                "question": f"教材第{page}页中，“{head}”和“{tail}”之间是什么关系？",
                "category": "graph_rag_auto",
                "expected_mode_prefix": "multi_agent_graph_rag",
                "expected_keywords": [head, tail, relation_zh][:5],
                "expected_pages": [page],
                "top_k": 6,
                "graph_hops": 2,
                "require_graph": True,
                "is_preset": False,
                "source": "auto_pangu_relation",
            }
        )
    return selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=200, help="Total number of evaluation cases to write.")
    parser.add_argument("--output", default=str(CURATED_PATH))
    args = parser.parse_args()

    if args.target < 50:
        raise ValueError("--target should be at least 50 for the expanded evaluation set.")

    curated = [
        row
        for row in read_jsonl(CURATED_PATH)
        if not str(row.get("source", "")).startswith("auto_")
    ]
    chunks = read_jsonl(CHUNKS_PATH)
    relations = read_jsonl(RELATIONS_PATH)
    existing_ids = {row["id"] for row in curated}
    needed = args.target - len(curated)
    auto_cases = build_relation_cases(relations, existing_ids, needed)
    if len(auto_cases) < needed:
        auto_cases.extend(build_chunk_cases(chunks, existing_ids | {row["id"] for row in auto_cases}, needed - len(auto_cases)))
    rows = curated + auto_cases
    write_jsonl(Path(args.output), rows[: args.target])
    print(json.dumps({"output": args.output, "cases": len(rows[: args.target]), "curated": len(curated), "auto": len(rows[: args.target]) - len(curated)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
