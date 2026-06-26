from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import json5


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
CHUNKS_PATH = BASE_DIR / "data" / "chapter5_chunks.jsonl"
EVAL_DIR = BASE_DIR / "eval"

RELATION_MAP = {
    "contains": "包括", "has_item": "包括", "包括": "包括", "包含": "包括", "装配程序包括": "包括",
    "belongs_to": "属于", "属于": "属于",
    "采用": "可采用", "可采用": "可采用", "可以采用": "可采用",
    "适合": "适用于", "适合于": "适用于", "适用于": "适用于", "适合装配方式": "适用于",
    "used_for": "用于", "uses_tool": "用于", "operates_on": "用于", "用来": "用于", "用于": "用于", "作用于": "用于",
    "provides_basis_for": "依据", "依据": "依据", "指导": "指导",
    "composed_of": "组成", "由……组成": "组成", "组成": "组成",
    "assembled_with": "连接", "连接/装配": "连接", "连接到": "连接", "连接": "连接", "相连": "连接",
    "located_at": "装配于", "装配位置": "装配于", "装配于": "装配于", "装配在": "装配于", "装配到": "装配于",
    "定位": "定位", "对准": "对准",
    "measures": "控制", "controls": "控制", "checks": "控制", "控制": "控制",
    "causes": "导致", "导致": "导致", "引起": "导致",
    "repairs": "校正", "校正": "校正",
    "代表": "代表", "反映": "反映", "表达": "表达", "具有": "具有",
    "设置依据": "设置依据", "标准范围": "标准范围", "允许界限": "允许界限",
    "工作量占比": "约占", "约占": "约占",
    "同时提供": "同时提供", "装配基面": "装配基面", "装配顺序": "装配顺序",
    "用于控制": "用于控制", "应达到": "应达到", "宽度要求": "宽度要求",
}

ENTITY_TYPE_MAP = {
    "Chapter": "其他", "ProcessObject": "分段类型", "Component": "船体构件",
    "Process": "工艺工序", "Operation": "工艺工序", "ToolEquipment": "工装设备",
    "Measurement": "数据指标", "Parameter": "数据指标", "Material": "其他",
    "QualityRequirement": "控制措施", "Defect": "质量问题", "StandardSafety": "控制措施",
}

ALIAS_GROUPS = [
    ["分段装配", "装配方式", "分段装配方式", "分段的装配方式"],
    ["胎架上进行板的拼接和分段的装配", "胎架"],
    ["专用胎架上装配", "专用胎架"],
    ["平台或胎架上装配", "平台或胎架"],
    ["35%", "船体装焊工作量的35%左右"],
    ["精度标准", "分段制造精度标准"],
    ["含有铸钢艉柱的艉部下段", "艉部下段"],
    ["双斜切胎架", "专用双斜切胎架"],
    ["反装", "倒装"],
]
ALIASES = {}
for group in ALIAS_GROUPS:
    normed = [re.sub(r"\s+", "", item) for item in group]
    for item in normed:
        ALIASES[item] = set(normed)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip()


def norm_rel(value: Any) -> str:
    text = norm(value)
    if text.endswith("标准范围"):
        return "标准范围"
    if text.endswith("允许界限"):
        return "允许界限"
    return RELATION_MAP.get(text, text)


def compatible_name(left: str, right: str) -> bool:
    left = norm(left)
    right = norm(right)
    if not left or not right:
        return False
    if left == right:
        return True
    if right in ALIASES.get(left, set()) or left in ALIASES.get(right, set()):
        return True
    if left in right or right in left:
        shorter = min(len(left), len(right))
        return shorter >= 2
    nums_left = set(re.findall(r"\d+(?:\.\d+)?%?", left))
    nums_right = set(re.findall(r"\d+(?:\.\d+)?%?", right))
    return bool(nums_left and nums_left & nums_right)


def semantic_name(left: str, right: str) -> bool:
    if compatible_name(left, right):
        return True
    left_set = set(norm(left))
    right_set = set(norm(right))
    if not left_set or not right_set:
        return False
    return len(left_set & right_set) / max(1, min(len(left_set), len(right_set))) >= 0.65


def parse_json_legal(text: str) -> bool:
    text = (text or "").strip()
    if not text:
        return False
    try:
        json.loads(text)
        return True
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return False
    try:
        json5.loads(text[start : end + 1])
        return True
    except Exception:
        return False


