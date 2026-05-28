from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_rag.main import app

OUT_DIR = ROOT / "docs" / "rag_design" / "evaluation"
DEFAULT_DATASET_PATH = ROOT / "data" / "evaluation" / "rag_eval_dataset.jsonl"


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    category: str
    expected_mode_prefix: str
    expected_keywords: tuple[str, ...]
    expected_pages: tuple[int, ...] = ()
    top_k: int = 4
    graph_hops: int = 1
    require_graph: bool = False
    allow_uncertain: bool = False
    is_negative: bool = False
    is_preset: bool = False
    source: str = "inline_fallback"


CASES: tuple[EvalCase, ...] = (
    EvalCase(
        id="book_chapter_count",
        question="这本书有多少章？",
        category="book_profile",
        expected_mode_prefix="multi_agent_book_profile",
        expected_keywords=("7", "七章", "目录"),
        expected_pages=(4, 6, 7),
    ),
    EvalCase(
        id="book_summary",
        question="这本书主要讲什么？",
        category="book_profile",
        expected_mode_prefix="multi_agent_book_profile",
        expected_keywords=("船体装配", "船体放样", "分段装配", "总装配", "船体修理"),
        expected_pages=(4, 5),
    ),
    EvalCase(
        id="domain_block_prepare",
        question="船体分段装配前需要做哪些准备工作？",
        category="domain_qa",
        expected_mode_prefix="multi_agent_domain_qa",
        expected_keywords=("分段工作图", "装配方式", "平台", "胎架", "质量控制"),
        expected_pages=(112, 116, 146),
    ),
    EvalCase(
        id="domain_rib_frame",
        question="船体装配中，肋骨框架的装配流程一般包括哪些步骤？",
        category="domain_qa",
        expected_mode_prefix="multi_agent_domain_qa",
        expected_keywords=("画线", "吊装", "垂直度", "定位焊", "焊接"),
        expected_pages=(136, 139),
    ),
    EvalCase(
        id="domain_slipway_vs_block",
        question="船台装配和船体分段装配有什么区别？各自的施工重点是什么？",
        category="domain_qa",
        expected_mode_prefix="multi_agent_domain_qa",
        expected_keywords=("平台", "胎架", "船台", "定位", "合拢"),
        expected_pages=(112, 150, 157),
    ),
    EvalCase(
        id="domain_total_quality",
        question="在船体总装配过程中，如何保证分段定位的准确性和焊接质量？",
        category="domain_qa",
        expected_mode_prefix="multi_agent_domain_qa",
        expected_keywords=("中心线", "肋骨检验线", "高度", "余量", "定位焊"),
        expected_pages=(157, 163, 165),
    ),
    EvalCase(
        id="domain_measure_tools",
        question="船体装配中常用的测量工具有哪些？它们分别适用于什么场景？",
        category="domain_qa",
        expected_mode_prefix="multi_agent_domain_qa",
        expected_keywords=("激光经纬仪", "水平软管", "线锤", "钢卷尺", "水准仪"),
        expected_pages=(8, 158, 163),
    ),
    EvalCase(
        id="domain_structure_code",
        question="船体结构编码的作用是什么？在船体建造过程中为什么需要进行编码？",
        category="domain_qa",
        expected_mode_prefix="multi_agent_domain_qa",
        expected_keywords=("施工图样", "工艺流程", "五级编码", "分段代码", "零件代码"),
        expected_pages=(19, 20, 109),
    ),
    EvalCase(
        id="domain_welding_deformation_4_1",
        question="船体装配中常见的焊接变形有哪些？",
        category="domain_qa",
        expected_mode_prefix="multi_agent_domain_qa",
        expected_keywords=("横向弯曲", "上翘", "下塌", "角变形", "局部"),
        expected_pages=(146, 147, 148),
        top_k=4,
        graph_hops=1,
    ),
    EvalCase(
        id="domain_welding_deformation_6_2",
        question="船体装配中常见的焊接变形有哪些？",
        category="domain_qa",
        expected_mode_prefix="multi_agent_domain_qa",
        expected_keywords=("横向弯曲", "上翘", "下塌", "角变形", "局部"),
        expected_pages=(146, 147, 148),
        top_k=6,
        graph_hops=2,
    ),
    EvalCase(
        id="graph_laser_use",
        question="激光经纬仪在船体装配中有什么用途？",
        category="graph_rag",
        expected_mode_prefix="multi_agent_graph_rag",
        expected_keywords=("测量", "画线", "基准线", "水平度", "垂直度"),
        expected_pages=(8,),
        require_graph=True,
    ),
    EvalCase(
        id="graph_lofting_tasks",
        question="船体放样的主要任务有哪些？",
        category="graph_rag",
        expected_mode_prefix="multi_agent_graph_rag",
        expected_keywords=("修顺型线", "消除误差", "结构细节", "准确形状", "施工依据"),
        expected_pages=(33,),
        require_graph=True,
        top_k=6,
        graph_hops=2,
    ),
    EvalCase(
        id="graph_baseline_marking",
        question="船台中心线和肋骨检验线通常如何画出？",
        category="graph_rag",
        expected_mode_prefix="multi_agent_graph_rag",
        expected_keywords=("船台中心线", "激光经纬仪", "肋骨检验线", "对中", "90"),
        expected_pages=(157,),
        require_graph=True,
        top_k=6,
        graph_hops=2,
    ),
    EvalCase(
        id="graph_block_positioning",
        question="底部分段在船台上定位时要检查哪些内容？",
        category="domain_qa",
        expected_mode_prefix="multi_agent_domain_qa",
        expected_keywords=("肋骨检验线", "船台中心线", "高度", "左右水平", "固定"),
        expected_pages=(163,),
        require_graph=False,
        top_k=6,
        graph_hops=2,
    ),
    EvalCase(
        id="graph_segment_modes",
        question="船体分段装配方式有哪些？",
        category="graph_rag",
        expected_mode_prefix="multi_agent_graph_rag",
        expected_keywords=("正装", "反装", "侧装", "卧装", "框架式"),
        expected_pages=(112, 113, 114, 115),
        require_graph=True,
        top_k=6,
        graph_hops=1,
    ),
    EvalCase(
        id="negative_mars_population",
        question="火星现在有多少常住人口？",
        category="negative",
        expected_mode_prefix="multi_agent_graph_rag",
        expected_keywords=("无法确定", "知识库", "未"),
        allow_uncertain=True,
        is_negative=True,
    ),
    EvalCase(
        id="negative_reactor_repair",
        question="这本教材是否介绍了核潜艇反应堆维修流程？",
        category="negative",
        expected_mode_prefix="multi_agent_graph_rag",
        expected_keywords=("无法确定", "知识库", "未"),
        allow_uncertain=True,
        is_negative=True,
        top_k=6,
        graph_hops=2,
    ),
)


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def load_cases(path: Path) -> list[EvalCase]:
    if not path.exists():
        return list(CASES)
    cases: list[EvalCase] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        try:
            cases.append(
                EvalCase(
                    id=payload["id"],
                    question=payload["question"],
                    category=payload["category"],
                    expected_mode_prefix=payload.get("expected_mode_prefix", "multi_agent_graph_rag"),
                    expected_keywords=tuple(payload.get("expected_keywords", ())),
                    expected_pages=tuple(payload.get("expected_pages", ())),
                    top_k=int(payload.get("top_k", 4)),
                    graph_hops=int(payload.get("graph_hops", 1)),
                    require_graph=bool(payload.get("require_graph", False)),
                    allow_uncertain=bool(payload.get("allow_uncertain", False)),
                    is_negative=bool(payload.get("is_negative", False)),
                    is_preset=bool(payload.get("is_preset", False)),
                    source=payload.get("source", str(path.relative_to(ROOT))),
                )
            )
        except KeyError as exc:
            raise ValueError(f"{path}:{line_no} missing required field {exc}") from exc
    return cases


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    if len(values) == 1:
        return round(values[0], 4)
    k = (len(values) - 1) * p
    lower = math.floor(k)
    upper = math.ceil(k)
    if lower == upper:
        return round(values[int(k)], 4)
    return round(values[lower] * (upper - k) + values[upper] * (k - lower), 4)


