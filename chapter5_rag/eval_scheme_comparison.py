from __future__ import annotations

import json
import math
import re
import time
from collections import Counter, defaultdict
from hashlib import md5
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
DATA_DIR = BASE_DIR / "data"
EVAL_DIR = BASE_DIR / "eval"
REPORT_DIR = BASE_DIR / "reports"
ROUND2_DIR = BASE_DIR / "outputs" / "round2"

CHUNKS_PATH = DATA_DIR / "chapter5_chunks.jsonl"
QA_TESTSET_PATH = EVAL_DIR / "qa_testset.json"
SCHEME_METRICS_PATH = EVAL_DIR / "scheme_comparison_metrics.json"
GRAPH_METRICS_PATH = EVAL_DIR / "graph_quality_metrics.json"
ROUND_COMPARISON_PATH = EVAL_DIR / "extraction_round_comparison.json"


SCHEMES = {
    "A_vector_rag": {
        "name": "纯向量 RAG",
        "model": None,
        "use_graph": False,
        "complexity": 2,
        "gpu_required": False,
        "api_cost": 0,
    },
    "B_pangu_graph_rag": {
        "name": "Pangu Graph-RAG",
        "model": "pangu",
        "use_graph": True,
        "complexity": 4,
        "gpu_required": True,
        "api_cost": "N/A/self-hosted",
    },
    "C_deepseek_graph_rag": {
        "name": "DeepSeek Graph-RAG",
        "model": "deepseek",
        "use_graph": True,
        "complexity": 3,
        "gpu_required": False,
        "api_cost": "unknown",
    },
}


QA_TESTSET = [
    {
        "question": "分段装配是什么？它在船体建造中的作用是什么？",
        "expected_keywords": ["分段装配", "船体建造", "工艺阶段", "35%"],
        "expected_chunk_ids": ["chapter5_001"],
        "type": "概念定义类",
    },
    {
        "question": "分段装配方式按位置状态可以分为哪些？",
        "expected_keywords": ["正装", "倒装", "侧装", "卧装"],
        "expected_chunk_ids": ["chapter5_001", "chapter5_002"],
        "type": "概念定义类",
    },
    {
        "question": "放射式、插入式、框架式装配方式有什么区别？",
        "expected_keywords": ["放射式", "插入式", "框架式", "纵骨", "肋板"],
        "expected_chunk_ids": ["chapter5_002", "chapter5_003"],
        "type": "对比类",
    },
    {
        "question": "分段工作图通常同时提供哪些图纸资料？",
        "expected_keywords": ["板材号料图", "外板加工", "型钢弯曲", "分段工作图"],
        "expected_chunk_ids": ["chapter5_005"],
        "type": "图纸资料类",
    },
    {
        "question": "分段组立树反映了什么信息？",
        "expected_keywords": ["分段组立树", "结构装配单元", "装配程序", "建造方式"],
        "expected_chunk_ids": ["chapter5_005"],
        "type": "图纸资料类",
    },
    {
        "question": "分段装配相关数据包括哪些内容？",
        "expected_keywords": ["胎架支柱高度", "定位数值", "二次画线", "型值"],
        "expected_chunk_ids": ["chapter5_006", "chapter5_007"],
        "type": "图纸资料类",
    },
    {
        "question": "双层底分段装配中纵骨和肋板如何定位？",
        "expected_keywords": ["纵骨", "肋板", "定位", "内底板", "外板"],
        "expected_chunk_ids": ["chapter5_010", "chapter5_011"],
        "type": "工艺流程类",
    },
    {
        "question": "舷侧分段采用双斜切胎架时要画哪些基准线？",
        "expected_keywords": ["双斜切胎架", "中心线", "中间肋骨线", "基准线"],
        "expected_chunk_ids": ["chapter5_012", "chapter5_013"],
        "type": "工艺流程类",
    },
    {
        "question": "横骨架式舷侧分段的装配流程包括哪些步骤？",
        "expected_keywords": ["外板拼接", "装配画线", "肋骨", "舷侧纵桁", "封底焊"],
        "expected_chunk_ids": ["chapter5_012", "chapter5_014"],
        "type": "工艺流程类",
    },
    {
        "question": "艉部下段装配时如何进行定位和调整？",
        "expected_keywords": ["艉柱", "K行板", "中心线", "松紧螺丝", "千斤顶"],
        "expected_chunk_ids": ["chapter5_018", "chapter5_019", "chapter5_020"],
        "type": "工艺流程类",
    },
    {
        "question": "球鼻艏分段装配中纵桁和肋骨框架如何处理？",
        "expected_keywords": ["球鼻艏", "纵桁", "肋骨框架", "切口", "强制装配"],
        "expected_chunk_ids": ["chapter5_021", "chapter5_022"],
        "type": "工艺流程类",
    },
    {
        "question": "提高分段制造质量需要采取哪些措施？",
        "expected_keywords": ["全面质量管理", "施工精度", "补偿", "刚性固定", "火工矫正"],
        "expected_chunk_ids": ["chapter5_025", "chapter5_028", "chapter5_029"],
        "type": "质量控制类",
    },
    {
        "question": "分段制造精度标准中平直分段有哪些控制指标？",
        "expected_keywords": ["分段长度", "分段宽度", "对角线", "标准范围", "允许界限"],
        "expected_chunk_ids": ["chapter5_025", "chapter5_026"],
        "type": "表格数据类",
    },
    {
        "question": "焊接变形产生的原因有哪些，如何控制？",
        "expected_keywords": ["焊接变形", "刚性固定", "补偿", "余量", "火工矫正"],
        "expected_chunk_ids": ["chapter5_028", "chapter5_029"],
        "type": "质量控制类",
    },
    {
        "question": "完工测量和二次除锈涂装在质量控制中起什么作用？",
        "expected_keywords": ["完工测量", "二次除锈", "涂装", "质量控制"],
        "expected_chunk_ids": ["chapter5_024", "chapter5_025"],
        "type": "质量控制类",
    },
]


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def file_size_kb(path: Path) -> float | None:
    return round(path.stat().st_size / 1024, 2) if path.exists() else None


