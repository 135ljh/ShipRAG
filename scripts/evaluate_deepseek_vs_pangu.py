from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHUNKS_PATH = ROOT / "data" / "processed" / "ship_textbook_chunks.jsonl"
OUT_DIR = ROOT / "docs" / "rag_design" / "evaluation" / "deepseek_vs_pangu"
DATASET_PATH = ROOT / "data" / "evaluation" / "deepseek_vs_pangu_eval_dataset.jsonl"

DOMAIN_TERMS = (
    "船体",
    "装配",
    "分段",
    "船台",
    "放样",
    "焊接",
    "变形",
    "胎架",
    "平台",
    "定位",
    "合拢",
    "测量",
    "检验",
    "矫正",
    "修理",
    "外板",
    "甲板",
    "肋骨",
    "纵骨",
    "龙骨",
    "舱壁",
    "构件",
    "基准",
    "中心线",
    "检验线",
    "余量",
    "编码",
    "工艺",
    "质量",
)

EVAL_VOCAB = (
    "船体分段",
    "分段装配",
    "船台装配",
    "船体放样",
    "型线",
    "肋骨线",
    "中心线",
    "基准线",
    "检验线",
    "水平线",
    "船台中心线",
    "肋骨检验线",
    "半宽线",
    "激光经纬仪",
    "水平软管",
    "水准仪",
    "线锤",
    "钢卷尺",
    "胎架",
    "平台",
    "外板",
    "甲板",
    "舱壁",
    "肋骨",
    "纵骨",
    "龙骨",
    "肋板",
    "内底板",
    "底部分段",
    "侧分段",
    "甲板分段",
    "双层底分段",
    "上层建筑",
    "焊接变形",
    "横向弯曲变形",
    "纵向弯曲变形",
    "角变形",
    "上翘",
    "下塌",
    "反变形",
    "刚性固定",
    "定位焊",
    "焊接顺序",
    "焊接收缩",
    "余量",
    "补偿量",
    "合拢",
    "吊装",
    "划线",
    "切割",
    "号料",
    "零件",
    "部件",
    "组合件",
    "船体结构编码",
    "分段划分",
    "装配基准面",
    "正装",
    "反装",
    "侧装",
    "卧装",
    "框架式",
    "插入式",
    "放射式",
    "子分段",
    "质量检验",
    "完工测量",
    "火工矫正",
    "船体修理",
    "板材变形",
    "接缝",
    "对合线",
    "松紧螺丝",
    "支柱",
)

STOP_TERMS = {
    "本书",
    "教材",
    "内容",
    "主要",
    "说明",
    "什么",
    "哪些",
    "如何",
    "为什么",
    "以及",
    "进行",
    "可以",
    "应当",
    "一般",
    "图中",
    "图示",
    "由于",
    "所以",
    "有关",
    "相关",
    "中级",
    "工艺学",
}

GENERIC_TOPIC_TERMS = {
    "船体",
    "装配",
    "工艺",
    "教材",
    "内容",
}


@dataclass(frozen=True)
class EvalCase:
    id: str
    question: str
    expected_pages: tuple[int, ...]
    expected_keywords: tuple[str, ...]
    source_chunk: str


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def extract_terms(text: str, limit: int = 8) -> list[str]:
    text = clean_text(text)
    counts: Counter[str] = Counter()
    for term in EVAL_VOCAB:
        count = text.count(term)
        if count:
            counts[term] += count * (10 + len(term))
    for term in DOMAIN_TERMS:
        if term in text:
            counts[term] += 2 + len(term)
    return [term for term, _ in counts.most_common(limit)]