def keyword_recall(answer: str, keywords: tuple[str, ...]) -> float:
    if not keywords:
        return 1.0
    hits = sum(1 for keyword in keywords if keyword in answer)
    return round(hits / len(keywords), 4)


def page_hit(documents: list[dict], expected_pages: tuple[int, ...]) -> bool:
    if not expected_pages:
        return True
    pages = set()
    for doc in documents:
        start = doc.get("page_start")
        end = doc.get("page_end") or start
        if isinstance(start, int) and isinstance(end, int):
            pages.update(range(start, end + 1))
    return any(page in pages for page in expected_pages)


def document_pages(doc: dict) -> set[int]:
    start = doc.get("page_start")
    end = doc.get("page_end") or start
    if isinstance(start, int) and isinstance(end, int):
        return set(range(start, end + 1))
    return set()


def document_relevance(doc: dict, expected_pages: tuple[int, ...]) -> int:
    if not expected_pages:
        return 0
    return 1 if document_pages(doc) & set(expected_pages) else 0


def retrieval_metrics(documents: list[dict], expected_pages: tuple[int, ...]) -> dict[str, float]:
    if not expected_pages:
        return {
            "context_precision": 1.0,
            "context_recall": 1.0,
            "hit_at_k": 1.0,
            "mrr": 1.0,
            "ndcg": 1.0,
        }
    relevances = [document_relevance(doc, expected_pages) for doc in documents]
    retrieved = len(relevances)
    relevant_retrieved = sum(relevances)
    covered_pages = set()
    expected_set = set(expected_pages)
    for doc in documents:
        covered_pages.update(document_pages(doc) & expected_set)
    first_rank = next((idx + 1 for idx, rel in enumerate(relevances) if rel), None)
    dcg = sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevances))
    ideal_rels = [1] * min(relevant_retrieved, retrieved)
    idcg = sum(rel / math.log2(idx + 2) for idx, rel in enumerate(ideal_rels))
    return {
        "context_precision": round(relevant_retrieved / retrieved, 4) if retrieved else 0.0,
        "context_recall": round(len(covered_pages) / len(expected_set), 4),
        "hit_at_k": 1.0 if relevant_retrieved > 0 else 0.0,
        "mrr": round(1 / first_rank, 4) if first_rank else 0.0,
        "ndcg": round(dcg / idcg, 4) if idcg else 0.0,
    }


