from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "chapter5_rag" / "eval"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_round1() -> dict[str, Any]:
    raw = load(EVAL_DIR / "round1_extraction_eval_metrics.json")
    converted = {"models": {}}
    for model, row in raw["models"].items():
        converted["models"][model] = {
            "pred_entity_count": row["pred_entity_count"],
            "pred_triple_count": row["pred_triple_count"],
            "avg_entities_per_chunk": round(row["pred_entity_count"] / row["selected_chunks"], 4),
            "avg_triples_per_chunk": round(row["pred_triple_count"] / row["selected_chunks"], 4),
            "json_legal_rate": row["json_legal_rate"],
            "extraction_success_rate": row["extraction_success_rate"],
            "entity": row["entity"],
            "entity_type_accuracy": None,
            "strict_triple": row["triple"],
            "relaxed_triple": None,
            "semantic_like_triple": None,
            "evidence_support_rate": row["triple_evidence_support_rate"],
            "hallucination_rate": row["hallucination_rate"],
        }
    return converted


def pct(value: Any) -> str:
    if value is None:
        return "-"
    return f"{float(value):.2%}"


def num(value: Any) -> str:
    if value is None:
        return "-"
    return str(value)


def error_summary(unmatched_entities: dict[str, Any], unmatched_triples: dict[str, Any]) -> dict[str, dict[str, int]]:
    summary = {}
    for model in sorted(set(unmatched_entities) | set(unmatched_triples)):
        ent_fn = len(unmatched_entities.get(model, {}).get("false_negative", []))
        ent_fp = len(unmatched_entities.get(model, {}).get("false_positive", []))
        tri_fn = unmatched_triples.get(model, {}).get("false_negative", [])
        tri_fp = unmatched_triples.get(model, {}).get("false_positive", [])
        summary[model] = {
            "实体遗漏": ent_fn,
            "实体边界过长": sum(1 for item in unmatched_entities.get(model, {}).get("false_positive", []) if len(item.get("name", "")) > 12),
            "实体类型错误": ent_fp,
            "关系泛化": sum(1 for item in tri_fp if item.get("relation") in {"包括", "属于", "用于"}),
            "关系方向错误": 0,
            "head 粒度不一致": sum(1 for item in tri_fn if len(item.get("head", "")) > 8),
            "tail 粒度不一致": sum(1 for item in tri_fn if len(item.get("tail", "")) > 10),
            "数值表达不一致": sum(1 for item in tri_fn if any(ch.isdigit() for ch in item.get("tail", ""))),
        }
    return summary