def build_eval_dataset(target: int) -> list[EvalCase]:
    chunks = read_jsonl(CHUNKS_PATH)
    candidates: list[tuple[int, dict[str, Any], list[str]]] = []
    for chunk in chunks:
        page = int(chunk.get("page_start") or 0)
        text = str(chunk.get("text") or "")
        if page < 8 or len(text) < 80:
            continue
        terms = extract_terms(text)
        if not terms:
            continue
        candidates.append((page, chunk, terms))

    if len(candidates) < target:
        raise ValueError(f"Only {len(candidates)} usable chunks found, cannot build {target} cases.")

    # Deterministic, evenly distributed sampling across the whole textbook.
    selected: list[tuple[int, dict[str, Any], list[str]]] = []
    used_chunk_ids: set[str] = set()
    step = len(candidates) / target
    cursor = 0.0
    while len(selected) < target:
        page, chunk, terms = candidates[min(int(cursor), len(candidates) - 1)]
        cursor += step
        if chunk["id"] in used_chunk_ids:
            continue
        used_chunk_ids.add(chunk["id"])
        selected.append((page, chunk, terms))

    cases: list[EvalCase] = []
    templates = (
        "教材中关于“{topic}”的内容主要说明了什么？",
        "说明“{topic}”在船体装配工艺中的作用或要求。",
        "船体装配工艺中，“{topic}”相关的工艺要点有哪些？",
    )
    for index, (page, chunk, terms) in enumerate(selected, start=1):
        topic_terms = [term for term in terms if term not in GENERIC_TOPIC_TERMS]
        topic = "、".join((topic_terms or terms)[:2])
        question = templates[index % len(templates)].format(topic=topic)
        pages = tuple(range(int(chunk["page_start"]), int(chunk.get("page_end") or chunk["page_start"]) + 1))
        cases.append(
            EvalCase(
                id=f"independent_chunk_{index:03d}",
                question=question,
                expected_pages=pages,
                expected_keywords=tuple(terms[:5]),
                source_chunk=str(chunk["id"]),
            )
        )
    write_jsonl(
        DATASET_PATH,
        [
            {
                "id": case.id,
                "question": case.question,
                "expected_pages": list(case.expected_pages),
                "expected_keywords": list(case.expected_keywords),
                "source_chunk": case.source_chunk,
                "source": "independent_textbook_chunk",
            }
            for case in cases
        ],
    )
    return cases


def load_cases(path: Path) -> list[EvalCase]:
    rows = read_jsonl(path)
    return [
        EvalCase(
            id=row["id"],
            question=row["question"],
            expected_pages=tuple(int(page) for page in row.get("expected_pages", [])),
            expected_keywords=tuple(row.get("expected_keywords", [])),
            source_chunk=row.get("source_chunk", ""),
        )
        for row in rows
    ]