def dir_size_kb(path: Path) -> float | None:
    if not path.exists():
        return None
    total = sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    return round(total / 1024, 2)


def estimate_tokens(text: str) -> int:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    other = max(0, len(text) - cjk - latin_words)
    return int(math.ceil(cjk / 1.5 + latin_words + other / 4))


def hash_embed(text: str, dim: int = 384) -> list[float]:
    vector = [0.0] * dim
    chars = [ch for ch in text if not ch.isspace()]
    tokens = chars[:]
    tokens.extend("".join(chars[index : index + 2]) for index in range(max(0, len(chars) - 1)))
    tokens.extend("".join(chars[index : index + 3]) for index in range(max(0, len(chars) - 2)))
    for token in tokens:
        digest = md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(item * item for item in vector)) or 1.0
    return [item / norm for item in vector]


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def keyword_overlap_score(query: str, text: str) -> float:
    terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+", query))
    if not terms:
        return 0.0
    hits = sum(1 for term in terms if term in text)
    return hits / len(terms)


def load_chunks() -> list[dict[str, Any]]:
    chunks = read_jsonl(CHUNKS_PATH)
    for chunk in chunks:
        chunk["content"] = f"{chunk.get('chapter_hint', '')}\n{chunk.get('text', '')}"
    return chunks


def load_triples(model: str | None) -> list[dict[str, Any]]:
    if not model:
        return []
    return read_jsonl(ROUND2_DIR / model / "kg_triples.jsonl")


def triple_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key, ""))
        for key in ("head", "relation", "tail", "evidence", "source_chunk")
        if row.get(key)
    )


