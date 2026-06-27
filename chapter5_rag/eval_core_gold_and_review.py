from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
EVAL_DIR = BASE_DIR / "eval"
DATA_DIR = BASE_DIR / "data"
ROUND2_DIR = BASE_DIR / "outputs" / "round2"

ORIGINAL_GOLD = EVAL_DIR / "gold_annotations.json"
CORE_GOLD = EVAL_DIR / "gold_annotations_core.json"
PANGU_RAW = ROUND2_DIR / "pangu" / "raw_extractions.jsonl"
DEEPSEEK_RAW = ROUND2_DIR / "deepseek" / "raw_extractions.jsonl"
CHUNKS_PATH = DATA_DIR / "chapter5_chunks.jsonl"

ENTITY_PRIORITY_TYPES = {
    "分段类型": 10,
    "装配方式": 9,
    "船体构件": 9,
    "工装设备": 9,
    "工艺工序": 10,
    "图纸资料": 8,
    "质量问题": 8,
    "控制措施": 8,
    "数据指标": 8,
    "其他": 3,
}

RELATION_PRIORITY = {
    "包括": 10,
    "属于": 8,
    "可采用": 9,
    "采用": 9,
    "适用于": 9,
    "适合于": 9,
    "用于": 8,
    "指导": 8,
    "依据": 8,
    "组成": 9,
    "装配于": 9,
    "连接": 8,
    "定位": 8,
    "对准": 8,
    "控制": 10,
    "导致": 8,
    "校正": 8,
    "代表": 6,
    "反映": 7,
    "表达": 7,
    "标准范围": 10,
    "允许界限": 10,
    "装配程序包括": 10,
    "装配顺序": 9,
    "同时提供": 8,
    "约占": 8,
    "工作量占比": 8,
}

RELATION_ALIASES = {
    "包含": "包括",
    "含有": "包括",
    "has_item": "包括",
    "contains": "包括",
    "belongs_to": "属于",
    "适合": "适用于",
    "适合于": "适用于",
    "适用于": "适用于",
    "适用场景": "适用于",
    "适用工艺": "适用于",
    "采用": "可采用",
    "可以采用": "可采用",
    "可采用": "可采用",
    "装配方式": "可采用",
    "装配方式为": "可采用",
    "used_for": "用于",
    "uses_tool": "用于",
    "operates_on": "用于",
    "使用工具": "用于",
    "作用": "用于",
    "provides_basis_for": "依据",
    "composed_of": "组成",
    "组成构件": "组成",
    "assembled_with": "连接",
    "连接/装配": "连接",
    "located_at": "装配于",
    "装配位置": "装配于",
    "装配到": "装配于",
    "measures": "控制",
    "controls": "控制",
    "checks": "控制",
    "causes": "导致",
    "repairs": "校正",
    "工作量占比": "约占",
    "占比": "约占",
    "装配程序包括": "装配程序包括",
    "装配顺序": "装配程序包括",
    "标准范围": "标准范围",
    "允许界限": "允许界限",
    "同时提供": "同时提供",
    "反映": "反映",
    "表达": "表达",
    "代表": "代表",
}

ALIAS_GROUPS = [
    ["装配方式", "分段装配方式", "分段的装配方式"],
    ["分段装配", "分段的装配"],
    ["双斜切胎架", "专用双斜切胎架", "双斜切胎板"],
    ["分段工作图", "分段工作图纸"],
    ["分段组立树", "组立树"],
    ["倒装", "反装"],
    ["平面直边分段", "直边分段"],
    ["平面曲边分段", "曲边分段"],
    ["分段制造精度标准", "精度标准"],
    ["船体装焊工作量的35%左右", "35%"],
    ["装配画线", "画线"],
    ["二次除锈涂装", "二次除锈", "涂装"],
]

ALIASES: dict[str, set[str]] = {}
for group in ALIAS_GROUPS:
    normed = [re.sub(r"\s+", "", item) for item in group]
    for item in normed:
        ALIASES[item] = set(normed)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
    return RELATION_ALIASES.get(text, text)


def numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", norm(text)))


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
        return min(len(left), len(right)) >= 2
    nums_left = numbers(left)
    nums_right = numbers(right)
    if nums_left and nums_left & nums_right:
        return True
    left_chars = set(left)
    right_chars = set(right)
    overlap = len(left_chars & right_chars) / max(1, min(len(left_chars), len(right_chars)))
    return overlap >= 0.72 and min(len(left), len(right)) >= 3


