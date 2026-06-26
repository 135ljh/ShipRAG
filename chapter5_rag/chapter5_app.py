from __future__ import annotations

import json
import math
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chapter5_rag.chapter5_vector import Chapter5Qdrant


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
DATA_DIR = BASE_DIR / "data"
GRAPH_DIR = BASE_DIR / "outputs" / "graph"
WEB_DIR = BASE_DIR / "web"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def terms(text: str) -> list[str]:
    vocab = [
        "分段装配",
        "装配方式",
        "正装",
        "反装",
        "侧装",
        "卧装",
        "放射式",
        "插入式",
        "框架式",
        "散装式",
        "子分段",
        "双层底分段",
        "舷侧分段",
        "胎架",
        "平台",
        "肋板",
        "纵骨",
        "纵桁",
        "外板",
        "甲板",
        "焊接变形",
        "反变形",
        "刚性固定",
        "分段工作图",
        "完工测量",
        "分段定位",
        "吊装",
        "合拢",
        "余量",
        "补偿量",
        "基准线",
        "中心线",
    ]
    result = [word for word in vocab if word in text]
    candidates = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}", text)
    stop = {"教材", "第五章", "内容", "什么", "哪些", "如何", "说明", "主要", "进行", "相关"}
    for item in candidates:
        if item in stop:
            continue
        if item not in result:
            result.append(item)
    return result[:20]


def score_text(query_terms: list[str], text: str) -> float:
    clean = compact(text)
    score = 0.0
    for term in query_terms:
        count = clean.count(compact(term))
        if count:
            score += count * (4.0 + math.log1p(len(term)))
        elif len(term) >= 3:
            chars = set(term)
            overlap = sum(1 for ch in chars if ch in clean) / max(len(chars), 1)
            if overlap >= 0.65:
                score += overlap * len(term) * 0.5
    if not score and query_terms:
        query_chars = set("".join(query_terms))
        if query_chars:
            overlap = sum(1 for ch in query_chars if ch in clean) / len(query_chars)
            if overlap >= 0.45:
                score += overlap
    return score


