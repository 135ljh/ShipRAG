from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import json5


ROOT = Path(__file__).resolve().parents[2]
BASE_DIR = ROOT / "chapter5_rag"
EVAL_DIR = BASE_DIR / "eval"
CHUNKS_PATH = BASE_DIR / "data" / "chapter5_chunks.jsonl"
GOLD_PATH = EVAL_DIR / "gold_annotations.json"

MODEL_CONFIGS = {
    "pangu": {
        "raw": BASE_DIR / "outputs" / "raw_extractions.jsonl",
        "graph_entities": BASE_DIR / "outputs" / "graph" / "entities.jsonl",
        "graph_relations": BASE_DIR / "outputs" / "graph" / "relations.jsonl",
    },
    "deepseek": {
        "raw": BASE_DIR / "deepseek_outputs" / "raw_extractions.jsonl",
        "graph_entities": BASE_DIR / "deepseek_outputs" / "graph" / "entities.jsonl",
        "graph_relations": BASE_DIR / "deepseek_outputs" / "graph" / "relations.jsonl",
    },
}

RELATION_MAP = {
    "contains": "包括",
    "has_item": "包括",
    "belongs_to": "属于",
    "used_for": "用于",
    "uses_tool": "用于",
    "operates_on": "用于",
    "precedes": "依据",
    "follows": "依据",
    "measures": "控制",
    "controls": "控制",
    "provides_basis_for": "依据",
    "composed_of": "组成",
    "assembled_with": "连接",
    "located_at": "定位",
    "causes": "导致",
    "checks": "控制",
    "repairs": "校正",
    "包含": "包括",
    "包括": "包括",
    "属于": "属于",
    "采用": "可采用",
    "可采用": "可采用",
    "装配方式为": "可采用",
    "适用": "适用于",
    "适用于": "适用于",
    "用于": "用于",
    "指导": "指导",
    "依据": "依据",
    "组成": "组成",
    "由……组成": "组成",
    "装配于": "装配于",
    "连接": "连接",
    "连接/装配": "连接",
    "定位": "定位",
    "位置关系": "定位",
    "控制": "控制",
    "导致": "导致",
    "校正": "校正",
    "修理对象": "校正",
    "适合装配方式": "适用于",
    "装配位置": "装配于",
    "工作量占比": "约占",
    "约占": "约占",
    "同时提供": "同时提供",
    "设置依据": "设置依据",
    "用于控制": "用于控制",
    "装配基面": "装配基面",
    "装配程序包括": "装配程序包括",
    "装配顺序": "装配顺序",
    "宽度要求": "宽度要求",
    "应达到": "应达到",
    "表达": "表达",
    "反映": "反映",
    "代表": "代表",
    "具有": "具有",
    "形成": "形成",
    "可看出": "可看出",
    "对准": "定位",
    "采用": "可采用",
}