def contains_uncertain(answer: str) -> bool:
    uncertain_terms = ("无法确定", "不能确定", "证据不足", "未给出", "不足以回答")
    return any(term in answer for term in uncertain_terms)


def has_required_sections(answer: str) -> bool:
    return all(term in answer for term in ("结论", "依据", "引用"))


def has_mojibake(text: str) -> bool:
    markers = ("锛", "绗", "鐨", "瑁", "鍒", "涓", "€", "�")
    return any(marker in text for marker in markers)


def context_utilization(answer: str, documents: list[dict]) -> float:
    if not documents:
        return 1.0
    used = 0
    for doc in documents:
        pages = document_pages(doc)
        if any(f"第{page}页" in answer or f"页码{page}" in answer or f"页码={page}" in answer or str(page) in answer for page in pages):
            used += 1
    return round(used / len(documents), 4)


def generation_metrics(case: EvalCase, answer: str, documents: list[dict], graph: list[dict], kw_recall: float) -> dict[str, float]:
    relevant_docs = sum(document_relevance(doc, case.expected_pages) for doc in documents)
    evidence_available = relevant_docs > 0 or len(graph) > 0 or not case.expected_pages
    citation = "引用" in answer and (len(documents) > 0 or len(graph) > 0)
    uncertain = contains_uncertain(answer)
    if case.is_negative:
        negative_rejection = 1.0 if uncertain else 0.0
        faithfulness = 1.0 if uncertain else 0.0
        answer_relevance = keyword_recall(answer, case.expected_keywords)
        completeness = answer_relevance
        correctness = negative_rejection
    else:
        negative_rejection = 1.0
        faithfulness = mean([1.0 if evidence_available else 0.0, 1.0 if citation else 0.0, 0.0 if uncertain else 1.0])
        answer_relevance = kw_recall
        completeness = kw_recall
        correctness = mean([kw_recall, 1.0 if evidence_available else 0.0, 0.0 if uncertain else 1.0])
    fluency = mean(
        [
            0.0 if has_mojibake(answer) else 1.0,
            1.0 if "**" not in answer else 0.0,
            1.0 if has_required_sections(answer) else 0.0,
            1.0 if 40 <= len(answer) <= 1200 else 0.0,
        ]
    )
    return {
        "faithfulness": faithfulness,
        "answer_relevance": answer_relevance,
        "answer_completeness": completeness,
        "answer_correctness": correctness,
        "fluency": fluency,
        "negative_rejection": negative_rejection,
        "context_utilization": context_utilization(answer, documents),
    }