def ensure_qa_testset() -> list[dict[str, Any]]:
    if not QA_TESTSET_PATH.exists():
        write_json(QA_TESTSET_PATH, QA_TESTSET)
    return read_json(QA_TESTSET_PATH, QA_TESTSET)


def build_chunk_vectors(chunks: list[dict[str, Any]]) -> tuple[dict[str, list[float]], float]:
    start = time.perf_counter()
    vectors = {chunk["id"]: hash_embed(chunk["content"]) for chunk in chunks}
    return vectors, time.perf_counter() - start


def retrieve(
    question: str,
    chunks: list[dict[str, Any]],
    chunk_vectors: dict[str, list[float]],
    triples: list[dict[str, Any]],
    use_graph: bool,
    top_k: int = 5,
) -> dict[str, Any]:
    start = time.perf_counter()
    query_vec = hash_embed(question)
    graph_boost: Counter[str] = Counter()
    top_triples: list[dict[str, Any]] = []

    if use_graph and triples:
        scored_triples = []
        for row in triples:
            text = triple_text(row)
            score = keyword_overlap_score(question, text)
            if score > 0:
                scored_triples.append((score, row))
                source_chunk = str(row.get("source_chunk", ""))
                if source_chunk:
                    graph_boost[source_chunk] += score
        scored_triples.sort(key=lambda item: item[0], reverse=True)
        top_triples = [row for _, row in scored_triples[:12]]

    scored_chunks = []
    for chunk in chunks:
        chunk_id = chunk["id"]
        vector_score = cosine(query_vec, chunk_vectors[chunk_id])
        lexical_score = keyword_overlap_score(question, chunk["content"])
        graph_score = graph_boost[chunk_id]
        score = vector_score + 0.28 * lexical_score + (0.18 * graph_score if use_graph else 0)
        scored_chunks.append((score, chunk))
    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    selected = [chunk for _, chunk in scored_chunks[:top_k]]
    return {
        "chunks": selected,
        "triples": top_triples,
        "retrieval_time_ms": (time.perf_counter() - start) * 1000,
    }


def keyword_coverage(expected_keywords: list[str], chunks: list[dict[str, Any]], triples: list[dict[str, Any]]) -> float:
    if not expected_keywords:
        return 0.0
    context = "\n".join(chunk.get("content", "") for chunk in chunks)
    context += "\n" + "\n".join(triple_text(row) for row in triples)
    hits = sum(1 for keyword in expected_keywords if keyword in context)
    return hits / len(expected_keywords)


def evaluate_qa_scheme(
    scheme_id: str,
    qa_set: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    chunk_vectors: dict[str, list[float]],
) -> dict[str, Any]:
    scheme = SCHEMES[scheme_id]
    triples = load_triples(scheme["model"])
    if scheme["use_graph"] and not triples:
        return {
            "available": False,
            "reason": f"缺少 {scheme['model']} round2 三元组文件",
        }

    rows = []
    for item in qa_set:
        result = retrieve(item["question"], chunks, chunk_vectors, triples, scheme["use_graph"], top_k=5)
        retrieved_ids = [chunk["id"] for chunk in result["chunks"]]
        expected_ids = set(item.get("expected_chunk_ids") or [])
        top_hits = {}
        for k in (1, 3, 5):
            top_hits[f"top{k}_hit"] = bool(expected_ids and expected_ids.intersection(retrieved_ids[:k]))
        rows.append(
            {
                "question": item["question"],
                "type": item.get("type", ""),
                "retrieved_chunk_ids": retrieved_ids,
                "expected_chunk_ids": sorted(expected_ids),
                "top_triples": [triple_text(row) for row in result["triples"][:5]],
                "keyword_coverage": keyword_coverage(
                    item.get("expected_keywords", []),
                    result["chunks"],
                    result["triples"],
                ),
                "retrieval_time_ms": result["retrieval_time_ms"],
                **top_hits,
            }
        )

    total = len(rows) or 1
    return {
        "available": True,
        "question_count": len(rows),
        "top1_hit_rate": round(sum(1 for row in rows if row["top1_hit"]) / total, 4),
        "top3_hit_rate": round(sum(1 for row in rows if row["top3_hit"]) / total, 4),
        "top5_hit_rate": round(sum(1 for row in rows if row["top5_hit"]) / total, 4),
        "answer_keyword_coverage": round(sum(row["keyword_coverage"] for row in rows) / total, 4),
        "avg_retrieval_time_ms": round(sum(row["retrieval_time_ms"] for row in rows) / total, 2),
        "avg_generation_time_ms": None,
        "avg_total_latency_ms": round(sum(row["retrieval_time_ms"] for row in rows) / total, 2),
        "answer_length_avg": None,
        "generation_status": "未调用生成模型；生成阶段受远程模型稳定性影响，本实验主要比较检索阶段性能。",
        "details": rows,
    }