def load_gold(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_chunks() -> dict[str, str]:
    return {row["id"]: row.get("text", "") for row in read_jsonl(CHUNKS_PATH)}


def load_pred(path: Path) -> tuple[dict[str, dict[str, list[dict[str, Any]]]], dict[str, Any]]:
    rows = read_jsonl(path)
    result = {}
    json_ok = 0
    success = 0
    for row in rows:
        cid = row.get("source_chunk")
        if not cid:
            continue
        json_ok += int(parse_json_legal(row.get("raw_response", "")))
        success += int(bool(not row.get("error") and (row.get("entities") or row.get("triples"))))
        ents = []
        triples = []
        for item in row.get("entities", []) or []:
            name = norm(item.get("name"))
            if name:
                ents.append({"name": name, "type": ENTITY_TYPE_MAP.get(str(item.get("type", "")), str(item.get("type", "")) or "其他"), "evidence": item.get("evidence", "")})
        for item in row.get("triples", []) or []:
            h, r, t = norm(item.get("head")), norm_rel(item.get("relation")), norm(item.get("tail"))
            if h and r and t:
                triples.append({"head": h, "relation": r, "tail": t, "evidence": item.get("evidence", "")})
        result[cid] = {"entities": ents, "triples": triples}
    total = len(rows) or 1
    return result, {
        "raw_rows_found": len(rows),
        "json_legal_rate": round(json_ok / total, 4),
        "extraction_success_rate": round(success / total, 4),
    }


def prf(tp: int, pred_count: int, gold_count: int) -> dict[str, Any]:
    p = tp / pred_count if pred_count else 0.0
    r = tp / gold_count if gold_count else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4)}


def evidence_supported(evidence: str, text: str, head: str = "", tail: str = "") -> bool:
    e = norm(evidence)
    source = norm(text)
    if not e:
        return False
    return e in source or (head and tail and norm(head) in source and norm(tail) in source)


def match_triples(pred: list[dict[str, Any]], gold: list[dict[str, Any]], mode: str) -> tuple[int, list[dict[str, Any]]]:
    used = set()
    manual = []
    tp = 0
    for p in pred:
        hit = None
        for idx, g in enumerate(gold):
            if idx in used:
                continue
            rel_ok = p["relation"] == g["relation"]
            if mode == "strict":
                ok = rel_ok and p["head"] == g["head"] and p["tail"] == g["tail"]
            elif mode == "relaxed":
                ok = rel_ok and compatible_name(p["head"], g["head"]) and compatible_name(p["tail"], g["tail"])
            else:
                ok = rel_ok and semantic_name(p["head"], g["head"]) and semantic_name(p["tail"], g["tail"])
            if ok:
                hit = idx
                break
            if rel_ok and (semantic_name(p["head"], g["head"]) or semantic_name(p["tail"], g["tail"])):
                manual.append({"pred": p, "gold": g, "reason": "partial head/tail overlap"})
        if hit is not None:
            used.add(hit)
            tp += 1
    return tp, manual


