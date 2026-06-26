from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = ROOT / "chapter5_rag"
CHUNKS_PATH = BASE_DIR / "data" / "chapter5_chunks.jsonl"
EVAL_DIR = BASE_DIR / "eval"

SELECTED_CHUNKS = [
    "chapter5_001",  # 第一节/概述：分段装配概述、装配方式总览
    "chapter5_005",  # 第二节：分段工作图及相关图纸资料
    "chapter5_012",  # 第五节：舷侧分段装配、双斜切胎架
    "chapter5_018",  # 第八节：艏、艉分段装配
    "chapter5_025",  # 第九节：提高分段制造质量的措施
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    chunks = {row["id"]: row for row in read_jsonl(CHUNKS_PATH)}
    missing = [chunk_id for chunk_id in SELECTED_CHUNKS if chunk_id not in chunks]
    if missing:
        raise KeyError(f"Missing selected chunks: {missing}")

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    selected = [chunks[chunk_id] for chunk_id in SELECTED_CHUNKS]

    markdown_parts = [
        "# 第五章知识抽取人工标注样本",
        "",
        "本文件导出 5 个代表性 chunk 原文，用于人工标注实体和三元组 gold 数据。",
        "",
    ]
    template = []
    for chunk in selected:
        markdown_parts.extend(
            [
                f"## {chunk['id']}",
                "",
                f"- chunk_id: `{chunk['id']}`",
                f"- section: {chunk.get('chapter_hint', '')}",
                "",
                "```text",
                chunk.get("text", "").strip(),
                "```",
                "",
            ]
        )
        template.append(
            {
                "chunk_id": chunk["id"],
                "section": chunk.get("chapter_hint", ""),
                "gold_entities": [
                    {"name": "", "type": "", "evidence": ""}
                ],
                "gold_triples": [
                    {"head": "", "relation": "", "tail": "", "evidence": ""}
                ],
            }
        )

    (EVAL_DIR / "gold_sample_chunks.md").write_text("\n".join(markdown_parts), encoding="utf-8")
    (EVAL_DIR / "gold_annotations_template.json").write_text(
        json.dumps(template, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "selected_chunks": SELECTED_CHUNKS,
                "sample_file": str(EVAL_DIR / "gold_sample_chunks.md"),
                "template_file": str(EVAL_DIR / "gold_annotations_template.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