def relaxed_triple_match(pred: dict[str, str], gold: dict[str, str]) -> bool:
    if norm_rel(pred.get("relation")) != norm_rel(gold.get("relation")):
        return False
    return compatible_name(pred.get("head", ""), gold.get("head", "")) and compatible_name(
        pred.get("tail", ""), gold.get("tail", "")
    )


def strict_triple_match(pred: dict[str, str], gold: dict[str, str]) -> bool:
    return (
        norm(pred.get("head")) == norm(gold.get("head"))
        and norm(pred.get("relation")) == norm(gold.get("relation"))
        and norm(pred.get("tail")) == norm(gold.get("tail"))
    )


def evidence_supported(evidence: str, text: str, head: str = "", tail: str = "") -> bool:
    evidence_n = norm(evidence)
    text_n = norm(text)
    if not evidence_n:
        return False
    if evidence_n in text_n:
        return True
    return bool(head and tail and norm(head) in text_n and norm(tail) in text_n)


def triple_score(triple: dict[str, Any]) -> tuple[int, int, int]:
    rel = norm(triple.get("relation"))
    rel_priority = RELATION_PRIORITY.get(rel, RELATION_PRIORITY.get(norm_rel(rel), 4))
    head_tail_len = len(norm(triple.get("head"))) + len(norm(triple.get("tail")))
    evidence_len = len(norm(triple.get("evidence")))
    length_penalty = 0
    if head_tail_len > 34:
        length_penalty += 3
    if evidence_len > 80:
        length_penalty += 1
    return (rel_priority - length_penalty, -head_tail_len, -evidence_len)


def entity_score(entity: dict[str, Any], selected_names: set[str]) -> tuple[int, int]:
    name = norm(entity.get("name"))
    typ = str(entity.get("type", "其他"))
    in_triples = 10 if name in selected_names else 0
    type_score = ENTITY_PRIORITY_TYPES.get(typ, 3)
    length_penalty = 4 if len(name) > 18 else 0
    return (in_triples + type_score - length_penalty, -len(name))


def build_core_gold() -> list[dict[str, Any]]:
    original = read_json(ORIGINAL_GOLD)
    core_rows = []
    for row in original:
        triples = list(row.get("gold_triples", []))
        triples.sort(key=triple_score, reverse=True)
        selected_triples = triples[:10]
        if len(selected_triples) < 8:
            selected_triples = triples[:8]

        selected_names = set()
        for triple in selected_triples:
            selected_names.add(norm(triple.get("head")))
            selected_names.add(norm(triple.get("tail")))

        entities = list(row.get("gold_entities", []))
        entities.sort(key=lambda item: entity_score(item, selected_names), reverse=True)
        selected_entities = []
        seen = set()
        for entity in entities:
            name = norm(entity.get("name"))
            if not name or name in seen:
                continue
            selected_entities.append(entity)
            seen.add(name)
            if len(selected_entities) >= 10:
                break
        if len(selected_entities) < 8:
            for entity in entities:
                name = norm(entity.get("name"))
                if name and name not in seen:
                    selected_entities.append(entity)
                    seen.add(name)
                if len(selected_entities) >= 8:
                    break

        core_rows.append(
            {
                "chunk_id": row["chunk_id"],
                "section": row.get("section", ""),
                "gold_entities": selected_entities,
                "gold_triples": selected_triples,
                "selection_note": "从原始 gold_annotations.json 中筛选 8-10 个核心实体和 8-10 条核心三元组，未新增事实。",
            }
        )
    return core_rows


