from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CURATED_PATH = ROOT / "data" / "evaluation" / "rag_eval_dataset.jsonl"
CHUNKS_PATH = ROOT / "data" / "processed" / "ship_textbook_chunks.jsonl"

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


def build_question(terms: list[str], chapter_hint: str) -> str:
    topic = terms[0]
    if chapter_hint:
        return f"教材{chapter_hint}中关于“{topic}”的内容主要说明了什么？"
    return f"教材中关于“{topic}”的内容主要说明了什么？"


def build_auto_cases(chunks: list[dict[str, Any]], existing_ids: set[str], needed: int) -> list[dict[str, Any]]:
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
                "question": build_question(terms, str(chunk.get("chapter_hint") or "")),
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=200, help="Total number of evaluation cases to write.")
    parser.add_argument("--output", default=str(CURATED_PATH))
    args = parser.parse_args()

    if args.target < 50:
        raise ValueError("--target should be at least 50 for the expanded evaluation set.")

    curated = read_jsonl(CURATED_PATH)
    chunks = read_jsonl(CHUNKS_PATH)
    existing_ids = {row["id"] for row in curated}
    auto_cases = build_auto_cases(chunks, existing_ids, args.target - len(curated))
    rows = curated + auto_cases
    write_jsonl(Path(args.output), rows[: args.target])
    print(json.dumps({"output": args.output, "cases": len(rows[: args.target]), "curated": len(curated), "auto": len(rows[: args.target]) - len(curated)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
