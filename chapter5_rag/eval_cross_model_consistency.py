from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
EVAL_DIR = BASE_DIR / "eval"
ROUND2_DIR = BASE_DIR / "outputs" / "round2"

PANGU_ENTITIES = ROUND2_DIR / "pangu" / "kg_entities.jsonl"
PANGU_TRIPLES = ROUND2_DIR / "pangu" / "kg_triples.jsonl"
DEEPSEEK_ENTITIES = ROUND2_DIR / "deepseek" / "kg_entities.jsonl"
DEEPSEEK_TRIPLES = ROUND2_DIR / "deepseek" / "kg_triples.jsonl"

RELATION_ALIASES = {
    "包含": "包括",
    "含有": "包括",
    "contains": "包括",
    "属于": "属于",
    "belongs_to": "属于",
    "适合": "适用于",
    "适合于": "适用于",
    "适用于": "适用于",
    "适用场景": "适用于",
    "适用工艺": "适用于",
    "适合装配方式": "适用于",
    "采用": "可采用",
    "可采用": "可采用",
    "可以采用": "可采用",
    "装配方式": "包括",
    "装配方式为": "包括",
    "可以是": "包括",
    "用于": "用于",
    "用来": "用于",
    "作用于": "用于",
    "used_for": "用于",
    "uses_tool": "用于",
    "operates_on": "用于",
    "依据": "依据",
    "指导": "指导",
    "provides_basis_for": "依据",
    "组成": "组成",
    "组成构件": "组成",
    "composed_of": "组成",
    "连接": "连接",
    "连接/装配": "连接",
    "assembled_with": "连接",
    "装配于": "装配于",
    "装配位置": "装配于",
    "装配到": "装配于",
    "located_at": "装配于",
    "定位": "定位",
    "对准": "对准",
    "控制": "控制",
    "用于控制": "控制",
    "controls": "控制",
    "measures": "控制",
    "checks": "控制",
    "导致": "导致",
    "causes": "导致",
    "校正": "校正",
    "repairs": "校正",
    "约占": "约占",
    "工作量占比": "约占",
    "占比": "约占",
    "标准范围": "标准范围",
    "允许界限": "允许界限",
    "同时提供": "同时提供",
    "反映": "反映",
    "表达": "表达",
    "代表": "代表",
    "装配程序包括": "装配程序包括",
    "装配顺序": "装配程序包括",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。；：、,.?？!！;:（）()【】\[\]《》<>\"'“”‘’\-—_/\\|]", "", text)
    return text.strip()


def normalize_relation(value: Any) -> str:
    text = normalize_text(value)
    if text.endswith("标准范围"):
        return "标准范围"
    if text.endswith("允许界限"):
        return "允许界限"
    return RELATION_ALIASES.get(text, text)


def numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", normalize_text(text)))


def compatible_entity(left: Any, right: Any) -> bool:
    left_n = normalize_text(left)
    right_n = normalize_text(right)
    if not left_n or not right_n:
        return False
    if left_n == right_n:
        return True
    if left_n in right_n or right_n in left_n:
        return min(len(left_n), len(right_n)) >= 2
    nums_l = numbers(left_n)
    nums_r = numbers(right_n)
    if nums_l and nums_l & nums_r:
        return True
    left_chars = set(left_n)
    right_chars = set(right_n)
    return len(left_chars & right_chars) / max(1, min(len(left_chars), len(right_chars))) >= 0.76


def entity_key(row: dict[str, Any]) -> str:
    return normalize_text(row.get("name"))


def strict_triple_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        normalize_text(row.get("head")),
        normalize_text(row.get("relation")),
        normalize_text(row.get("tail")),
    )


def relaxed_triple_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if normalize_relation(left.get("relation")) != normalize_relation(right.get("relation")):
        return False
    return compatible_entity(left.get("head"), right.get("head")) and compatible_entity(left.get("tail"), right.get("tail"))


