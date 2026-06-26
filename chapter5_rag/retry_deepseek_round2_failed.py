from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

from eval_extraction_quality import evaluate
from extract_round2_gold_chunks import (
    BASE_DIR,
    DATA_PATH,
    DeepSeekClient,
    build_prompt,
    extract_json,
    normalize_payload,
    read_jsonl,
    write_jsonl,
)


FAILED_CHUNK_ID = "chapter5_012"
RETRY_DIR = BASE_DIR / "outputs" / "round2_retry" / "deepseek"
EVAL_DIR = BASE_DIR / "eval"
ORIGINAL_RAW = BASE_DIR / "outputs" / "round2" / "deepseek" / "raw_extractions.jsonl"
PANGU_RAW = BASE_DIR / "outputs" / "round2" / "pangu" / "raw_extractions.jsonl"
GOLD_PATH = EVAL_DIR / "gold_annotations.json"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_chunk(chunk_id: str) -> dict[str, Any]:
    chunks = {row["id"]: row for row in read_jsonl(DATA_PATH)}
    if chunk_id not in chunks:
        raise KeyError(f"Chunk not found: {chunk_id}")
    return chunks[chunk_id]


def find_original_failure() -> dict[str, Any] | None:
    for row in read_jsonl(ORIGINAL_RAW):
        if row.get("source_chunk") == FAILED_CHUNK_ID:
            return row
    return None


def evidence_supported(evidence: str, text: str, head: str = "", tail: str = "") -> bool:
    evidence = (evidence or "").strip()
    text = text or ""
    if not evidence:
        return False
    if evidence in text:
        return True
    return bool(head and tail and head in text and tail in text)


def retry_chunk() -> dict[str, Any]:
    chunk = load_chunk(FAILED_CHUNK_ID)
    client = DeepSeekClient()
    prompt = build_prompt(chunk)
    raw = ""
    error = None
    parsed = None
    for attempt in range(2):
        try:
            raw = client.generate(prompt)
            parsed = extract_json(raw)
            break
        except Exception as exc:
            error = repr(exc)
            if attempt == 0:
                time.sleep(1.0)
    if parsed is None:
        return {
            "source_chunk": chunk["id"],
            "section": chunk.get("chapter_hint", ""),
            "text": chunk.get("text", ""),
            "raw_response": raw,
            "error": error,
            "entities": [],
            "triples": [],
        }
    normalized = normalize_payload(parsed, chunk)
    return {
        "source_chunk": chunk["id"],
        "section": chunk.get("chapter_hint", ""),
        "text": chunk.get("text", ""),
        "raw_response": raw,
        "entities": normalized["entities"],
        "triples": normalized["triples"],
    }


def merge_after_retry(retry_row: dict[str, Any]) -> list[dict[str, Any]]:
    merged = []
    for row in read_jsonl(ORIGINAL_RAW):
        if row.get("source_chunk") == FAILED_CHUNK_ID and not retry_row.get("error"):
            merged.append(retry_row)
        else:
            merged.append(row)
    return merged


def render_retry_report(metrics: dict[str, Any]) -> str:
    return f"""# DeepSeek Round2 失败 Chunk 补充重试分析

本次实验只对 DeepSeek round2 中首次失败的 `{FAILED_CHUNK_ID}` 做一次补充重试，不重跑全量 DeepSeek，也不覆盖 round2 原始结果。

## 重试结果

| 项目 | 结果 |
|---|---|
| 失败 chunk_id | {metrics["failed_chunk_id"]} |
| 首次失败原因 | {metrics["first_failure_reason"]} |
| 重试是否成功 | {"是" if metrics["retry_success"] else "否"} |
| 是否能解析 JSON | {"是" if metrics["json_parseable"] else "否"} |
| 重试后新增实体数 | {metrics["retry_entity_count"]} |
| 重试后新增三元组数 | {metrics["retry_triple_count"]} |
| evidence 可追溯率 | {metrics["evidence_traceable_rate"]:.2%} |
| 首次 DeepSeek 抽取成功率 | {metrics["original_success_rate"]:.2%} |
| 合并重试后的抽取成功率 | {metrics["after_retry_success_rate"]:.2%} |

## 指标解释

- 首次运行指标用于衡量模型稳定性，反映一次性批处理时 DeepSeek 输出 JSON 的可靠程度。
- after_retry 指标用于衡量加入失败重试机制后的系统可用性，反映工程系统在失败补偿后的可恢复能力。
- 不能用 after_retry 结果替代首次运行结果；两者应同时报告：前者看系统可用性，后者看模型首轮稳定性。

## 文件保留说明

原始 round2 文件未被修改：

- `outputs/round2/deepseek/raw_extractions.jsonl`
- `eval/round2_extraction_eval_metrics.json`
- `eval/extraction_round_comparison.md`

本次补充输出保存在：

- `outputs/round2_retry/deepseek/raw_extractions_retry.jsonl`
- `outputs/round2_retry/deepseek/kg_entities_retry.jsonl`
- `outputs/round2_retry/deepseek/kg_triples_retry.jsonl`
- `eval/deepseek_retry_metrics.json`
- `eval/deepseek_retry_analysis.md`
- `eval/round2_after_retry_extraction_eval_metrics.json`
- `eval/round2_after_retry_comparison.md`
"""