def evaluate_case(client: TestClient, case: EvalCase, repeat_cached: bool) -> dict[str, Any]:
    started = time.perf_counter()
    response = client.post(
        "/ask",
        json={"question": case.question, "top_k": case.top_k, "graph_hops": case.graph_hops},
    )
    wall_ms = round((time.perf_counter() - started) * 1000, 2)
    data = response.json()
    answer = data.get("answer", "")
    metadata = data.get("metadata", {})
    evidence = data.get("evidence", {})
    documents = evidence.get("documents", [])
    graph = evidence.get("graph", [])
    trace = metadata.get("agent_trace", [])
    mode = metadata.get("retrieval_mode", "")

    cached_elapsed_ms = None
    cached_trace = []
    if repeat_cached:
        started_cached = time.perf_counter()
        cached_response = client.post(
            "/ask",
            json={"question": case.question, "top_k": case.top_k, "graph_hops": case.graph_hops},
        )
        cached_elapsed_ms = round((time.perf_counter() - started_cached) * 1000, 2)
        cached_trace = cached_response.json().get("metadata", {}).get("agent_trace", [])

    kw_recall = keyword_recall(answer, case.expected_keywords)
    retrieval = retrieval_metrics(documents, case.expected_pages)
    generation = generation_metrics(case, answer, documents, graph, kw_recall)
    result = {
        "id": case.id,
        "question": case.question,
        "category": case.category,
        "is_preset": case.is_preset,
        "source": case.source,
        "top_k": case.top_k,
        "graph_hops": case.graph_hops,
        "status_code": response.status_code,
        "retrieval_mode": mode,
        "mode_ok": mode.startswith(case.expected_mode_prefix),
        "keyword_recall": kw_recall,
        "keyword_ok": kw_recall >= 0.6,
        **retrieval,
        **generation,
        "page_hit": page_hit(documents, case.expected_pages),
        "graph_ok": (len(graph) > 0) if case.require_graph else True,
        "sections_ok": has_required_sections(answer),
        "citation_ok": "引用" in answer and (len(documents) > 0 or len(graph) > 0),
        "uncertain": contains_uncertain(answer),
        "uncertain_ok": case.allow_uncertain or not contains_uncertain(answer),
        "mojibake": has_mojibake(answer),
        "no_markdown_bold": "**" not in answer,
        "answer_chars": len(answer),
        "documents": len(documents),
        "graph_facts": len(graph),
        "linked_entities": len(data.get("linked_entities", [])),
        "agent_steps": [step.get("agent") for step in trace],
        "agent_steps_count": len(trace),
        "reported_elapsed_ms": metadata.get("elapsed_ms"),
        "wall_elapsed_ms": wall_ms,
        "cached_wall_elapsed_ms": cached_elapsed_ms,
        "cached_agent_steps": [step.get("agent") for step in cached_trace],
        "answer_preview": answer[:240].replace("\n", " "),
    }
    result["pass"] = all(
        [
            result["status_code"] == 200,
            result["mode_ok"],
            result["keyword_ok"],
            result["page_hit"],
            result["graph_ok"],
            result["sections_ok"],
            result["citation_ok"],
            result["uncertain_ok"],
            not result["mojibake"],
            result["no_markdown_bold"],
            result["agent_steps_count"] > 0,
        ]
    )
    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not results:
        return {"cases": 0, "by_category": {}}
    latencies = [float(item["wall_elapsed_ms"]) for item in results]
    reported_latencies = [float(item["reported_elapsed_ms"] or 0) for item in results]
    cached_latencies = [float(item["cached_wall_elapsed_ms"] or 0) for item in results if item["cached_wall_elapsed_ms"] is not None]
    return {
        "cases": len(results),
        "pass_rate": mean([1.0 if item["pass"] else 0.0 for item in results]),
        "task_completion_rate": mean([1.0 if item["pass"] else 0.0 for item in results]),
        "mode_accuracy": mean([1.0 if item["mode_ok"] else 0.0 for item in results]),
        "context_precision": mean([float(item["context_precision"]) for item in results]),
        "context_recall": mean([float(item["context_recall"]) for item in results]),
        "hit_at_k": mean([float(item["hit_at_k"]) for item in results]),
        "mrr": mean([float(item["mrr"]) for item in results]),
        "ndcg": mean([float(item["ndcg"]) for item in results]),
        "faithfulness": mean([float(item["faithfulness"]) for item in results]),
        "answer_relevance": mean([float(item["answer_relevance"]) for item in results]),
        "answer_completeness": mean([float(item["answer_completeness"]) for item in results]),
        "answer_correctness": mean([float(item["answer_correctness"]) for item in results]),
        "fluency": mean([float(item["fluency"]) for item in results]),
        "context_utilization": mean([float(item["context_utilization"]) for item in results]),
        "negative_rejection_rate": negative_rejection_rate(results),
        "noise_robustness_rate": noise_robustness_rate(results),
        "keyword_recall_avg": mean([float(item["keyword_recall"]) for item in results]),
        "keyword_ok_rate": mean([1.0 if item["keyword_ok"] else 0.0 for item in results]),
        "page_hit_rate": mean([1.0 if item["page_hit"] else 0.0 for item in results]),
        "graph_ok_rate": mean([1.0 if item["graph_ok"] else 0.0 for item in results]),
        "format_sections_rate": mean([1.0 if item["sections_ok"] else 0.0 for item in results]),
        "citation_rate": mean([1.0 if item["citation_ok"] else 0.0 for item in results]),
        "uncertain_rate": mean([1.0 if item["uncertain"] else 0.0 for item in results]),
        "mojibake_rate": mean([1.0 if item["mojibake"] else 0.0 for item in results]),
        "markdown_bold_rate": mean([0.0 if item["no_markdown_bold"] else 1.0 for item in results]),
        "avg_answer_chars": round(statistics.mean([item["answer_chars"] for item in results]), 2),
        "avg_documents": round(statistics.mean([item["documents"] for item in results]), 2),
        "avg_graph_facts": round(statistics.mean([item["graph_facts"] for item in results]), 2),
        "avg_agent_steps": round(statistics.mean([item["agent_steps_count"] for item in results]), 2),
        "latency_wall_ms": {
            "avg": round(statistics.mean(latencies), 2),
            "p50": percentile(latencies, 0.5),
            "p90": percentile(latencies, 0.9),
            "p95": percentile(latencies, 0.95),
            "max": round(max(latencies), 2),
        },
        "latency_reported_ms": {
            "avg": round(statistics.mean(reported_latencies), 2),
            "p50": percentile(reported_latencies, 0.5),
            "p90": percentile(reported_latencies, 0.9),
            "p95": percentile(reported_latencies, 0.95),
            "max": round(max(reported_latencies), 2),
        },
        "cached_latency_wall_ms": {
            "avg": round(statistics.mean(cached_latencies), 2) if cached_latencies else 0.0,
            "p50": percentile(cached_latencies, 0.5),
            "p90": percentile(cached_latencies, 0.9),
            "max": round(max(cached_latencies), 2) if cached_latencies else 0.0,
        },
        "by_category": summarize_by_category(results),
        "by_subset": summarize_by_subset(results),
    }