ENTITY_TYPE_MAP = {
    "Chapter": "其他",
    "ProcessObject": "分段类型",
    "Component": "船体构件",
    "Process": "工艺工序",
    "Operation": "工艺工序",
    "ToolEquipment": "工装设备",
    "Measurement": "数据指标",
    "Parameter": "数据指标",
    "Material": "其他",
    "QualityRequirement": "控制措施",
    "Defect": "质量问题",
    "StandardSafety": "控制措施",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_name(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip()


def normalize_relation(value: Any) -> str:
    text = normalize_name(value)
    return RELATION_MAP.get(text, text)


def parse_json_response(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        json.loads(text)
        return True
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return False
    candidate = re.sub(r",\s*([}\]])", r"\1", match.group(0))
    try:
        json5.loads(candidate)
        return True
    except Exception:
        return False


def metric_counts(pred: set[Any], gold: set[Any]) -> dict[str, Any]:
    tp_items = pred & gold
    fp_items = pred - gold
    fn_items = gold - pred
    tp = len(tp_items)
    fp = len(fp_items)
    fn = len(fn_items)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def load_gold() -> list[dict[str, Any]]:
    if not GOLD_PATH.exists():
        raise FileNotFoundError(
            f"Gold annotation file not found: {GOLD_PATH}. "
            "Please copy gold_annotations_template.json to gold_annotations.json and fill it manually."
        )
    rows = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    for row in rows:
        row["gold_entities"] = [item for item in row.get("gold_entities", []) if normalize_name(item.get("name"))]
        row["gold_triples"] = [
            item for item in row.get("gold_triples", [])
            if normalize_name(item.get("head")) and normalize_name(item.get("relation")) and normalize_name(item.get("tail"))
        ]
    return rows


def selected_chunk_ids(gold_rows: list[dict[str, Any]]) -> set[str]:
    return {row["chunk_id"] for row in gold_rows}


def raw_predictions(model: str, chunk_ids: set[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    rows = read_jsonl(MODEL_CONFIGS[model]["raw"])
    selected = [row for row in rows if row.get("source_chunk") in chunk_ids]
    by_chunk: dict[str, dict[str, Any]] = {}
    json_legal = 0
    success = 0
    for row in selected:
        chunk_id = row.get("source_chunk")
        if not chunk_id:
            continue
        by_chunk[chunk_id] = row
        if parse_json_response(row.get("raw_response", "")):
            json_legal += 1
        if not row.get("error") and (row.get("entities") or row.get("triples")):
            success += 1
    total = len(chunk_ids)
    return by_chunk, {
        "selected_chunks": total,
        "raw_rows_found": len(selected),
        "json_legal_rate": round(json_legal / total, 4) if total else 0.0,
        "extraction_success_rate": round(success / total, 4) if total else 0.0,
    }


def model_predictions(model: str, chunk_ids: set[str]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    raw_by_chunk, _ = raw_predictions(model, chunk_ids)
    result: dict[str, dict[str, list[dict[str, Any]]]] = {
        chunk_id: {"entities": [], "triples": []} for chunk_id in chunk_ids
    }
    for chunk_id, row in raw_by_chunk.items():
        for item in row.get("entities", []) or []:
            name = normalize_name(item.get("name"))
            if not name:
                continue
            result[chunk_id]["entities"].append(
                {
                    "name": name,
                    "type": ENTITY_TYPE_MAP.get(str(item.get("type", "")), str(item.get("type", "")) or "其他"),
                    "evidence": str(item.get("evidence") or item.get("definition") or ""),
                }
            )
        for item in row.get("triples", []) or []:
            head = normalize_name(item.get("head") or item.get("subject"))
            relation = normalize_relation(item.get("relation") or item.get("predicate"))
            tail = normalize_name(item.get("tail") or item.get("object"))
            if not (head and relation and tail):
                continue
            result[chunk_id]["triples"].append(
                {
                    "head": head,
                    "relation": relation,
                    "tail": tail,
                    "evidence": str(item.get("evidence") or ""),
                }
            )
    return result


def load_chunks() -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in read_jsonl(CHUNKS_PATH)}


def evidence_supported(item: dict[str, Any], chunk_text: str) -> bool:
    evidence = normalize_name(item.get("evidence"))
    if not evidence:
        return False
    text = normalize_name(chunk_text)
    return evidence in text or normalize_name(item.get("head", "")) in text and normalize_name(item.get("tail", "")) in text


def evaluate_model(model: str, gold_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    chunk_ids = selected_chunk_ids(gold_rows)
    chunks = load_chunks()
    raw_by_chunk, raw_metrics = raw_predictions(model, chunk_ids)
    pred_by_chunk = model_predictions(model, chunk_ids)

    gold_entities = set()
    gold_triples = set()
    pred_entities = set()
    pred_triples = set()
    unmatched_entities: dict[str, Any] = {"false_positive": [], "false_negative": []}
    unmatched_triples: dict[str, Any] = {"false_positive": [], "false_negative": []}

    supported_triples = 0
    hallucinated_items = 0
    predicted_item_count = 0

    for row in gold_rows:
        chunk_id = row["chunk_id"]
        for item in row.get("gold_entities", []):
            gold_entities.add((chunk_id, normalize_name(item.get("name"))))
        for item in row.get("gold_triples", []):
            gold_triples.add(
                (
                    chunk_id,
                    normalize_name(item.get("head")),
                    normalize_relation(item.get("relation")),
                    normalize_name(item.get("tail")),
                )
            )

    for chunk_id, rows in pred_by_chunk.items():
        chunk_text = chunks.get(chunk_id, {}).get("text", "")
        for item in rows["entities"]:
            key = (chunk_id, normalize_name(item.get("name")))
            pred_entities.add(key)
            predicted_item_count += 1
            if item.get("evidence") and not evidence_supported(item, chunk_text):
                hallucinated_items += 1
        for item in rows["triples"]:
            key = (
                chunk_id,
                normalize_name(item.get("head")),
                normalize_relation(item.get("relation")),
                normalize_name(item.get("tail")),
            )
            pred_triples.add(key)
            predicted_item_count += 1
            if evidence_supported(item, chunk_text):
                supported_triples += 1
            else:
                hallucinated_items += 1

    entity_metrics = metric_counts(pred_entities, gold_entities)
    triple_metrics = metric_counts(pred_triples, gold_triples)
    triple_support_rate = supported_triples / len(pred_triples) if pred_triples else 0.0
    hallucination_rate = hallucinated_items / predicted_item_count if predicted_item_count else 0.0

    for key in sorted(pred_entities - gold_entities):
        unmatched_entities["false_positive"].append({"chunk_id": key[0], "name": key[1]})
    for key in sorted(gold_entities - pred_entities):
        unmatched_entities["false_negative"].append({"chunk_id": key[0], "name": key[1]})
    for key in sorted(pred_triples - gold_triples):
        unmatched_triples["false_positive"].append({"chunk_id": key[0], "head": key[1], "relation": key[2], "tail": key[3]})
    for key in sorted(gold_triples - pred_triples):
        unmatched_triples["false_negative"].append({"chunk_id": key[0], "head": key[1], "relation": key[2], "tail": key[3]})

    metrics = {
        "entity": entity_metrics,
        "triple": triple_metrics,
        "triple_evidence_support_rate": round(triple_support_rate, 4),
        "hallucination_rate": round(hallucination_rate, 4),
        **raw_metrics,
        "gold_entity_count": len(gold_entities),
        "gold_triple_count": len(gold_triples),
        "pred_entity_count": len(pred_entities),
        "pred_triple_count": len(pred_triples),
    }
    return metrics, unmatched_entities, unmatched_triples


def render_report(metrics: dict[str, Any]) -> str:
    lines = [
        "# 第五章知识抽取质量评测报告",
        "",
        "本报告基于人工标注的 `eval/gold_annotations.json`，对 Pangu 与 DeepSeek 的第五章知识抽取结果进行自动评测。",
        "",
        "## 指标说明",
        "",
        "- 实体匹配：实体名称完全一致或去空格后一致。",
        "- 三元组匹配：head、relation、tail 三者均归一化后一致。",
        "- 三元组证据支撑率：预测三元组 evidence 能在对应 chunk 原文中找到，或 head/tail 同时出现在原文中。",
        "- 幻觉率：预测实体/三元组存在 evidence 但不能被 chunk 原文支撑的比例。",
        "- JSON 合法率：模型原始输出可解析为 JSON 的 chunk 比例。",
        "- 抽取成功率：对应 chunk 无 error 且抽取出实体或三元组的比例。",
        "",
        "## 核心指标",
        "",
        "| 模型 | 实体 P | 实体 R | 实体 F1 | 三元组 P | 三元组 R | 三元组 F1 | 证据支撑率 | 幻觉率 | JSON 合法率 | 抽取成功率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model, row in metrics["models"].items():
        lines.append(
            "| {model} | {ep:.2%} | {er:.2%} | {ef:.2%} | {tp:.2%} | {tr:.2%} | {tf:.2%} | {support:.2%} | {hall:.2%} | {json_rate:.2%} | {success:.2%} |".format(
                model=model,
                ep=row["entity"]["precision"],
                er=row["entity"]["recall"],
                ef=row["entity"]["f1"],
                tp=row["triple"]["precision"],
                tr=row["triple"]["recall"],
                tf=row["triple"]["f1"],
                support=row["triple_evidence_support_rate"],
                hall=row["hallucination_rate"],
                json_rate=row["json_legal_rate"],
                success=row["extraction_success_rate"],
            )
        )
    lines.extend(
        [
            "",
            "## \u6837\u672c\u8303\u56f4",
            "",
            f"- \u6807\u6ce8 chunk \u6570\uff1a{metrics['gold_chunk_count']}",
            f"- Gold \u5b9e\u4f53\u6570\uff1a{metrics['gold_entity_count']}",
            f"- Gold \u4e09\u5143\u7ec4\u6570\uff1a{metrics['gold_triple_count']}",
            "",
            "## \u4eba\u5de5\u6807\u6ce8\u8bf4\u660e",
            "",
            "- `chapter5_025` \u7684 section \u663e\u793a\u4e3a\u201c\u88685-2 \u5206\u6bb5\u5c40\u90e8\u53d8\u5f62\u7cbe\u5ea6\u6807\u51c6\u201d\uff0c\u4f46\u6837\u672c\u5185\u5bb9\u5b9e\u9645\u4e3b\u8981\u6d89\u53ca\u201c\u88685-1 \u5206\u6bb5\u5236\u9020\u7cbe\u5ea6\u6807\u51c6\u201d\u3002\u672c\u6b21\u8bc4\u6d4b\u4ee5\u4eba\u5de5\u786e\u8ba4\u540e\u7684 `gold_annotations.json` \u4e3a\u51c6\u3002",
            "- \u4e09\u5143\u7ec4\u6307\u6807\u91c7\u7528\u4e25\u683c\u5339\u914d\uff1ahead\u3001relation\u3001tail \u4e09\u8005\u540c\u65f6\u4e00\u81f4\u624d\u8ba1\u4e3a\u6b63\u786e\uff1b\u56e0\u6b64\u6a21\u578b\u62bd\u53d6\u7c92\u5ea6\u4e0d\u540c\u6216\u5934\u5b9e\u4f53\u8868\u8fbe\u4e0d\u540c\uff0c\u5373\u4f7f\u8bed\u4e49\u76f8\u8fd1\u4e5f\u4e0d\u4f1a\u81ea\u52a8\u8ba1\u4e3a\u547d\u4e2d\u3002",
            "",
            "\u672a\u5339\u914d\u660e\u7ec6\u89c1\uff1a",
            "",
            "- `eval/unmatched_entities.json`",
            "- `eval/unmatched_triples.json`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    try:
        gold_rows = load_gold()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)

    all_metrics: dict[str, Any] = {
        "gold_chunk_count": len(gold_rows),
        "gold_entity_count": sum(len(row.get("gold_entities", [])) for row in gold_rows),
        "gold_triple_count": sum(len(row.get("gold_triples", [])) for row in gold_rows),
        "models": {},
    }
    unmatched_entities_all = {}
    unmatched_triples_all = {}

    for model in MODEL_CONFIGS:
        metrics, unmatched_entities, unmatched_triples = evaluate_model(model, gold_rows)
        all_metrics["models"][model] = metrics
        unmatched_entities_all[model] = unmatched_entities
        unmatched_triples_all[model] = unmatched_triples

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "extraction_eval_metrics.json").write_text(
        json.dumps(all_metrics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (EVAL_DIR / "unmatched_entities.json").write_text(
        json.dumps(unmatched_entities_all, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (EVAL_DIR / "unmatched_triples.json").write_text(
        json.dumps(unmatched_triples_all, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (EVAL_DIR / "extraction_eval_report.md").write_text(render_report(all_metrics), encoding="utf-8")
    print(json.dumps(all_metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