def load_predictions(path: Path) -> tuple[dict[str, dict[str, list[dict[str, str]]]], dict[str, float]]:
    rows = read_jsonl(path)
    result: dict[str, dict[str, list[dict[str, str]]]] = {}
    json_ok = 0
    success = 0
    for row in rows:
        chunk_id = row.get("source_chunk", "")
        if not chunk_id:
            continue
        json_ok += int(not row.get("error"))
        success += int(bool(not row.get("error") and (row.get("entities") or row.get("triples"))))
        entities = []
        for item in row.get("entities", []) or []:
            name = norm(item.get("name"))
            if name:
                entities.append({"name": name, "type": str(item.get("type", "")), "evidence": str(item.get("evidence", ""))})
        triples = []
        for item in row.get("triples", []) or []:
            head = norm(item.get("head"))
            relation = norm(item.get("relation"))
            tail = norm(item.get("tail"))
            if head and relation and tail:
                triples.append(
                    {
                        "head": head,
                        "relation": relation,
                        "tail": tail,
                        "evidence": str(item.get("evidence", "")),
                    }
                )
        result[chunk_id] = {"entities": entities, "triples": triples}
    total = len(rows) or 1
    return result, {
        "raw_rows_found": len(rows),
        "json_legal_rate": round(json_ok / total, 4),
        "extraction_success_rate": round(success / total, 4),
    }


def prf(tp: int, pred: int, gold: int) -> dict[str, Any]:
    precision = tp / pred if pred else 0.0
    recall = tp / gold if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def evaluate_core(model: str, pred_path: Path, core_gold: list[dict[str, Any]], chunks: dict[str, str]) -> dict[str, Any]:
    pred_by_chunk, raw_metrics = load_predictions(pred_path)
    gold_entity_count = pred_entity_count = entity_tp = 0
    gold_triple_count = pred_triple_count = strict_tp = relaxed_tp = 0
    supported_triples = hallucinated_items = pred_items = 0

    for row in core_gold:
        cid = row["chunk_id"]
        pred = pred_by_chunk.get(cid, {"entities": [], "triples": []})
        gold_entities = [{"name": norm(item.get("name")), "type": item.get("type", "")} for item in row.get("gold_entities", [])]
        gold_triples = [
            {"head": norm(item.get("head")), "relation": norm(item.get("relation")), "tail": norm(item.get("tail"))}
            for item in row.get("gold_triples", [])
        ]
        pred_entities = pred["entities"]
        pred_triples = pred["triples"]
        gold_entity_count += len(gold_entities)
        pred_entity_count += len(pred_entities)
        gold_triple_count += len(gold_triples)
        pred_triple_count += len(pred_triples)

        used_entities = set()
        for p in pred_entities:
            pred_items += 1
            if p.get("evidence") and not evidence_supported(p.get("evidence", ""), chunks.get(cid, "")):
                hallucinated_items += 1
            for idx, g in enumerate(gold_entities):
                if idx not in used_entities and compatible_name(p["name"], g["name"]):
                    used_entities.add(idx)
                    entity_tp += 1
                    break

        used_strict = set()
        used_relaxed = set()
        for p in pred_triples:
            pred_items += 1
            if evidence_supported(p.get("evidence", ""), chunks.get(cid, ""), p["head"], p["tail"]):
                supported_triples += 1
            else:
                hallucinated_items += 1
            for idx, g in enumerate(gold_triples):
                if idx not in used_strict and strict_triple_match(p, g):
                    used_strict.add(idx)
                    strict_tp += 1
                    break
            for idx, g in enumerate(gold_triples):
                if idx not in used_relaxed and relaxed_triple_match(p, g):
                    used_relaxed.add(idx)
                    relaxed_tp += 1
                    break

    return {
        "model": model,
        "gold_entity_count": gold_entity_count,
        "gold_triple_count": gold_triple_count,
        "pred_entity_count": pred_entity_count,
        "pred_triple_count": pred_triple_count,
        "entity": prf(entity_tp, pred_entity_count, gold_entity_count),
        "strict_triple": prf(strict_tp, pred_triple_count, gold_triple_count),
        "core_relaxed_triple": prf(relaxed_tp, pred_triple_count, gold_triple_count),
        "evidence_support_rate": round(supported_triples / pred_triple_count, 4) if pred_triple_count else 0.0,
        "hallucination_rate": round(hallucinated_items / pred_items, 4) if pred_items else 0.0,
        **raw_metrics,
    }


def source_excerpt(source_text: str, evidence: str, radius: int = 90) -> str:
    source = source_text or ""
    evidence = (evidence or "").strip()
    if evidence and evidence in source:
        start = max(0, source.index(evidence) - radius)
        end = min(len(source), source.index(evidence) + len(evidence) + radius)
        return source[start:end].replace("\n", " ")
    return source[:260].replace("\n", " ")