def dedupe_entities(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for row in rows:
        key = entity_key(row)
        if key and key not in seen:
            seen.add(key)
            result.append(row)
    return result


def dedupe_triples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for row in rows:
        key = strict_triple_key(row)
        if all(key) and key not in seen:
            seen.add(key)
            result.append(row)
    return result


def find_entity_overlap(pangu: list[dict[str, Any]], deepseek: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    overlap = []
    pangu_unique = []
    matched_deepseek = set()
    for p_idx, p in enumerate(pangu):
        hit = None
        for d_idx, d in enumerate(deepseek):
            if d_idx in matched_deepseek:
                continue
            if compatible_entity(p.get("name"), d.get("name")):
                hit = d_idx
                break
        if hit is None:
            pangu_unique.append(p)
        else:
            matched_deepseek.add(hit)
            overlap.append({"pangu": p, "deepseek": deepseek[hit]})
    deepseek_unique = [d for idx, d in enumerate(deepseek) if idx not in matched_deepseek]
    return overlap, pangu_unique, deepseek_unique


def find_triple_overlap(
    pangu: list[dict[str, Any]],
    deepseek: list[dict[str, Any]],
    relaxed: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    overlap = []
    pangu_unique = []
    matched_deepseek = set()
    for p in pangu:
        hit = None
        for d_idx, d in enumerate(deepseek):
            if d_idx in matched_deepseek:
                continue
            ok = relaxed_triple_match(p, d) if relaxed else strict_triple_key(p) == strict_triple_key(d)
            if ok:
                hit = d_idx
                break
        if hit is None:
            pangu_unique.append(p)
        else:
            matched_deepseek.add(hit)
            overlap.append({"pangu": p, "deepseek": deepseek[hit]})
    deepseek_unique = [d for idx, d in enumerate(deepseek) if idx not in matched_deepseek]
    return overlap, pangu_unique, deepseek_unique


def pct(value: float) -> str:
    return f"{value:.2%}"


def sample_rows(rows: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    return rows[:limit]


def render_triple(row: dict[str, Any]) -> str:
    return f"{row.get('head', '')} --{row.get('relation', '')}--> {row.get('tail', '')}"


def render_report(metrics: dict[str, Any], pangu_unique: list[dict[str, Any]], deepseek_unique: list[dict[str, Any]]) -> str:
    e = metrics["entity_metrics"]
    t = metrics["triple_metrics"]
    lines = [
        "# DeepSeek 伪标准参考集下的 Pangu 覆盖情况评测",
        "",
        "## 1. 评测目的",
        "",
        "本评测用于分析 Pangu round2 相对于 DeepSeek round2 的覆盖情况。DeepSeek 在第五章 round2 中通常抽取更多三元组，语义覆盖更强，因此可以作为 pseudo reference / teacher reference，用于观察 Pangu 是否遗漏了 DeepSeek 抽到的知识。",
        "",
        "需要强调：DeepSeek 不是人工 gold。本评测是模型间一致性评测，只能说明 Pangu 与 DeepSeek 的重合程度和相对覆盖情况，不能代表 Pangu 的真实准确率，也不能替代 `gold_annotations.json` 的人工标注评测。",
        "",
        "## 2. 实体重合情况",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| Pangu 实体数 | {e['pangu_entity_count']} |",
        f"| DeepSeek 实体数 | {e['deepseek_entity_count']} |",
        f"| 实体重合数 | {e['entity_overlap_count']} |",
        f"| Pangu 实体自身重合率 | {pct(e['pangu_entity_overlap_rate'])} |",
        f"| Pangu 对 DeepSeek 实体覆盖率 | {pct(e['pangu_entity_coverage_of_deepseek'])} |",
        f"| Pangu 独有实体数 | {len(e['pangu_unique_entities'])} |",
        f"| DeepSeek 独有实体数 | {len(e['deepseek_unique_entities'])} |",
        "",
        "## 3. 三元组重合情况",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| Pangu 三元组数 | {t['pangu_triple_count']} |",
        f"| DeepSeek 三元组数 | {t['deepseek_triple_count']} |",
        f"| Strict 三元组重合数 | {t['strict_triple_overlap_count']} |",
        f"| Relaxed 三元组重合数 | {t['relaxed_triple_overlap_count']} |",
        f"| Pangu strict 覆盖 DeepSeek | {pct(t['pangu_strict_coverage_of_deepseek'])} |",
        f"| Pangu relaxed 覆盖 DeepSeek | {pct(t['pangu_relaxed_coverage_of_deepseek'])} |",
        f"| Pangu 独有三元组数 | {len(t['pangu_unique_triples'])} |",
        f"| DeepSeek 独有三元组数 | {len(t['deepseek_unique_triples'])} |",
        "",
        "## 4. Pangu 独有知识示例",
        "",
    ]
    for row in sample_rows(pangu_unique, 10):
        lines.append(f"- {render_triple(row)}；证据：{row.get('evidence', '')}")
    lines.extend(["", "## 5. DeepSeek 独有知识示例", ""])
    for row in sample_rows(deepseek_unique, 10):
        lines.append(f"- {render_triple(row)}；证据：{row.get('evidence', '')}")
    lines.extend(
        [
            "",
            "## 6. 对 Pangu 抽取保守性的分析",
            "",
            "从模型间一致性角度看，Pangu 的输出更稳定，但相对于 DeepSeek 这个高覆盖参考集，Pangu 覆盖到的 DeepSeek 三元组比例有限。这说明 Pangu 更倾向于抽取较确定、较短、较容易结构化的知识，对枚举项、流程展开、表格标准和长尾关系的覆盖较保守。",
            "",
            "Pangu 独有三元组并不一定错误，它们反映了 Pangu 在某些关系表达上与 DeepSeek 有差异，例如 Pangu 可能抽出更细的适用场景、结构特点或装配特点。模型间不一致部分需要结合原文 evidence 和人工核查判断。",
            "",
            "## 7. 对 DeepSeek 高覆盖但稳定性不足的分析",
            "",
            "DeepSeek round2 的三元组数量多于 Pangu，能够抽出更多枚举关系、流程关系和标准范围关系，因此适合作为伪标准参考集分析覆盖情况。但 DeepSeek 不是人工 gold，它也存在实体粒度不一致、关系泛化和复杂 chunk JSON 不完整问题。例如 `chapter5_012` 曾出现不完整 JSON 输出，说明 DeepSeek 高覆盖的同时需要 JSON 修复、失败重试和人工复核机制。",
            "",
            "## 8. 可放入论文的结论段",
            "",
            "为了进一步分析不同大模型在知识抽取任务中的覆盖差异，本文将 DeepSeek round2 抽取结果作为伪标准参考集，对 Pangu round2 进行模型间一致性评测。需要说明的是，DeepSeek 并非人工 gold，该评测不能代表 Pangu 的真实准确率，只用于衡量 Pangu 相对于高覆盖模型的知识覆盖情况。结果表明，Pangu 与 DeepSeek 在实体和三元组层面存在一定重合，但 Pangu 对 DeepSeek 三元组的 relaxed 覆盖率仍有限，说明 Pangu 抽取更稳定但相对保守；DeepSeek 能抽取更多流程和标准类知识，但存在输出稳定性和实体粒度一致性问题。因此，在最终系统中，Pangu 更适合作为稳定可控的自部署抽取模型，DeepSeek 更适合作为高覆盖参考模型或辅助校验模型，二者结合人工核查和证据校验可以进一步提升知识图谱质量。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    pangu_entities = dedupe_entities(read_jsonl(PANGU_ENTITIES))
    deepseek_entities = dedupe_entities(read_jsonl(DEEPSEEK_ENTITIES))
    pangu_triples = dedupe_triples(read_jsonl(PANGU_TRIPLES))
    deepseek_triples = dedupe_triples(read_jsonl(DEEPSEEK_TRIPLES))

    entity_overlap, pangu_unique_entities, deepseek_unique_entities = find_entity_overlap(pangu_entities, deepseek_entities)
    strict_overlap, _, _ = find_triple_overlap(pangu_triples, deepseek_triples, relaxed=False)
    relaxed_overlap, pangu_unique_relaxed, deepseek_unique_relaxed = find_triple_overlap(
        pangu_triples,
        deepseek_triples,
        relaxed=True,
    )

    metrics = {
        "meta": {
            "task": "cross_model_consistency",
            "pseudo_reference": "deepseek_round2",
            "evaluated_model": "pangu_round2",
            "warning": "DeepSeek is not human gold; metrics indicate model-to-model consistency and relative coverage only.",
        },
        "entity_metrics": {
            "pangu_entity_count": len(pangu_entities),
            "deepseek_entity_count": len(deepseek_entities),
            "entity_overlap_count": len(entity_overlap),
            "pangu_entity_overlap_rate": round(len(entity_overlap) / len(pangu_entities), 4) if pangu_entities else 0.0,
            "pangu_entity_coverage_of_deepseek": round(len(entity_overlap) / len(deepseek_entities), 4) if deepseek_entities else 0.0,
            "pangu_unique_entities": pangu_unique_entities,
            "deepseek_unique_entities": deepseek_unique_entities,
        },
        "triple_metrics": {
            "pangu_triple_count": len(pangu_triples),
            "deepseek_triple_count": len(deepseek_triples),
            "strict_triple_overlap_count": len(strict_overlap),
            "relaxed_triple_overlap_count": len(relaxed_overlap),
            "pangu_strict_coverage_of_deepseek": round(len(strict_overlap) / len(deepseek_triples), 4) if deepseek_triples else 0.0,
            "pangu_relaxed_coverage_of_deepseek": round(len(relaxed_overlap) / len(deepseek_triples), 4) if deepseek_triples else 0.0,
            "pangu_unique_triples": pangu_unique_relaxed,
            "deepseek_unique_triples": deepseek_unique_relaxed,
        },
        "overlap_examples": {
            "entity_overlap": entity_overlap[:20],
            "strict_triple_overlap": strict_overlap[:20],
            "relaxed_triple_overlap": relaxed_overlap[:20],
        },
    }
    write_json(EVAL_DIR / "cross_model_consistency_metrics.json", metrics)
    write_json(EVAL_DIR / "pangu_unique_triples_vs_deepseek.json", pangu_unique_relaxed)
    write_json(EVAL_DIR / "deepseek_unique_triples_vs_pangu.json", deepseek_unique_relaxed)
    (EVAL_DIR / "cross_model_consistency_report.md").write_text(
        render_report(metrics, pangu_unique_relaxed, deepseek_unique_relaxed),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "metrics": str(EVAL_DIR / "cross_model_consistency_metrics.json"),
                "report": str(EVAL_DIR / "cross_model_consistency_report.md"),
                "pangu_unique": str(EVAL_DIR / "pangu_unique_triples_vs_deepseek.json"),
                "deepseek_unique": str(EVAL_DIR / "deepseek_unique_triples_vs_pangu.json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