class PanguClient:
    def __init__(self) -> None:
        load_dotenv(ROOT / "pangu" / ".env")
        load_dotenv(BASE_DIR / ".env")
        self.base_url = os.getenv("PANGU_BASE_URL", "http://10.21.77.7:8000").rstrip("/")
        self.generate_path = os.getenv("PANGU_GENERATE_PATH", "/generate")
        self.health_path = os.getenv("PANGU_HEALTH_PATH", "/health")
        self.timeout = int(os.getenv("PANGU_TIMEOUT", "240"))

    def health(self) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}{self.health_path}", timeout=15)
        response.raise_for_status()
        try:
            return response.json()
        except Exception:
            return {"status": response.text}

    def generate(self, prompt: str, max_new_tokens: int = 700) -> str:
        response = requests.post(
            f"{self.base_url}{self.generate_path}",
            json={"prompt": prompt, "max_new_tokens": max_new_tokens, "temperature": 0.0},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("content") or data.get("text") or data.get("response") or json.dumps(data, ensure_ascii=False)


class Chapter5RAG:
    def __init__(self) -> None:
        self.chunks = read_jsonl(DATA_DIR / "chapter5_chunks.jsonl")
        self.entities = read_jsonl(GRAPH_DIR / "entities.jsonl")
        self.relations = read_jsonl(GRAPH_DIR / "relations.jsonl")
        self.summary = json.loads((GRAPH_DIR / "summary.json").read_text(encoding="utf-8"))
        self.chunk_by_id = {chunk["id"]: chunk for chunk in self.chunks}
        self.relations_by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for rel in self.relations:
            self.relations_by_entity[rel["head"]].append(rel)
            self.relations_by_entity[rel["tail"]].append(rel)
        self.pangu = PanguClient()
        try:
            self.qdrant = Chapter5Qdrant()
            self.qdrant_enabled = True
        except Exception:
            self.qdrant = None
            self.qdrant_enabled = False

    def retrieve_documents(self, question: str, top_k: int) -> list[dict[str, Any]]:
        q_terms = terms(question)
        keyword_results = []
        for chunk in self.chunks:
            score = score_text(q_terms, f"{chunk.get('chapter_hint','')} {chunk.get('text','')}")
            if score <= 0:
                continue
            keyword_results.append({**chunk, "score": round(score, 4), "type": "document", "retrieval_source": "keyword"})
        keyword_results.sort(key=lambda row: row["score"], reverse=True)
        vector_results: list[dict[str, Any]] = []
        if self.qdrant_enabled and self.qdrant is not None:
            try:
                vector_results = self.qdrant.search(question, top_k=max(12, top_k * 4))
            except Exception:
                vector_results = []
        return self.fuse_documents(vector_results, keyword_results, top_k)

    def fuse_documents(self, vector_results: list[dict[str, Any]], keyword_results: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for weight, rows in ((1.15, vector_results), (1.35, keyword_results)):
            for rank, row in enumerate(rows, start=1):
                chunk_id = row.get("chunk_id") or row.get("id")
                if not chunk_id:
                    continue
                current = merged.setdefault(
                    chunk_id,
                    {
                        "id": chunk_id,
                        "chunk_id": chunk_id,
                        "source": row.get("source"),
                        "page_start": row.get("page_start"),
                        "page_end": row.get("page_end"),
                        "chapter_hint": row.get("chapter_hint", ""),
                        "text": row.get("text", ""),
                        "char_count": row.get("char_count", len(row.get("text", ""))),
                        "type": "document",
                        "score": 0.0,
                        "sources": [],
                    },
                )
                current["score"] += weight / (60 + rank)
                current["sources"].append(row.get("retrieval_source") or "keyword")
                if row.get("text") and len(row.get("text", "")) > len(current.get("text", "")):
                    current["text"] = row["text"]
        docs = list(merged.values())
        for doc in docs:
            doc["score"] = round(float(doc["score"]), 6)
            doc["retrieval_source"] = "+".join(sorted(set(doc.pop("sources"))))
        docs.sort(key=lambda item: item["score"], reverse=True)
        return docs[:top_k]

    def retrieve_graph(self, question: str, hops: int, limit: int = 24) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        q_terms = terms(question)
        matched_entities = []
        for ent in self.entities:
            text = f"{ent.get('name','')} {ent.get('definition','')}"
            score = score_text(q_terms, text)
            if score > 0:
                matched_entities.append({**ent, "score": round(score, 4)})
        matched_entities.sort(key=lambda row: row["score"], reverse=True)
        selected = matched_entities[:8]

        facts = []
        seen = set()
        frontier = [item["name"] for item in selected]
        for _ in range(max(1, min(hops, 2))):
            next_frontier = []
            for name in frontier:
                for rel in self.relations_by_entity.get(name, []):
                    key = (rel["head"], rel["relation"], rel["tail"])
                    if key in seen:
                        continue
                    seen.add(key)
                    score = score_text(q_terms, f"{rel['head']} {rel['relation_zh']} {rel['tail']} {rel.get('evidence','')}") + float(rel.get("confidence") or 0)
                    facts.append({**rel, "score": round(score, 4), "type": "graph"})
                    next_frontier.extend([rel["head"], rel["tail"]])
            frontier = next_frontier[:20]
        facts.sort(key=lambda row: row["score"], reverse=True)
        return selected, facts[:limit]

    def answer(self, question: str, top_k: int = 5, graph_hops: int = 1) -> dict[str, Any]:
        started = time.perf_counter()
        docs = self.retrieve_documents(question, top_k)
        entities, facts = self.retrieve_graph(question, graph_hops)
        answer = self.generate_answer(question, docs, facts)
        return {
            "question": question,
            "answer": answer,
            "linked_entities": entities[:8],
            "evidence": {"documents": docs, "graph": facts},
            "metadata": {
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "chapter": "第五章 船体分段的装配",
                "graph_entities": self.summary.get("entities"),
                "graph_relations": self.summary.get("relations"),
            },
        }

    def generate_answer(self, question: str, docs: list[dict[str, Any]], facts: list[dict[str, Any]]) -> str:
        graph_context = "\n".join(
            f"- {rel['head']} --{rel.get('relation_zh') or rel['relation']}--> {rel['tail']}；证据：{rel.get('evidence','')}；chunk={','.join(rel.get('source_chunks', []))}"
            for rel in facts[:10]
        )
        doc_context = "\n".join(
            f"- chunk={doc['id']}；位置={doc.get('page_start')}；{doc.get('text','')[:260]}"
            for doc in docs[:5]
        )
        if not graph_context and not doc_context:
            return "结论：根据第五章知识库暂时无法确定。\n依据：未检索到相关图谱事实或教材片段。\n引用：无。"
        prompt = f"""你是船体分段装配工艺课程的第五章知识问答助手。请只基于给定的知识图谱事实和教材片段回答问题，不使用外部知识。
要求：
1. 回答必须包含“结论：”“依据：”“引用：”三部分。
2. 不要使用 Markdown 加粗或星号。
3. 如果证据不足，只回答能由证据确认的部分。
4. 控制在 450 字以内。

问题：{question}

知识图谱事实：
{graph_context or "无"}

教材片段：
{doc_context or "无"}

/no_think
"""
        try:
            return clean_model_output(self.pangu.generate(prompt, max_new_tokens=700))
        except Exception:
            return fallback_answer(docs, facts)


def clean_model_output(text: str) -> str:
    text = (text or "").replace("**", "")
    text = re.sub(r"^\s*```.*?$|```\s*$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fallback_answer(docs: list[dict[str, Any]], facts: list[dict[str, Any]]) -> str:
    fact_lines = [f"{rel['head']}--{rel.get('relation_zh') or rel['relation']}-->{rel['tail']}" for rel in facts[:3]]
    doc_lines = [f"{doc['id']}：{doc.get('text','')[:120]}" for doc in docs[:2]]
    return (
        "结论：已检索到第五章中的相关证据，可据此进行回答。\n"
        f"依据：{'；'.join(fact_lines + doc_lines) or '无'}。\n"
        f"引用：{', '.join(doc['id'] for doc in docs[:3]) or '无'}。"
    )


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=10)
    graph_hops: int = Field(default=1, ge=1, le=2)


rag = Chapter5RAG()
app = FastAPI(title="Chapter 5 ShipRAG")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, Any]:
    pangu_status: Any
    try:
        pangu_status = rag.pangu.health()
    except Exception as exc:
        pangu_status = {"status": "error", "detail": repr(exc)}
    return {
        "status": "ok",
        "chapter": "第五章 船体分段的装配",
        "chunks": len(rag.chunks),
        "entities": len(rag.entities),
        "relations": len(rag.relations),
        "qdrant_enabled": rag.qdrant_enabled,
        "qdrant_collection": rag.qdrant.collection if rag.qdrant else None,
        "pangu": pangu_status,
    }


@app.post("/ask")
def ask(payload: AskRequest) -> dict[str, Any]:
    return rag.answer(payload.question, payload.top_k, payload.graph_hops)


@app.get("/graph/summary")
def graph_summary() -> dict[str, Any]:
    return rag.summary