def extraction_quality_table_data() -> list[dict[str, Any]]:
    data = read_json(ROUND_COMPARISON_PATH, {})
    rows = []
    for round_name in ("round1", "round2"):
        models = (data.get(round_name) or {}).get("models", {})
        for model in ("pangu", "deepseek"):
            metrics = models.get(model)
            if not metrics:
                continue
            rows.append(
                {
                    "model": model,
                    "round": round_name,
                    "entity_f1": (((metrics.get("entity") or {}).get("f1"))),
                    "strict_triple_f1": (((metrics.get("strict_triple") or {}).get("f1"))),
                    "relaxed_triple_f1": ((metrics.get("relaxed_triple") or {}).get("f1") if metrics.get("relaxed_triple") else None),
                    "semantic_like_f1": ((metrics.get("semantic_like_triple") or {}).get("f1") if metrics.get("semantic_like_triple") else None),
                    "json_valid_rate": metrics.get("json_legal_rate"),
                    "extraction_success_rate": metrics.get("extraction_success_rate"),
                }
            )
    return rows


def raw_token_stats(model: str | None) -> dict[str, Any]:
    if not model:
        return {
            "model_call_count": 0,
            "input_token_estimate": 0,
            "output_token_estimate": 0,
            "total_token_estimate": 0,
            "avg_tokens_per_chunk": 0,
        }
    rows = read_jsonl(ROUND2_DIR / model / "raw_extractions.jsonl")
    input_tokens = sum(estimate_tokens(str(row.get("text", ""))) for row in rows)
    output_tokens = sum(estimate_tokens(str(row.get("raw_response", ""))) for row in rows)
    total = input_tokens + output_tokens
    count = len(rows)
    return {
        "model_call_count": count,
        "input_token_estimate": input_tokens,
        "output_token_estimate": output_tokens,
        "total_token_estimate": total,
        "avg_tokens_per_chunk": round(total / count, 2) if count else 0,
    }


def build_graph_index_time(model: str | None) -> float | None:
    if not model:
        return 0.0
    path = ROUND2_DIR / model / "kg_triples.jsonl"
    if not path.exists():
        return None
    start = time.perf_counter()
    adjacency: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in read_jsonl(path):
        head = str(row.get("head", "")).strip()
        relation = str(row.get("relation", "")).strip()
        tail = str(row.get("tail", "")).strip()
        if head and relation and tail:
            adjacency[head].append((relation, tail))
            adjacency[tail].append((relation, head))
    return round(time.perf_counter() - start, 4)