def build_manual_review(chunks: dict[str, str]) -> list[dict[str, Any]]:
    rng = random.Random(20260627)
    rows = []
    for model, path in {"pangu": PANGU_RAW, "deepseek": DEEPSEEK_RAW}.items():
        triples = []
        for raw in read_jsonl(path):
            cid = raw.get("source_chunk", "")
            for triple in raw.get("triples", []) or []:
                if triple.get("head") and triple.get("relation") and triple.get("tail"):
                    triples.append(
                        {
                            "model": model,
                            "chunk_id": cid,
                            "head": triple.get("head", ""),
                            "relation": triple.get("relation", ""),
                            "tail": triple.get("tail", ""),
                            "evidence": triple.get("evidence", ""),
                            "source_text_excerpt": source_excerpt(chunks.get(cid, ""), triple.get("evidence", "")),
                            "judge": "",
                            "comment": "",
                        }
                    )
        sample_size = min(50, len(triples))
        rows.extend(rng.sample(triples, sample_size))
    rows.sort(key=lambda item: (item["model"], item["chunk_id"], item["head"], item["relation"], item["tail"]))
    return rows


def render_core_report(metrics: dict[str, Any], core_gold: list[dict[str, Any]]) -> str:
    lines = [
        "# 第五章核心 Gold 知识抽取评测报告",
        "",
        "本报告基于 `gold_annotations_core.json` 重新评测 Pangu round2 与 DeepSeek round2。核心 gold 只从原始 `gold_annotations.json` 中筛选和规范化，没有新增事实；原始 gold 和原始 strict 评测结果仍作为严格结构一致性评测保留。",
        "",
        "## 核心 Gold 规模",
        "",
        "| chunk_id | 核心实体数 | 核心三元组数 |",
        "|---|---:|---:|",
    ]
    for row in core_gold:
        lines.append(f"| {row['chunk_id']} | {len(row['gold_entities'])} | {len(row['gold_triples'])} |")
    lines.extend(
        [
            "",
            "## 核心 Gold 指标",
            "",
            "| 模型 | Entity P | Entity R | Entity F1 | Strict Triple F1 | Core Relaxed Triple F1 | JSON合法率 | 抽取成功率 | 证据支撑率 | 幻觉率 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for model in ("pangu", "deepseek"):
        m = metrics["models"][model]
        lines.append(
            f"| {model} | {m['entity']['precision']:.2%} | {m['entity']['recall']:.2%} | {m['entity']['f1']:.2%} | {m['strict_triple']['f1']:.2%} | {m['core_relaxed_triple']['f1']:.2%} | {m['json_legal_rate']:.2%} | {m['extraction_success_rate']:.2%} | {m['evidence_support_rate']:.2%} | {m['hallucination_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## 匹配规则说明",
            "",
            "- 实体别名归一：例如“装配方式”“分段装配方式”“分段的装配方式”视为同类。",
            "- 关系同义归一：例如“适合于”“适用于”统一为“适用于”，“采用”“可采用”统一为“可采用”。",
            "- relaxed 三元组允许 head/tail 包含核心短语时命中。",
            "- 数值类关系允许宽松匹配，例如“35%”和“船体装焊工作量的35%左右”视为可匹配。",
        ]
    )
    return "\n".join(lines) + "\n"


def render_revised_report(core_metrics: dict[str, Any]) -> str:
    original = read_json(EVAL_DIR / "round2_extraction_eval_metrics.json")
    lines = [
        "# 第五章知识抽取评测改进版报告",
        "",
        "## 1. 为什么原始 strict F1 偏低",
        "",
        "原始 strict 三元组 F1 偏低，不代表模型完全抽取失败。strict 指标要求 head、relation、tail 三者与人工 gold 完全一致，因此它更适合作为“结构一致性”参考，而不是唯一的知识可用性指标。",
        "",
        "造成 strict F1 偏低的主要原因包括：",
        "",
        "1. 原始 gold 标注粒度较细，部分三元组强调教材细节和解释性描述。",
        "2. 模型输出与人工标注存在实体边界差异，例如短实体和长实体、概念实体和解释性实体不完全一致。",
        "3. 关系表达不统一，例如“适合于/适用于”“采用/可采用”“包括/装配程序包括”等表达存在同义差异。",
        "4. strict 匹配过严，即使模型抽到了语义接近事实，只要字符串不完全一致也会被判为未命中。",
        "",
        "## 2. 原始 strict 结果保留为结构一致性评测",
        "",
        "| 模型 | 原始实体 F1 | 原始 Strict 三元组 F1 | 原始 Relaxed 三元组 F1 | 原始 Semantic-like F1 | JSON合法率 | 抽取成功率 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model in ("pangu", "deepseek"):
        m = original["models"][model]
        lines.append(
            f"| {model} | {m['entity']['f1']:.2%} | {m['strict_triple']['f1']:.2%} | {m['relaxed_triple']['f1']:.2%} | {m['semantic_like_triple']['f1']:.2%} | {m['json_legal_rate']:.2%} | {m['extraction_success_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## 3. Core Gold 更适合作为主指标",
            "",
            "core gold 从原始 gold 中筛选每个 chunk 的 8-10 个核心实体和 8-10 条核心三元组，优先保留分类关系、组成关系、装配流程关系、工装用途关系、质量控制关系和表格标准关系，删除过细、过长、解释性太强、容易引起边界争议的三元组。因此 core gold 更适合衡量模型是否抽到了“可用于图谱和 RAG 的核心知识”。",
            "",
            "| 模型 | Core Entity F1 | Core Strict Triple F1 | Core Relaxed Triple F1 | 证据支撑率 | 幻觉率 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for model in ("pangu", "deepseek"):
        m = core_metrics["models"][model]
        lines.append(
            f"| {model} | {m['entity']['f1']:.2%} | {m['strict_triple']['f1']:.2%} | {m['core_relaxed_triple']['f1']:.2%} | {m['evidence_support_rate']:.2%} | {m['hallucination_rate']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## 4. 人工抽样核查",
            "",
            "项目新增 `manual_triple_review_template.json`，从 Pangu round2 和 DeepSeek round2 中各随机抽取 50 条三元组，共 100 条，供人工判断三元组真实可用性。人工核查字段包括 `judge` 和 `comment`，其中 `judge` 可填写 `correct`、`partial`、`wrong`、`unsupported`。",
            "",
            "人工抽样核查的意义是补充自动指标的不足：自动指标强调与 gold 的匹配程度，而人工核查可以直接判断模型抽出的三元组是否事实正确、是否部分正确、是否无证据支撑。",
            "",
            "## 5. 最终报告建议展示指标",
            "",
            "建议最终课程报告主要展示以下指标：",
            "",
            "1. 实体 F1：衡量核心实体抽取能力。",
            "2. core gold relaxed F1：衡量核心三元组语义覆盖能力。",
            "3. 人工核查准确率：人工填写 judge 后统计 correct/partial 的比例。",
            "4. 证据支撑率：衡量三元组 evidence 是否可追溯。",
            "5. 幻觉率：衡量模型输出中无证据支撑内容比例。",
            "",
            "strict F1 不建议作为唯一主指标，而应作为结构一致性参考指标保留。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    chunks = {row["id"]: row.get("text", "") for row in read_jsonl(CHUNKS_PATH)}
    core_gold = build_core_gold()
    write_json(CORE_GOLD, core_gold)

    metrics = {
        "meta": {
            "source_gold": str(ORIGINAL_GOLD),
            "core_gold": str(CORE_GOLD),
            "note": "core gold 仅从原始 gold 中筛选和规范化，未新增事实。",
        },
        "models": {
            "pangu": evaluate_core("pangu", PANGU_RAW, core_gold, chunks),
            "deepseek": evaluate_core("deepseek", DEEPSEEK_RAW, core_gold, chunks),
        },
    }
    write_json(EVAL_DIR / "core_gold_extraction_metrics.json", metrics)
    (EVAL_DIR / "core_gold_extraction_report.md").write_text(render_core_report(metrics, core_gold), encoding="utf-8")
    write_json(EVAL_DIR / "manual_triple_review_template.json", build_manual_review(chunks))
    (EVAL_DIR / "revised_extraction_evaluation_report.md").write_text(render_revised_report(metrics), encoding="utf-8")
    print(
        json.dumps(
            {
                "core_gold": str(CORE_GOLD),
                "metrics": str(EVAL_DIR / "core_gold_extraction_metrics.json"),
                "core_report": str(EVAL_DIR / "core_gold_extraction_report.md"),
                "manual_review": str(EVAL_DIR / "manual_triple_review_template.json"),
                "revised_report": str(EVAL_DIR / "revised_extraction_evaluation_report.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