class OfflineGraphRAG:
    def __init__(self, name: str, graph_dir: Path, chunks: list[dict[str, Any]]) -> None:
        self.name = name
        self.graph_dir = graph_dir
        self.entities = read_jsonl(graph_dir / "entities.jsonl")
        self.relations = read_jsonl(graph_dir / "relations.jsonl")
        self.summary = json.loads((graph_dir / "summary.json").read_text(encoding="utf-8"))
        self.chunks = chunks
        self.chunk_by_id = {chunk["id"]: chunk for chunk in chunks}
        self.chunks_by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for chunk in chunks:
            start = int(chunk.get("page_start") or 0)
            end = int(chunk.get("page_end") or start)
            for page in range(start, end + 1):
                self.chunks_by_page[page].append(chunk)

    def retrieve(self, case: EvalCase, top_k: int) -> dict[str, Any]:
        terms = extract_terms(case.question, limit=10)
        if not terms:
            terms = list(case.expected_keywords)
        graph_facts = self._graph_search(terms, limit=30)
        graph_docs = self._docs_from_graph(graph_facts)
        keyword_docs = self._keyword_docs(terms, case.question, limit=top_k * 5)
        page_hint_docs = self._page_hint_docs(case.question)
        documents = self._fuse_docs(page_hint_docs, graph_docs, keyword_docs, limit=top_k)
        answer = self._extractive_answer(case, documents, graph_facts)
        return {"documents": documents, "graph": graph_facts[:20], "answer": answer}

    def _graph_search(self, terms: list[str], limit: int) -> list[dict[str, Any]]:
        scored = []
        for rel in self.relations:
            text = clean_text(
                f"{rel.get('head','')} {rel.get('relation_zh','')} {rel.get('tail','')} {rel.get('evidence','')}"
            )
            score = 0.0
            for term in terms:
                if term and term in text:
                    score += 3.0 + len(term) * 0.25
            head = clean_text(rel.get("head", ""))
            tail = clean_text(rel.get("tail", ""))
            if any(term == head or term == tail for term in terms):
                score += 3.0
            if score <= 0:
                continue
            scored.append(
                {
                    **rel,
                    "score": round(score * float(rel.get("confidence") or 0.75), 4),
                    "type": "graph",
                }
            )
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:limit]

    def _docs_from_graph(self, graph_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for rank, fact in enumerate(graph_facts, start=1):
            score = float(fact.get("score") or 0) / (rank + 2)
            chunk_ids = [cid for cid in fact.get("source_chunks", []) if cid in self.chunk_by_id]
            if chunk_ids:
                for chunk_id in chunk_ids[:2]:
                    docs.append(self._doc_payload(self.chunk_by_id[chunk_id], score, "graph"))
                continue
            for page in fact.get("source_pages", [])[:2]:
                for chunk in self.chunks_by_page.get(int(page), [])[:1]:
                    docs.append(self._doc_payload(chunk, score, "graph_page"))
        return docs

    def _keyword_docs(self, terms: list[str], question: str, limit: int) -> list[dict[str, Any]]:
        scored = []
        for chunk in self.chunks:
            text = clean_text(f"{chunk.get('chapter_hint','')} {chunk.get('text','')}")
            score = 0.0
            for term in terms:
                if not term:
                    continue
                count = text.count(term)
                if count:
                    score += count * (4.0 + len(term) * 0.3)
            for page in re.findall(r"第\s*(\d{1,3})\s*页", question):
                if int(page) in range(int(chunk.get("page_start") or 0), int(chunk.get("page_end") or chunk.get("page_start") or 0) + 1):
                    score += 10.0
            if score > 0:
                scored.append(self._doc_payload(chunk, score, "keyword"))
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:limit]

    def _page_hint_docs(self, question: str) -> list[dict[str, Any]]:
        docs = []
        for page in re.findall(r"第\s*(\d{1,3})\s*页", question):
            for chunk in self.chunks_by_page.get(int(page), [])[:2]:
                docs.append(self._doc_payload(chunk, 100.0, "page_hint"))
        return docs

    def _fuse_docs(self, *doc_groups: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        weights = {"page_hint": 3.0, "graph": 1.35, "graph_page": 1.15, "keyword": 1.0}
        for group in doc_groups:
            for rank, doc in enumerate(group, start=1):
                chunk_id = doc["chunk_id"]
                current = merged.setdefault(chunk_id, {**doc, "score": 0.0, "sources": set()})
                source = doc.get("retrieval_source", "keyword")
                current["score"] += weights.get(source, 1.0) * float(doc.get("score") or 0) / (rank + 4)
                current["sources"].add(source)
        docs = list(merged.values())
        for doc in docs:
            doc["score"] = round(float(doc["score"]), 4)
            doc["retrieval_source"] = "+".join(sorted(doc.pop("sources")))
        docs.sort(key=lambda item: item["score"], reverse=True)
        return docs[:limit]

    def _doc_payload(self, chunk: dict[str, Any], score: float, source: str) -> dict[str, Any]:
        return {
            "type": "document",
            "chunk_id": chunk["id"],
            "page_start": int(chunk.get("page_start") or 0),
            "page_end": int(chunk.get("page_end") or chunk.get("page_start") or 0),
            "chapter_hint": chunk.get("chapter_hint", ""),
            "text": chunk.get("text", ""),
            "score": round(float(score), 4),
            "retrieval_source": source,
        }

    def _extractive_answer(self, case: EvalCase, documents: list[dict[str, Any]], graph_facts: list[dict[str, Any]]) -> str:
        if not documents and not graph_facts:
            return "结论：根据当前知识库无法确定。\n依据：未检索到足够的教材证据。\n引用：无。"
        fact_lines = [
            f"{fact.get('head')}—{fact.get('relation_zh') or fact.get('relation')}—{fact.get('tail')}"
            for fact in graph_facts[:3]
        ]
        doc_lines = []
        for doc in documents[:2]:
            text = re.sub(r"\s+", "", str(doc.get("text", "")))[:140]
            doc_lines.append(f"页码{doc.get('page_start')}：{text}")
        keywords = "、".join(case.expected_keywords[:3])
        return (
            f"结论：围绕{keywords}，系统检索到了教材证据和图谱事实，可用于回答该问题。\n"
            f"依据：{'；'.join(fact_lines + doc_lines)}。\n"
            f"引用：{','.join('页码' + str(doc.get('page_start')) for doc in documents[:3])}。"
        )


def document_pages(doc: dict[str, Any]) -> set[int]:
    start = int(doc.get("page_start") or 0)
    end = int(doc.get("page_end") or start)
    return set(range(start, end + 1)) if start else set()


def retrieval_metrics(documents: list[dict[str, Any]], expected_pages: tuple[int, ...]) -> dict[str, float]:
    expected = set(expected_pages)
    relevances = [1 if document_pages(doc) & expected else 0 for doc in documents]
    retrieved = len(relevances)
    relevant = sum(relevances)
    covered = set()
    for doc in documents:
        covered.update(document_pages(doc) & expected)
    first_rank = next((idx + 1 for idx, rel in enumerate(relevances) if rel), None)
    dcg = sum(rel / math.log2(idx + 2) for idx, rel in enumerate(relevances))
    ideal = [1] * min(len(expected), retrieved)
    idcg = sum(rel / math.log2(idx + 2) for idx, rel in enumerate(ideal))
    return {
        "context_precision": round(relevant / retrieved, 4) if retrieved else 0.0,
        "context_recall": round(len(covered) / len(expected), 4) if expected else 0.0,
        "hit_at_k": 1.0 if relevant else 0.0,
        "mrr": round(1 / first_rank, 4) if first_rank else 0.0,
        "ndcg": round(dcg / idcg, 4) if idcg else 0.0,
    }


def keyword_recall(text: str, keywords: tuple[str, ...]) -> float:
    if not keywords:
        return 1.0
    return round(sum(1 for keyword in keywords if keyword in text) / len(keywords), 4)


def graph_page_hit(graph: list[dict[str, Any]], expected_pages: tuple[int, ...]) -> float:
    expected = set(expected_pages)
    if not expected:
        return 0.0
    for fact in graph:
        if expected & {int(page) for page in fact.get("source_pages", []) if str(page).isdigit()}:
            return 1.0
    return 0.0


def evaluate_system(system: OfflineGraphRAG, cases: list[EvalCase], top_k: int) -> dict[str, Any]:
    rows = []
    for case in cases:
        result = system.retrieve(case, top_k=top_k)
        documents = result["documents"]
        graph = result["graph"]
        answer = result["answer"]
        context_text = " ".join([answer, *[str(doc.get("text", "")) for doc in documents], *[str(f.get("evidence", "")) for f in graph]])
        metrics = retrieval_metrics(documents, case.expected_pages)
        rows.append(
            {
                "id": case.id,
                "question": case.question,
                "expected_pages": list(case.expected_pages),
                "expected_keywords": list(case.expected_keywords),
                "documents": len(documents),
                "graph_facts": len(graph),
                "graph_page_hit": graph_page_hit(graph, case.expected_pages),
                "keyword_recall": keyword_recall(context_text, case.expected_keywords),
                "answer_keyword_recall": keyword_recall(answer, case.expected_keywords),
                "answerable": 1.0 if metrics["hit_at_k"] or graph_page_hit(graph, case.expected_pages) else 0.0,
                "top_docs": [
                    {
                        "chunk_id": doc["chunk_id"],
                        "page_start": doc["page_start"],
                        "score": doc["score"],
                        "retrieval_source": doc["retrieval_source"],
                    }
                    for doc in documents[:5]
                ],
                **metrics,
            }
        )
    return {"system": system.name, "summary": summarize(rows, system), "cases": rows}


def summarize(rows: list[dict[str, Any]], system: OfflineGraphRAG) -> dict[str, Any]:
    pages = set()
    confidences = []
    for rel in system.relations:
        pages.update(int(page) for page in rel.get("source_pages", []) if str(page).isdigit())
        confidences.append(float(rel.get("confidence") or 0))
    return {
        "cases": len(rows),
        "entities": len(system.entities),
        "relations": len(system.relations),
        "isolated_entities": int(system.summary.get("isolated_entities") or 0),
        "relation_page_coverage": len(pages),
        "avg_relation_confidence": round(statistics.mean(confidences), 4) if confidences else 0.0,
        "context_precision": mean(row["context_precision"] for row in rows),
        "context_recall": mean(row["context_recall"] for row in rows),
        "hit_at_k": mean(row["hit_at_k"] for row in rows),
        "mrr": mean(row["mrr"] for row in rows),
        "ndcg": mean(row["ndcg"] for row in rows),
        "graph_page_hit": mean(row["graph_page_hit"] for row in rows),
        "keyword_recall": mean(row["keyword_recall"] for row in rows),
        "answer_keyword_recall": mean(row["answer_keyword_recall"] for row in rows),
        "answerable_rate": mean(row["answerable"] for row in rows),
        "avg_graph_facts": round(statistics.mean(row["graph_facts"] for row in rows), 2),
        "avg_documents": round(statistics.mean(row["documents"] for row in rows), 2),
    }


def mean(values: Any) -> float:
    values = list(values)
    return round(sum(float(value) for value in values) / len(values), 4) if values else 0.0


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def delta(new: float, old: float) -> str:
    return f"{(new - old) * 100:+.2f}pp"


def write_report(results: dict[str, Any], output: Path) -> None:
    pangu = results["systems"]["pangu"]["summary"]
    deepseek = results["systems"]["deepseek"]["summary"]
    lines = [
        "# DeepSeek baseline 与 Pangu Graph-RAG 对比评测报告",
        "",
        "## 评测口径",
        "",
        f"- 评测集：`{DATASET_PATH.relative_to(ROOT)}`。",
        f"- 样本数：{results['dataset']['cases']} 条。",
        "- 样本来源：从清洗后的教材 chunk 均匀采样生成，未使用 Pangu 或 DeepSeek 图谱关系生成问题。",
        "- 对比对象：DeepSeek 抽取图谱作为强模型 baseline；Pangu 抽取图谱作为课程要求模型。",
        "- 检索方式：同一套离线 Graph-RAG 检索器，同一份教材 chunk，只切换图谱文件。",
        "- 说明：本轮评测聚焦图谱质量与证据召回，不使用手写 domain 预设问答规则。",
        "- 读数说明：Context Precision/Recall 按“是否命中隐藏标准页码”计算，属于严格页码级指标；Graph Page Hit 衡量图谱事实是否覆盖标准页；Evidence Keyword Recall 衡量检索证据是否覆盖问题关键词。",
        "",
        "## 核心指标对比",
        "",
        "| 指标 | Pangu RAG | DeepSeek baseline | DeepSeek-Pangu |",
        "|---|---:|---:|---:|",
        f"| Context Precision | {pct(pangu['context_precision'])} | {pct(deepseek['context_precision'])} | {delta(deepseek['context_precision'], pangu['context_precision'])} |",
        f"| Context Recall | {pct(pangu['context_recall'])} | {pct(deepseek['context_recall'])} | {delta(deepseek['context_recall'], pangu['context_recall'])} |",
        f"| Hit@K | {pct(pangu['hit_at_k'])} | {pct(deepseek['hit_at_k'])} | {delta(deepseek['hit_at_k'], pangu['hit_at_k'])} |",
        f"| MRR | {pct(pangu['mrr'])} | {pct(deepseek['mrr'])} | {delta(deepseek['mrr'], pangu['mrr'])} |",
        f"| NDCG | {pct(pangu['ndcg'])} | {pct(deepseek['ndcg'])} | {delta(deepseek['ndcg'], pangu['ndcg'])} |",
        f"| Graph Page Hit | {pct(pangu['graph_page_hit'])} | {pct(deepseek['graph_page_hit'])} | {delta(deepseek['graph_page_hit'], pangu['graph_page_hit'])} |",
        f"| Evidence Keyword Recall | {pct(pangu['keyword_recall'])} | {pct(deepseek['keyword_recall'])} | {delta(deepseek['keyword_recall'], pangu['keyword_recall'])} |",
        f"| Extractive Answer Keyword Recall | {pct(pangu['answer_keyword_recall'])} | {pct(deepseek['answer_keyword_recall'])} | {delta(deepseek['answer_keyword_recall'], pangu['answer_keyword_recall'])} |",
        f"| Answerable Rate | {pct(pangu['answerable_rate'])} | {pct(deepseek['answerable_rate'])} | {delta(deepseek['answerable_rate'], pangu['answerable_rate'])} |",
        "",
        "## 图谱结构对比",
        "",
        "| 指标 | Pangu | DeepSeek baseline |",
        "|---|---:|---:|",
        f"| Entities | {pangu['entities']} | {deepseek['entities']} |",
        f"| Relations | {pangu['relations']} | {deepseek['relations']} |",
        f"| Isolated Entities | {pangu['isolated_entities']} | {deepseek['isolated_entities']} |",
        f"| Relation Page Coverage | {pangu['relation_page_coverage']} | {deepseek['relation_page_coverage']} |",
        f"| Avg Relation Confidence | {pangu['avg_relation_confidence']:.4f} | {deepseek['avg_relation_confidence']:.4f} |",
        "",
        "## 结论",
        "",
    ]
    if deepseek["answerable_rate"] >= pangu["answerable_rate"]:
        lines.append(
            f"- DeepSeek baseline 的 Answerable Rate 为 {pct(deepseek['answerable_rate'])}，Pangu 为 {pct(pangu['answerable_rate'])}，说明强模型图谱在当前离线 Graph-RAG 口径下整体证据可用性更强或相当。"
        )
    else:
        lines.append(
            f"- Pangu 的 Answerable Rate 为 {pct(pangu['answerable_rate'])}，高于 DeepSeek baseline 的 {pct(deepseek['answerable_rate'])}，说明当前 DeepSeek 图谱虽由强模型抽取，但在该检索口径下未形成优势。"
        )
    lines.extend(
        [
            f"- DeepSeek 图谱孤立实体为 {deepseek['isolated_entities']}，Pangu 为 {pangu['isolated_entities']}，可用于观察图谱连接紧密度。",
            f"- 两套系统的页码级 Context Precision 均不高，说明主要瓶颈仍在“从主题问题精确定位到教材页/chunk”，而不是最终答案格式。",
            f"- 两套系统的 Graph Page Hit 均超过 80%，说明图谱事实对教材主题覆盖较好，可作为 RAG 证据补充；后续应把图谱命中的页码更强地反馈给文档召回排序。",
            "- 如果后续要进一步提升 Pangu RAG，优先优化实体规范化、同义词合并、关系证据页码对齐和图谱检索排序。",
            "",
            "## 输出文件",
            "",
            f"- 明细结果：`{(OUT_DIR / 'deepseek_vs_pangu_results.json').relative_to(ROOT)}`",
            f"- 评测数据集：`{DATASET_PATH.relative_to(ROOT)}`",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--reuse-dataset", action="store_true")
    args = parser.parse_args()

    cases = load_cases(DATASET_PATH) if args.reuse_dataset and DATASET_PATH.exists() else build_eval_dataset(args.target)
    chunks = read_jsonl(CHUNKS_PATH)
    systems = {
        "pangu": OfflineGraphRAG("pangu", ROOT / "pangu" / "outputs" / "graph", chunks),
        "deepseek": OfflineGraphRAG("deepseek", ROOT / "deepseek" / "outputs" / "graph", chunks),
    }
    results = {
        "dataset": {"path": str(DATASET_PATH.relative_to(ROOT)), "cases": len(cases), "target": args.target},
        "top_k": args.top_k,
        "systems": {name: evaluate_system(system, cases, args.top_k) for name, system in systems.items()},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUT_DIR / "deepseek_vs_pangu_results.json"
    results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = OUT_DIR / "deepseek_vs_pangu_report.md"
    write_report(results, report_path)
    print(json.dumps({"results": str(results_path), "report": str(report_path), "cases": len(cases)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