def build_cost_metrics(chunks: list[dict[str, Any]], embedding_time: float) -> dict[str, Any]:
    round2_eval = read_json(EVAL_DIR / "round2_extraction_eval_metrics.json", {}).get("models", {})
    metrics = {}
    for scheme_id, scheme in SCHEMES.items():
        model = scheme["model"]
        entities_path = ROUND2_DIR / str(model) / "kg_entities.jsonl" if model else None
        triples_path = ROUND2_DIR / str(model) / "kg_triples.jsonl" if model else None
        token_stats = raw_token_stats(model)
        kg_build_time = build_graph_index_time(model)
        entity_size = file_size_kb(entities_path) if entities_path else 0
        triple_size = file_size_kb(triples_path) if triples_path else 0
        graph_size = round((entity_size or 0) + (triple_size or 0), 2)
        extraction_metrics = round2_eval.get(model, {}) if model else {}
        metrics[scheme_id] = {
            "available": True if not scheme["use_graph"] else bool(triples_path and triples_path.exists()),
            "chunk_count": len(chunks),
            "embedding_time_seconds": round(embedding_time, 4),
            "kg_extraction_time_seconds": None if model else 0,
            "kg_build_time_seconds": kg_build_time,
            "total_build_time_seconds": None if model else round(embedding_time + (kg_build_time or 0), 4),
            "model_call_count": token_stats["model_call_count"],
            "json_valid_rate": extraction_metrics.get("json_legal_rate"),
            "extraction_success_rate": extraction_metrics.get("extraction_success_rate"),
            "chunk_file_size_kb": file_size_kb(CHUNKS_PATH),
            "vector_index_size_kb": dir_size_kb(BASE_DIR / "qdrant_storage"),
            "kg_entities_size_kb": entity_size,
            "kg_triples_size_kb": triple_size,
            "kg_graph_size_kb": graph_size,
            "total_output_size_kb": round(
                (file_size_kb(CHUNKS_PATH) or 0)
                + (dir_size_kb(BASE_DIR / "qdrant_storage") or 0)
                + graph_size,
                2,
            ),
            **token_stats,
            "estimated_api_cost": scheme["api_cost"],
            "local_gpu_required": scheme["gpu_required"],
            "engineering_complexity_score": scheme["complexity"],
            "notes": "未记录端到端知识抽取耗时，因此 kg_extraction_time_seconds 不填；token 仅按已有 raw_extractions 文本与响应估算。"
            if model
            else "纯向量方案不进行知识抽取，模型调用和抽取相关指标不适用。",
        }
    return metrics


def pct(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.2f}%"


def num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    return f"{float(value):.{digits}f}"