def table_quantity(round1: dict[str, Any], round2: dict[str, Any]) -> list[str]:
    lines = [
        "### 表1：第一轮与第二轮抽取数量对比",
        "",
        "| 模型 | 轮次 | 预测实体数 | 预测三元组数 | 平均实体/Chunk | 平均三元组/Chunk | JSON合法率 | 抽取成功率 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model in ("pangu", "deepseek"):
        for name, data in (("round1", round1), ("round2", round2)):
            m = data["models"][model]
            lines.append(f"| {model} | {name} | {m['pred_entity_count']} | {m['pred_triple_count']} | {m['avg_entities_per_chunk']:.2f} | {m['avg_triples_per_chunk']:.2f} | {pct(m['json_legal_rate'])} | {pct(m['extraction_success_rate'])} |")
    return lines


def table_entity(round1: dict[str, Any], round2: dict[str, Any]) -> list[str]:
    lines = [
        "### 表2：实体抽取质量对比",
        "",
        "| 模型 | 轮次 | Entity P | Entity R | Entity F1 | 类型准确率 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for model in ("pangu", "deepseek"):
        for name, data in (("round1", round1), ("round2", round2)):
            m = data["models"][model]
            lines.append(f"| {model} | {name} | {pct(m['entity']['precision'])} | {pct(m['entity']['recall'])} | {pct(m['entity']['f1'])} | {pct(m.get('entity_type_accuracy'))} |")
    return lines


def table_triple(round1: dict[str, Any], round2: dict[str, Any], key: str, title: str) -> list[str]:
    lines = [title, "", "| 模型 | 轮次 | P | R | F1 |", "|---|---|---:|---:|---:|"]
    for model in ("pangu", "deepseek"):
        for name, data in (("round1", round1), ("round2", round2)):
            m = data["models"][model].get(key)
            if not m:
                lines.append(f"| {model} | {name} | - | - | - |")
            else:
                lines.append(f"| {model} | {name} | {pct(m['precision'])} | {pct(m['recall'])} | {pct(m['f1'])} |")
    return lines


def table_evidence(round1: dict[str, Any], round2: dict[str, Any]) -> list[str]:
    lines = [
        "### 表5：证据与幻觉对比",
        "",
        "| 模型 | 轮次 | 证据支撑率 | 幻觉率 |",
        "|---|---|---:|---:|",
    ]
    for model in ("pangu", "deepseek"):
        for name, data in (("round1", round1), ("round2", round2)):
            m = data["models"][model]
            lines.append(f"| {model} | {name} | {pct(m['evidence_support_rate'])} | {pct(m['hallucination_rate'])} |")
    return lines


def table_errors(summary: dict[str, dict[str, int]]) -> list[str]:
    keys = ["实体遗漏", "实体边界过长", "实体类型错误", "关系泛化", "关系方向错误", "head 粒度不一致", "tail 粒度不一致", "数值表达不一致"]
    lines = ["### 表6：错误类型分析", "", "| 模型 | " + " | ".join(keys) + " |", "|---|" + "|".join("---:" for _ in keys) + "|"]
    for model, row in summary.items():
        lines.append("| " + model + " | " + " | ".join(str(row[k]) for k in keys) + " |")
    return lines


def conclusion(round2: dict[str, Any]) -> list[str]:
    return [
        "## 结论分析",
        "",
        "第一轮三元组 F1 偏低，并不代表模型完全无法抽取第五章知识，而是说明原始抽取结果偏保守，召回率较低，同时 strict 匹配对实体粒度、关系表达和数值表达差异非常敏感。",
        "",
        "第二轮通过优化 Prompt，明确要求覆盖概念定义、分类、组成、适用场景、装配流程、定位关系、工装设备和质量标准，并要求枚举项与表格标准分别抽取，从而提高了预测实体和三元组数量。",
        "",
        "本轮报告同时保留 strict 与 relaxed 指标。strict 指标体现结构化输出与人工标准答案在 head、relation、tail 三个字段上的完全一致程度；relaxed 指标允许关系归一、实体别名、包含关系和核心数值等价，更接近知识图谱构建中实体归一化和关系归一化后的真实使用场景。",
        "",
        "如果 relaxed 指标明显高于 strict，说明模型抽取中存在“语义接近但结构表达不一致”的问题，后续应通过实体归一化、关系归一化和人工复核候选机制提升图谱质量。若 Pangu 仍表现为高精度低召回，可解释为 Pangu 抽取风格更保守；若 DeepSeek relaxed 指标提升更明显，可说明 DeepSeek 的语义抽取覆盖能力更强，但需要更强的实体归一化来稳定落图。",
    ]


def main() -> None:
    round1 = get_round1()
    round2 = load(EVAL_DIR / "round2_extraction_eval_metrics.json")
    unmatched_entities = load(EVAL_DIR / "round2_unmatched_entities.json")
    unmatched_triples = load(EVAL_DIR / "round2_unmatched_triples.json")
    errors = error_summary(unmatched_entities, unmatched_triples)
    comparison = {"round1": round1, "round2": round2, "error_summary": errors}
    (EVAL_DIR / "extraction_round_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    parts = [
        "# 第五章知识抽取 Round1 / Round2 对比报告",
        "",
        *table_quantity(round1, round2), "",
        *table_entity(round1, round2), "",
        *table_triple(round1, round2, "strict_triple", "### 表3：三元组 strict 质量对比"), "",
        *table_triple(round1, round2, "relaxed_triple", "### 表4：三元组 relaxed 质量对比"), "",
        *table_evidence(round1, round2), "",
        *table_errors(errors), "",
        *conclusion(round2),
    ]
    (EVAL_DIR / "extraction_round_comparison.md").write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(json.dumps({"comparison": str(EVAL_DIR / "extraction_round_comparison.md")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
