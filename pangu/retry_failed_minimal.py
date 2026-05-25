from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import json5
from tqdm import tqdm

from extract_triples import DEFAULT_CHUNKS, DEFAULT_OUT, PanguClient


ALLOWED_TYPES = "Chapter, ProcessObject, Component, Process, Operation, ToolEquipment, Measurement, Parameter, Material, QualityRequirement, Defect, StandardSafety"
ALLOWED_RELATIONS = "contains, belongs_to, used_for, uses_tool, operates_on, precedes, follows, measures, controls, provides_basis_for, composed_of, assembled_with, located_at, causes, checks, repairs"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_json(text: str) -> dict[str, Any]:
    text = (text or "").replace("[unused16]", "").replace("[unused17]", "").replace("[unused10]", "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except Exception:
        return json5.loads(text)


def build_prompt(chunk: dict[str, Any], max_chars: int) -> str:
    text = chunk["text"][:max_chars]
    return f"""你是船体装配知识图谱抽取器。只返回一行合法 JSON。

实体类型只能是：{ALLOWED_TYPES}
关系只能是：{ALLOWED_RELATIONS}

从文本中抽取最多 2 条最重要三元组。不要解释，不要 Markdown，不要思考过程。
如果没有明确关系，返回 {{"entities":[],"triples":[]}}。

每条 triples 字段必须包含：
head, head_type, relation, tail, tail_type, evidence, source_page, source_chunk, confidence

source_page: {chunk["page_start"]}
source_chunk: {chunk["id"]}
文本：{text}

输出示例：
{{"entities":[],"triples":[{{"head":"激光经纬仪","head_type":"ToolEquipment","relation":"measures","tail":"垂直度","tail_type":"Measurement","evidence":"测结构垂直度","source_page":{chunk["page_start"]},"source_chunk":"{chunk["id"]}","confidence":0.8}}]}}
/no_think"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry failed chunks with a minimal Pangu prompt.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--max-input-chars", type=int, default=220)
    parser.add_argument("--max-new-tokens", type=int, default=260)
    parser.add_argument("--sleep", type=float, default=0.1)
    args = parser.parse_args()

    raw_rows = load_jsonl(args.raw)
    failed_ids = {row["source_chunk"] for row in raw_rows if row.get("error")}
    chunks = {row["id"]: row for row in load_jsonl(args.chunks)}
    client = PanguClient()

    with args.raw.open("a", encoding="utf-8") as f:
        for chunk_id in tqdm(sorted(failed_ids), desc="minimal retry"):
            chunk = chunks.get(chunk_id)
            if not chunk:
                continue
            prompt = build_prompt(chunk, args.max_input_chars)
            raw = ""
            try:
                raw = client.generate(prompt, max_new_tokens=args.max_new_tokens)
                parsed = parse_json(raw)
                row = {
                    "source_chunk": chunk["id"],
                    "source_page": chunk["page_start"],
                    "chapter_hint": chunk.get("chapter_hint", ""),
                    "text": chunk["text"],
                    "raw_response": raw,
                    "entities": parsed.get("entities", []),
                    "triples": parsed.get("triples", []),
                }
            except Exception as exc:
                row = {
                    "source_chunk": chunk["id"],
                    "source_page": chunk["page_start"],
                    "chapter_hint": chunk.get("chapter_hint", ""),
                    "text": chunk["text"],
                    "error": repr(exc),
                    "raw_response": raw,
                    "entities": [],
                    "triples": [],
                }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