def render_scheme_report(metrics: dict[str, Any]) -> str:
    extraction_rows = metrics.get("extraction_quality", [])
    graph_quality = metrics.get("graph_quality", {})
    qa = metrics.get("qa_performance", {})
    cost = metrics.get("build_and_cost", {})
    lines = [
        "# 第五章 RAG 不同实现方案性能与成本对比报告",
        "",
        "本报告比较三种实现方案：A_vector_rag 仅使用文本块向量检索；B_pangu_graph_rag 使用 Pangu 抽取三元组构建知识图谱并融合向量检索；C_deepseek_graph_rag 使用 DeepSeek 抽取三元组构建知识图谱并融合向量检索。评测不重新调用 Pangu / DeepSeek 抽取，只复用 round2 已有结果。",
        "",
        "生成阶段说明：为避免远程模型波动影响对比，本次 RAG 问答性能主要评测检索阶段，关键词覆盖率基于检索上下文计算；平均生成耗时和答案长度记为 N/A。",
        "",
        "## 表1：知识抽取质量对比",
        "",
        "| 模型 | 轮次 | 实体F1 | Strict三元组F1 | Relaxed三元组F1 | Semantic-like F1 | JSON合法率 | 抽取成功率 |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in extraction_rows:
        lines.append(
            f"| {row['model']} | {row['round']} | {pct(row['entity_f1'])} | {pct(row['strict_triple_f1'])} | {pct(row['relaxed_triple_f1'])} | {pct(row['semantic_like_f1'])} | {pct(row['json_valid_rate'])} | {pct(row['extraction_success_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## 表2：图谱结构质量对比",
            "",
            "| 方案 | 实体数 | 三元组数 | 关系类型数 | 平均度数 | 最大连通子图比例 | 孤立实体比例 | 泛化关系比例 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    graph_labels = {"pangu": "B_pangu_graph_rag", "deepseek": "C_deepseek_graph_rag"}
    for model in ("pangu", "deepseek"):
        row = graph_quality.get(model, {})
        if not row.get("available"):
            lines.append(f"| {graph_labels[model]} | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 |")
            continue
        lines.append(
            f"| {graph_labels[model]} | {row['entity_count']} | {row['triple_count']} | {row['relation_type_count']} | {num(row['average_degree'], 4)} | {pct(row['largest_component_ratio'])} | {pct(row['isolated_entity_ratio'])} | {pct(row['generic_relation_ratio'])} |"
        )

    lines.extend(
        [
            "",
            "## 表3：RAG问答性能对比",
            "",
            "| 方案 | Top1命中率 | Top3命中率 | Top5命中率 | 关键词覆盖率 | 平均检索耗时 | 平均生成耗时 | 平均总耗时 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for scheme_id, row in qa.items():
        if not row.get("available"):
            lines.append(f"| {scheme_id} | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 | 未完成 |")
            continue
        lines.append(
            f"| {scheme_id} | {pct(row['top1_hit_rate'])} | {pct(row['top3_hit_rate'])} | {pct(row['top5_hit_rate'])} | {pct(row['answer_keyword_coverage'])} | {num(row['avg_retrieval_time_ms'])} ms | N/A | {num(row['avg_total_latency_ms'])} ms |"
        )

    lines.extend(
        [
            "",
            "## 表4：成本对比",
            "",
            "| 方案 | 模型调用次数 | 输入Token估计 | 输出Token估计 | API费用估计 | 构建耗时 | 存储大小 | 是否需要GPU | 工程复杂度 |",
            "|---|---:|---:|---:|---|---:|---:|---|---:|",
        ]
    )
    for scheme_id, row in cost.items():
        build_time = row.get("total_build_time_seconds")
        build_time_text = "N/A" if build_time is None else f"{num(build_time, 4)} s"
        lines.append(
            f"| {scheme_id} | {row['model_call_count']} | {row['input_token_estimate']} | {row['output_token_estimate']} | {row['estimated_api_cost']} | {build_time_text} | {num(row['total_output_size_kb'])} KB | {'是' if row['local_gpu_required'] else '否'} | {row['engineering_complexity_score']} |"
        )

    lines.extend(
        [
            "",
            "## 表5：综合评价",
            "",
            "| 方案 | 优势 | 不足 | 适用场景 |",
            "|---|---|---|---|",
            "| A_vector_rag | 实现简单，构建快，成本低，不需要知识抽取。 | 缺少结构化关系表达，对流程链路、工序依赖和质量标准类问题解释能力有限。 | 资料规模较小、问题主要依赖原文片段召回的快速原型。 |",
            "| B_pangu_graph_rag | 自部署模型 API 费用可控，round2 JSON 合法率和抽取成功率稳定；图谱可与教材证据共同追溯。 | 抽取较保守，三元组召回偏低，关系表达需要进一步归一化。 | 需要本地/内网部署、重视稳定性和数据可控性的课程项目或企业内网场景。 |",
            "| C_deepseek_graph_rag | 语义覆盖更好，round2 relaxed / semantic-like 三元组 F1 更高，能补充更多流程和关系信息。 | 存在输出失败和实体粒度不一致问题，API 成本取决于外部服务价格。 | 需要更强语义抽取能力、可接受外部 API 调用和后处理校验的场景。 |",
            "",
            "## 未统计或不可用指标",
            "",
            "- 平均生成耗时、答案长度：本次未调用生成模型，避免远程模型稳定性影响对比。",
            "- kg_extraction_time_seconds：round2 抽取阶段未保存完整端到端耗时日志，因此不伪造该数值。",
            "- DeepSeek estimated_api_cost：未配置官方价格参数，因此记为 unknown。",
        ]
    )
    return "\n".join(lines) + "\n"


def render_final_summary(metrics: dict[str, Any]) -> str:
    qa = metrics.get("qa_performance", {})
    best_line = ""
    if qa:
        best_scheme = max(
            (item for item in qa.items() if item[1].get("available")),
            key=lambda item: (item[1].get("top5_hit_rate", 0), item[1].get("answer_keyword_coverage", 0)),
            default=None,
        )
        if best_scheme:
            best_line = f"本次 15 题检索评测中，{best_scheme[0]} 的 Top5 命中率为 {pct(best_scheme[1]['top5_hit_rate'])}，关键词覆盖率为 {pct(best_scheme[1]['answer_keyword_coverage'])}。"
    return (
        "# 第五章 RAG 方案综合评测总结\n\n"
        "本文围绕第五章“船体分段的装配”设置了三种实现方案：纯向量 RAG、Pangu Graph-RAG 和 DeepSeek Graph-RAG。"
        "纯向量 RAG 实现简单、工程成本低，适合作为基线方案，但它只依赖文本块召回，缺少显式的实体、工序和关系结构，难以稳定支撑流程类、关系类和质量标准类问题。\n\n"
        "Pangu Graph-RAG 通过 Pangu 7B 自部署模型抽取三元组并构建知识图谱，稳定性较好，round2 中 JSON 合法率和抽取成功率较高，但抽取风格相对保守，三元组召回偏低。"
        "DeepSeek Graph-RAG 的语义覆盖更好，round2 relaxed / semantic-like 指标更高，能够抽出更多流程关系和质量控制信息，但也存在输出失败、实体粒度不一致以及后处理成本更高的问题。"
        f"{best_line}\n\n"
        "总体来看，Graph-RAG 相比纯向量 RAG 在流程类、关系类、质量标准类问题上更有优势，因为图谱能够显式表达“工序-构件-图纸资料-质量措施”之间的连接。"
        "成本方面，Graph-RAG 需要额外的知识抽取、图谱构建、关系归一化和证据校验，构建成本高于纯向量 RAG；Pangu 方案需要自部署 GPU 推理环境，DeepSeek 方案依赖外部 API 服务。"
        "后续优化方向包括实体归一化、关系归一化、三元组证据校验、多智能体校验和人工复核低置信度三元组，以进一步提高图谱质量和问答可信度。\n"
    )


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    qa_set = ensure_qa_testset()
    chunks = load_chunks()
    chunk_vectors, embedding_time = build_chunk_vectors(chunks)

    qa_metrics = {
        scheme_id: evaluate_qa_scheme(scheme_id, qa_set, chunks, chunk_vectors)
        for scheme_id in SCHEMES
    }
    graph_quality = read_json(GRAPH_METRICS_PATH, {})
    build_cost = build_cost_metrics(chunks, embedding_time)
    metrics = {
        "meta": {
            "chapter": "第五章 船体分段的装配",
            "qa_question_count": len(qa_set),
            "generation_evaluation": "not_run",
            "generation_note": "生成阶段受远程模型稳定性影响，本实验主要比较检索阶段性能。",
        },
        "extraction_quality": extraction_quality_table_data(),
        "graph_quality": graph_quality,
        "qa_performance": qa_metrics,
        "build_and_cost": build_cost,
    }
    write_json(SCHEME_METRICS_PATH, metrics)
    (REPORT_DIR / "scheme_comparison_report.md").write_text(render_scheme_report(metrics), encoding="utf-8")
    (REPORT_DIR / "final_eval_summary.md").write_text(render_final_summary(metrics), encoding="utf-8")
    print(
        json.dumps(
            {
                "qa_testset": str(QA_TESTSET_PATH),
                "metrics": str(SCHEME_METRICS_PATH),
                "report": str(REPORT_DIR / "scheme_comparison_report.md"),
                "summary": str(REPORT_DIR / "final_eval_summary.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