def negative_rejection_rate(results: list[dict[str, Any]]) -> float:
    items = [item for item in results if item["category"] == "negative"]
    return mean([float(item["negative_rejection"]) for item in items]) if items else 0.0


def noise_robustness_rate(results: list[dict[str, Any]]) -> float:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        grouped.setdefault(item["question"], []).append(item)
    pairs = [items for items in grouped.values() if len(items) > 1]
    if not pairs:
        return 1.0
    robust = []
    for items in pairs:
        robust.append(1.0 if all(item["pass"] for item in items) and len({item["retrieval_mode"] for item in items}) == 1 else 0.0)
    return mean(robust)


def summarize_by_category(results: list[dict[str, Any]]) -> dict[str, Any]:
    categories = sorted({item["category"] for item in results})
    grouped = {}
    for category in categories:
        items = [item for item in results if item["category"] == category]
        grouped[category] = {
            "cases": len(items),
            "pass_rate": mean([1.0 if item["pass"] else 0.0 for item in items]),
            "context_precision": mean([float(item["context_precision"]) for item in items]),
            "context_recall": mean([float(item["context_recall"]) for item in items]),
            "faithfulness": mean([float(item["faithfulness"]) for item in items]),
            "answer_relevance": mean([float(item["answer_relevance"]) for item in items]),
            "keyword_recall_avg": mean([float(item["keyword_recall"]) for item in items]),
            "page_hit_rate": mean([1.0 if item["page_hit"] else 0.0 for item in items]),
            "avg_latency_ms": round(statistics.mean([float(item["wall_elapsed_ms"]) for item in items]), 2),
        }
    return grouped