def render_after_retry_comparison(after_retry_metrics: dict[str, Any], retry_metrics: dict[str, Any]) -> str:
    original = json.loads((EVAL_DIR / "round2_extraction_eval_metrics.json").read_text(encoding="utf-8"))
    lines = [
        "# Round2 DeepSeek 补充重试前后对比",
        "",
        "本文件是 after_retry 版本，只用于说明加入失败重试机制后的系统可用性，不替代首次 round2 指标。",
        "",
        "| 模型 | 版本 | Entity F1 | Strict Triple F1 | Relaxed Triple F1 | Semantic-like F1 | JSON合法率 | 抽取成功率 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model in ("pangu", "deepseek"):
        m = original["models"][model]
        lines.append(
            f"| {model} | original_round2 | {m['entity']['f1']:.2%} | {m['strict_triple']['f1']:.2%} | {m['relaxed_triple']['f1']:.2%} | {m['semantic_like_triple']['f1']:.2%} | {m['json_legal_rate']:.2%} | {m['extraction_success_rate']:.2%} |"
        )
    m = after_retry_metrics["models"]["deepseek"]
    lines.append(
        f"| deepseek | after_retry | {m['entity']['f1']:.2%} | {m['strict_triple']['f1']:.2%} | {m['relaxed_triple']['f1']:.2%} | {m['semantic_like_triple']['f1']:.2%} | {m['json_legal_rate']:.2%} | {m['extraction_success_rate']:.2%} |"
    )
    lines.extend(
        [
            "",
            f"`{FAILED_CHUNK_ID}` 首次失败原因：{retry_metrics['first_failure_reason']}",
            f"补充重试成功：{'是' if retry_metrics['retry_success'] else '否'}；新增实体 {retry_metrics['retry_entity_count']} 个，新增三元组 {retry_metrics['retry_triple_count']} 条。",
            "",
            "说明：首次运行指标用于衡量模型稳定性；after_retry 指标用于衡量加入失败重试机制后的系统可用性；不能用 after_retry 结果替代首次运行结果。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    RETRY_DIR.mkdir(parents=True, exist_ok=True)
    retry_raw_path = RETRY_DIR / "raw_extractions_retry.jsonl"
    retry_entity_path = RETRY_DIR / "kg_entities_retry.jsonl"
    retry_triple_path = RETRY_DIR / "kg_triples_retry.jsonl"

    original_failure = find_original_failure()
    retry_row = retry_chunk()
    write_jsonl(retry_raw_path, [retry_row])
    write_jsonl(retry_entity_path, retry_row.get("entities", []))
    write_jsonl(retry_triple_path, retry_row.get("triples", []))

    chunk_text = load_chunk(FAILED_CHUNK_ID).get("text", "")
    evidence_items = retry_row.get("entities", []) + retry_row.get("triples", [])
    traceable = 0
    for item in evidence_items:
        if evidence_supported(item.get("evidence", ""), chunk_text, item.get("head", ""), item.get("tail", "")):
            traceable += 1
    retry_success = bool(not retry_row.get("error") and (retry_row.get("entities") or retry_row.get("triples")))
    original_rows = read_jsonl(ORIGINAL_RAW)
    original_success = sum(1 for row in original_rows if not row.get("error") and (row.get("entities") or row.get("triples")))
    after_success = original_success + (1 if retry_success and original_failure and original_failure.get("error") else 0)
    retry_metrics = {
        "failed_chunk_id": FAILED_CHUNK_ID,
        "first_failure_reason": (original_failure or {}).get("error", "not found"),
        "retry_success": retry_success,
        "retry_entity_count": len(retry_row.get("entities", [])),
        "retry_triple_count": len(retry_row.get("triples", [])),
        "json_parseable": bool(not retry_row.get("error")),
        "evidence_traceable_count": traceable,
        "evidence_item_count": len(evidence_items),
        "evidence_traceable_rate": round(traceable / len(evidence_items), 4) if evidence_items else 0.0,
        "original_success_rate": round(original_success / len(original_rows), 4) if original_rows else 0.0,
        "after_retry_success_rate": round(after_success / len(original_rows), 4) if original_rows else 0.0,
        "original_raw_file_preserved": str(ORIGINAL_RAW),
        "retry_raw_file": str(retry_raw_path),
        "retry_entity_file": str(retry_entity_path),
        "retry_triple_file": str(retry_triple_path),
    }
    write_json(EVAL_DIR / "deepseek_retry_metrics.json", retry_metrics)
    (EVAL_DIR / "deepseek_retry_analysis.md").write_text(render_retry_report(retry_metrics), encoding="utf-8")

    merged_rows = merge_after_retry(retry_row)
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tmp:
        tmp_path = Path(tmp.name)
        tmp.write("\n".join(json.dumps(row, ensure_ascii=False) for row in merged_rows) + "\n")
    try:
        deepseek_after, _, _, _ = evaluate(GOLD_PATH, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    pangu_metrics, _, _, _ = evaluate(GOLD_PATH, PANGU_RAW)
    after_retry_metrics = {"models": {"pangu": pangu_metrics, "deepseek": deepseek_after}}
    write_json(EVAL_DIR / "round2_after_retry_extraction_eval_metrics.json", after_retry_metrics)
    (EVAL_DIR / "round2_after_retry_comparison.md").write_text(
        render_after_retry_comparison(after_retry_metrics, retry_metrics),
        encoding="utf-8",
    )
    print(json.dumps(retry_metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