def evaluate(gold_path: Path, pred_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    gold_rows = load_gold(gold_path)
    pred_by_chunk, raw_metrics = load_pred(pred_path)
    chunks = load_chunks()
    gold_entity_count = 0
    pred_entity_count = 0
    entity_tp = 0
    type_correct = 0
    gold_triple_count = 0
    pred_triple_count = 0
    strict_tp = 0
    relaxed_tp = 0
    semantic_tp = 0
    supported = 0
    hallucinated = 0
    pred_item_count = 0
    unmatched_entities = {"false_positive": [], "false_negative": []}
    unmatched_triples = {"false_positive": [], "false_negative": []}
    manual_candidates = []

    for row in gold_rows:
        cid = row["chunk_id"]
        pred = pred_by_chunk.get(cid, {"entities": [], "triples": []})
        gold_entities = [{"name": norm(x.get("name")), "type": x.get("type", "其他")} for x in row.get("gold_entities", []) if norm(x.get("name"))]
        pred_entities = pred["entities"]
        gold_triples = [{"head": norm(x.get("head")), "relation": norm_rel(x.get("relation")), "tail": norm(x.get("tail"))} for x in row.get("gold_triples", []) if norm(x.get("head")) and norm(x.get("tail"))]
        pred_triples = pred["triples"]
        gold_entity_count += len(gold_entities)
        pred_entity_count += len(pred_entities)
        gold_triple_count += len(gold_triples)
        pred_triple_count += len(pred_triples)

        matched_gold_entities = set()
        for p in pred_entities:
            hit_idx = next((i for i, g in enumerate(gold_entities) if compatible_name(p["name"], g["name"])), None)
            pred_item_count += 1
            if evidence_supported(p.get("evidence", ""), chunks.get(cid, "")):
                pass
            elif p.get("evidence"):
                hallucinated += 1
            if hit_idx is not None:
                entity_tp += 1
                matched_gold_entities.add(hit_idx)
                if p.get("type") == gold_entities[hit_idx].get("type"):
                    type_correct += 1
            else:
                unmatched_entities["false_positive"].append({"chunk_id": cid, **p})
        for i, g in enumerate(gold_entities):
            if i not in matched_gold_entities:
                unmatched_entities["false_negative"].append({"chunk_id": cid, **g})

        s_tp, _ = match_triples(pred_triples, gold_triples, "strict")
        r_tp, manual_r = match_triples(pred_triples, gold_triples, "relaxed")
        sem_tp, manual_s = match_triples(pred_triples, gold_triples, "semantic")
        strict_tp += s_tp
        relaxed_tp += r_tp
        semantic_tp += sem_tp
        manual_candidates.extend({"chunk_id": cid, **x} for x in (manual_r + manual_s))
        strict_matched = set()
        for p in pred_triples:
            pred_item_count += 1
            if evidence_supported(p.get("evidence", ""), chunks.get(cid, ""), p["head"], p["tail"]):
                supported += 1
            else:
                hallucinated += 1
            if not any(p["head"] == g["head"] and p["relation"] == g["relation"] and p["tail"] == g["tail"] for g in gold_triples):
                unmatched_triples["false_positive"].append({"chunk_id": cid, **p})
        for g in gold_triples:
            if not any(p["head"] == g["head"] and p["relation"] == g["relation"] and p["tail"] == g["tail"] for p in pred_triples):
                unmatched_triples["false_negative"].append({"chunk_id": cid, **g})

    metrics = {
        "gold_entity_count": gold_entity_count,
        "gold_triple_count": gold_triple_count,
        "pred_entity_count": pred_entity_count,
        "pred_triple_count": pred_triple_count,
        "avg_entities_per_chunk": round(pred_entity_count / max(1, len(gold_rows)), 4),
        "avg_triples_per_chunk": round(pred_triple_count / max(1, len(gold_rows)), 4),
        "entity": prf(entity_tp, pred_entity_count, gold_entity_count),
        "entity_type_accuracy": round(type_correct / entity_tp, 4) if entity_tp else 0.0,
        "strict_triple": prf(strict_tp, pred_triple_count, gold_triple_count),
        "relaxed_triple": prf(relaxed_tp, pred_triple_count, gold_triple_count),
        "semantic_like_triple": prf(semantic_tp, pred_triple_count, gold_triple_count),
        "evidence_support_rate": round(supported / pred_triple_count, 4) if pred_triple_count else 0.0,
        "hallucination_rate": round(hallucinated / pred_item_count, 4) if pred_item_count else 0.0,
        **raw_metrics,
    }
    return metrics, unmatched_entities, unmatched_triples, manual_candidates


def report(metrics: dict[str, Any], out_prefix: str) -> str:
    lines = [
        f"# 第五章知识抽取质量评测（{out_prefix}）", "",
        "| 模型 | Entity P | Entity R | Entity F1 | 类型准确率 | Strict Triple F1 | Relaxed Triple F1 | Semantic-like F1 | JSON合法率 | 抽取成功率 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model, m in metrics["models"].items():
        lines.append(
            f"| {model} | {m['entity']['precision']:.2%} | {m['entity']['recall']:.2%} | {m['entity']['f1']:.2%} | {m['entity_type_accuracy']:.2%} | {m['strict_triple']['f1']:.2%} | {m['relaxed_triple']['f1']:.2%} | {m['semantic_like_triple']['f1']:.2%} | {m['json_legal_rate']:.2%} | {m['extraction_success_rate']:.2%} |"
        )
    lines += [
        "",
        "说明：strict 要求 head/relation/tail 完全一致；relaxed 允许关系归一、实体别名、包含关系和核心数值匹配；semantic-like 在 relaxed 基础上加入少量字符重叠近似判断。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--pangu", type=Path, required=True)
    parser.add_argument("--deepseek", type=Path, required=True)
    parser.add_argument("--out-prefix", default="round2")
    args = parser.parse_args()

    results = {"models": {}}
    unmatched_entities = {}
    unmatched_triples = {}
    manual = {}
    for model, path in {"pangu": args.pangu, "deepseek": args.deepseek}.items():
        m, ue, ut, mc = evaluate(args.gold, path)
        results["models"][model] = m
        unmatched_entities[model] = ue
        unmatched_triples[model] = ut
        manual[model] = mc

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / f"{args.out_prefix}_extraction_eval_metrics.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVAL_DIR / f"{args.out_prefix}_unmatched_entities.json").write_text(json.dumps(unmatched_entities, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVAL_DIR / f"{args.out_prefix}_unmatched_triples.json").write_text(json.dumps(unmatched_triples, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVAL_DIR / f"{args.out_prefix}_manual_review_candidates.json").write_text(json.dumps(manual, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVAL_DIR / f"{args.out_prefix}_extraction_eval_report.md").write_text(report(results, args.out_prefix), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