def summarize_by_subset(results: list[dict[str, Any]]) -> dict[str, Any]:
    subsets = {
        "strict_non_preset": [item for item in results if not item["is_preset"]],
        "preset_or_rule_based": [item for item in results if item["is_preset"]],
    }
    return {
        name: {
            "cases": len(items),
            "pass_rate": mean([1.0 if item["pass"] else 0.0 for item in items]),
            "context_precision": mean([float(item["context_precision"]) for item in items]),
            "context_recall": mean([float(item["context_recall"]) for item in items]),
            "hit_at_k": mean([float(item["hit_at_k"]) for item in items]),
            "faithfulness": mean([float(item["faithfulness"]) for item in items]),
            "answer_relevance": mean([float(item["answer_relevance"]) for item in items]),
            "keyword_recall_avg": mean([float(item["keyword_recall"]) for item in items]),
            "page_hit_rate": mean([1.0 if item["page_hit"] else 0.0 for item in items]),
            "avg_latency_ms": round(statistics.mean([float(item["wall_elapsed_ms"]) for item in items]), 2) if items else 0.0,
        }
        for name, items in subsets.items()
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# ShipRAG RAG 评估报告",
        "",
        "本报告按照 `RAG评估体系.docx` 中的三层指标体系重新计算：检索层、生成层、系统层。",
        "",
        f"- 评估样本数：{summary['cases']}",
        f"- 任务完成率：{summary['task_completion_rate']:.2%}",
        f"- 路由准确率：{summary['mode_accuracy']:.2%}",
        f"- 噪声鲁棒性：{summary['noise_robustness_rate']:.2%}",
        f"- 负样本拒绝率：{summary['negative_rejection_rate']:.2%}",
        f"- 严格非预设样本数：{summary['by_subset']['strict_non_preset']['cases']}",
        f"- 严格非预设通过率：{summary['by_subset']['strict_non_preset']['pass_rate']:.2%}",
        "",
        "## 核心指标",
        "",
        "| 层级 | 指标 | 分数 |",
        "|---|---|---:|",
        f"| 检索层 | Context Precision | {summary['context_precision']:.2%} |",
        f"| 检索层 | Context Recall | {summary['context_recall']:.2%} |",
        f"| 检索层 | Hit@K | {summary['hit_at_k']:.2%} |",
        f"| 检索层 | MRR | {summary['mrr']:.2%} |",
        f"| 检索层 | NDCG | {summary['ndcg']:.2%} |",
        f"| 生成层 | Faithfulness/Groundedness | {summary['faithfulness']:.2%} |",
        f"| 生成层 | Answer Relevance | {summary['answer_relevance']:.2%} |",
        f"| 生成层 | Answer Completeness | {summary['answer_completeness']:.2%} |",
        f"| 生成层 | Answer Correctness | {summary['answer_correctness']:.2%} |",
        f"| 生成层 | Fluency | {summary['fluency']:.2%} |",
        f"| 系统层 | Context Utilization | {summary['context_utilization']:.2%} |",
        f"| 系统层 | Task Completion | {summary['task_completion_rate']:.2%} |",
        f"| 系统层 | Negative Rejection | {summary['negative_rejection_rate']:.2%} |",
        f"| 系统层 | Noise Robustness | {summary['noise_robustness_rate']:.2%} |",
        "",
        "## 质量辅助指标",
        "",
        f"- 关键词覆盖率均值：{summary['keyword_recall_avg']:.2%}",
        f"- 期望页命中率：{summary['page_hit_rate']:.2%}",
        f"- 引用完整率：{summary['citation_rate']:.2%}",
        f"- 答案结构完整率：{summary['format_sections_rate']:.2%}",
        f"- 无法确定率：{summary['uncertain_rate']:.2%}",
        f"- 乱码率：{summary['mojibake_rate']:.2%}",
        f"- Markdown 粗体符号率：{summary['markdown_bold_rate']:.2%}",
        "",
        "## 响应耗时",
        "",
        "| 指标 | 平均 | P50 | P90 | P95 | 最大 |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| 首次 wall time/ms | {summary['latency_wall_ms']['avg']} | {summary['latency_wall_ms']['p50']} | "
            f"{summary['latency_wall_ms']['p90']} | {summary['latency_wall_ms']['p95']} | {summary['latency_wall_ms']['max']} |"
        ),
        (
            f"| 系统 reported/ms | {summary['latency_reported_ms']['avg']} | {summary['latency_reported_ms']['p50']} | "
            f"{summary['latency_reported_ms']['p90']} | {summary['latency_reported_ms']['p95']} | {summary['latency_reported_ms']['max']} |"
        ),
        (
            f"| 缓存 wall time/ms | {summary['cached_latency_wall_ms']['avg']} | {summary['cached_latency_wall_ms']['p50']} | "
            f"{summary['cached_latency_wall_ms']['p90']} | - | {summary['cached_latency_wall_ms']['max']} |"
        ),
        "",
        "## 分类结果",
        "",
        "| 类别 | 样本数 | 通过率 | Context Precision | Context Recall | Faithfulness | Answer Relevance | 平均耗时/ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for category, values in summary["by_category"].items():
        lines.append(
            f"| {category} | {values['cases']} | {values['pass_rate']:.2%} | "
            f"{values['context_precision']:.2%} | {values['context_recall']:.2%} | "
            f"{values['faithfulness']:.2%} | {values['answer_relevance']:.2%} | {values['avg_latency_ms']} |"
        )
    lines.extend(
        [
            "",
            "## 预设样本隔离",
            "",
            "为避免把 `domain_qa.py` 中的规则问答当作真实 RAG 能力，本次评估把样本拆成两组：",
            "",
            "| 子集 | 样本数 | 通过率 | Context Precision | Context Recall | Hit@K | Faithfulness | Answer Relevance | 平均耗时/ms |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for subset, values in summary["by_subset"].items():
        lines.append(
            f"| {subset} | {values['cases']} | {values['pass_rate']:.2%} | "
            f"{values['context_precision']:.2%} | {values['context_recall']:.2%} | "
            f"{values['hit_at_k']:.2%} | {values['faithfulness']:.2%} | "
            f"{values['answer_relevance']:.2%} | {values['avg_latency_ms']} |"
        )
    strict = summary["by_subset"]["strict_non_preset"]
    lines.extend(
        [
            "",
            "## 评估结论",
            "",
            f"- 严格非预设样本通过率为 {strict['pass_rate']:.2%}，明显低于规则路径，说明此前只用少量 `domain_qa.py` 预设题无法代表真实 RAG 能力。",
            f"- 非预设样本 Hit@K 为 {strict['hit_at_k']:.2%}，Context Precision 为 {strict['context_precision']:.2%}，主要瓶颈在教材证据召回和页码命中，而不是答案格式。",
            f"- 生成层 Faithfulness 为 {strict['faithfulness']:.2%}，说明在检索证据不足时系统倾向于保守拒答，降低了幻觉风险，但也导致大量教材内问题回答为“无法确定”。",
            "- 后续优化重点应放在：重建 Qdrant 切片与元数据、增强章节/页码/术语索引、把 Neo4j 实体别名回填到向量检索查询、并减少“证据不足”判断过严的问题。",
        ]
    )
    lines.extend(
        [
            "",
            "## 明细",
            "",
            "| ID | 类别 | 预设 | 通过 | 模式 | C.Precision | C.Recall | MRR | NDCG | Faithfulness | Relevance | 耗时/ms |",
            "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for item in report["results"]:
        lines.append(
            f"| {item['id']} | {item['category']} | {'是' if item['is_preset'] else '否'} | {'是' if item['pass'] else '否'} | "
            f"{item['retrieval_mode']} | {item['context_precision']:.2%} | {item['context_recall']:.2%} | "
            f"{item['mrr']:.2%} | {item['ndcg']:.2%} | {item['faithfulness']:.2%} | "
            f"{item['answer_relevance']:.2%} | {item['wall_elapsed_ms']} |"
        )
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "本评估根据 `RAG评估体系.docx` 中的指标进行工程化近似实现，不额外调用 LLM-as-Judge。",
            "默认评估集来自 `data/evaluation/rag_eval_dataset.jsonl`，其中 `is_preset=false` 的样本作为严格主评估集；`is_preset=true` 的样本仅用于验证规则智能体与快捷路径。",
            "Context Precision、Context Recall、MRR、NDCG 基于期望页码与返回文档页码计算。",
            "Faithfulness、Answer Relevance、Completeness、Correctness、Fluency 采用证据命中、引用、关键词覆盖、格式与乱码检测等规则近似计算。",
            "Graph RAG 类问题会调用云雾模型，因此耗时显著高于 book_profile 和 domain_qa 快速路径。",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="JSONL evaluation dataset path.")
    parser.add_argument("--limit", type=int, default=0, help="Evaluate only the first N cases after filtering.")
    parser.add_argument("--category", action="append", help="Evaluate only selected category; can be repeated.")
    parser.add_argument("--no-cache-repeat", action="store_true", help="Do not run the second cached request.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    cases = load_cases(Path(args.dataset))
    if args.category:
        selected = set(args.category)
        cases = [case for case in cases if case.category in selected]
    if args.limit:
        cases = cases[: args.limit]
    with TestClient(app) as client:
        results = [evaluate_case(client, case, repeat_cached=not args.no_cache_repeat) for case in cases]
    report = {
        "generated_at": started,
        "dataset": str(Path(args.dataset).resolve()),
        "summary": summarize(results),
        "results": results,
    }
    json_path = OUT_DIR / "rag_eval_results.json"
    md_path = OUT_DIR / "rag_eval_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, md_path)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")


if __name__ == "__main__":
    main()
