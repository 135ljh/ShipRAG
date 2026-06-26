from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chapter5_rag.chapter5_vector import Chapter5Qdrant, hash_embed


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
DATA_DIR = BASE_DIR / "data"
WEB_DIR = BASE_DIR / "web"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def terms(text: str) -> list[str]:
    vocab = [
        "\u5206\u6bb5\u88c5\u914d",
        "\u88c5\u914d\u65b9\u5f0f",
        "\u6b63\u88c5",
        "\u5012\u88c5",
        "\u53cd\u88c5",
        "\u4fa7\u88c5",
        "\u5367\u88c5",
        "\u653e\u5c04\u5f0f",
        "\u63d2\u5165\u5f0f",
        "\u6846\u67b6\u5f0f",
        "\u6563\u88c5\u5f0f",
        "\u5b50\u5206\u6bb5",
        "\u80ce\u67b6",
        "\u710a\u63a5\u53d8\u5f62",
        "\u5b8c\u5de5\u6d4b\u91cf",
        "\u5206\u6bb5\u5b9a\u4f4d",
    ]
    result = [word for word in vocab if word in text]
    for item in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}", text):
        if item not in {"\u6559\u6750", "\u7b2c\u4e94\u7ae0", "\u4ec0\u4e48", "\u54ea\u4e9b", "\u5982\u4f55"} and item not in result:
            result.append(item)
    return result[:16]


def keyword_score(query_terms: list[str], text: str) -> float:
    clean = compact(text)
    score = 0.0
    for term in query_terms:
        count = clean.count(compact(term))
        if count:
            score += count * (3.0 + math.log1p(len(term)))
    return score


def clean_model_output(text: str) -> str:
    text = (text or "").replace("**", "")
    text = re.sub(r"^\s*```.*?$|```\s*$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class DeepSeekChatClient:
    def __init__(self) -> None:
        load_dotenv(ROOT / ".env")
        load_dotenv(BASE_DIR / ".env", override=False)
        self.api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("CHAPTER5_DEEPSEEK_API_KEY")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "180"))

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {"status": "missing_api_key", "provider": "deepseek", "model": self.model}
        return {"status": "configured", "provider": "deepseek", "model": self.model, "base_url": self.base_url}

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 720, temperature: float = 0.0) -> str:
        if not self.api_key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY.")
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class Chapter5VectorBaselineRAG:
    def __init__(self) -> None:
        self.chunks = read_jsonl(DATA_DIR / "chapter5_chunks.jsonl")
        self.deepseek = DeepSeekChatClient()
        self.qdrant: Chapter5Qdrant | None = None
        self.qdrant_enabled = False
        self.qdrant_error = ""
        try:
            self.qdrant = Chapter5Qdrant()
            self.qdrant.ensure_collection(recreate=False)
            self.qdrant_enabled = True
        except Exception as exc:
            self.qdrant_error = repr(exc)
            self.qdrant = None
        self.memory_vectors = [
            (chunk, hash_embed(f"{chunk.get('chapter_hint', '')}\n{chunk.get('text', '')}"))
            for chunk in self.chunks
        ]

    def trace_step(self, trace: list[dict[str, Any]], agent: str, action: str, detail: dict[str, Any], started: float) -> None:
        trace.append({"agent": agent, "action": action, "detail": detail, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)})

    def qdrant_search(self, question: str, top_k: int) -> list[dict[str, Any]]:
        if not self.qdrant_enabled or self.qdrant is None:
            return []
        return self.qdrant.search(question, top_k=max(top_k * 4, 12))

    def memory_vector_search(self, question: str, top_k: int) -> list[dict[str, Any]]:
        query_vector = hash_embed(question)
        rows = []
        for chunk, vector in self.memory_vectors:
            rows.append({
                **chunk,
                "chunk_id": chunk["id"],
                "score": round(cosine(query_vector, vector), 6),
                "type": "document",
                "retrieval_source": "memory_vector",
            })
        rows.sort(key=lambda item: item["score"], reverse=True)
        return rows[: max(top_k * 4, 12)]

    def retrieve_documents(self, question: str, top_k: int) -> list[dict[str, Any]]:
        vector_rows = self.qdrant_search(question, top_k) or self.memory_vector_search(question, top_k)
        query_terms = terms(question)
        merged: dict[str, dict[str, Any]] = {}
        for rank, row in enumerate(vector_rows, start=1):
            chunk_id = row.get("chunk_id") or row.get("id")
            if not chunk_id:
                continue
            text = row.get("text", "")
            score = float(row.get("score") or 0) + 0.015 * keyword_score(query_terms, f"{row.get('chapter_hint','')} {text}") + 1.0 / (80 + rank)
            merged[chunk_id] = {
                "id": chunk_id,
                "chunk_id": chunk_id,
                "source": row.get("source"),
                "page_start": row.get("page_start"),
                "page_end": row.get("page_end"),
                "chapter_hint": row.get("chapter_hint", ""),
                "text": text,
                "char_count": row.get("char_count", len(text)),
                "type": "document",
                "score": round(score, 6),
                "retrieval_source": row.get("retrieval_source", "qdrant_vector"),
            }
        docs = list(merged.values())
        docs.sort(key=lambda item: item["score"], reverse=True)
        return docs[:top_k]

    def generate_answer(self, question: str, docs: list[dict[str, Any]]) -> str:
        if not docs:
            return "\u7ed3\u8bba\uff1a\u7eaf\u5411\u91cf RAG \u57fa\u7ebf\u672a\u68c0\u7d22\u5230\u76f8\u5173\u6587\u672c\u5757\u3002\n\u4f9d\u636e\uff1a\u65e0\u53ef\u7528\u6587\u672c\u8bc1\u636e\u3002\n\u5f15\u7528\uff1a\u65e0\u3002"
        doc_context = "\n".join(
            f"- chunk={doc['id']}\uff1b\u4f4d\u7f6e {doc.get('page_start')}\uff1b{doc.get('text','')[:360]}"
            for doc in docs[:6]
        )
        if self.deepseek.enabled:
            try:
                return clean_model_output(
                    self.deepseek.chat(
                        [
                            {"role": "system", "content": "\u4f60\u662f\u8239\u4f53\u5206\u6bb5\u88c5\u914d\u5de5\u827a\u8bfe\u7a0b\u7684\u7b2c\u4e94\u7ae0\u95ee\u7b54\u52a9\u624b\u3002\u53ea\u57fa\u4e8e\u7ed9\u5b9a\u6559\u6750\u6587\u672c\u5757\u56de\u7b54\uff0c\u4e0d\u4f7f\u7528\u77e5\u8bc6\u56fe\u8c31\u3002"},
                            {
                                "role": "user",
                                "content": f"\u8981\u6c42\uff1a\u5305\u542b\u201c\u7ed3\u8bba\uff1a\u201d\u201c\u4f9d\u636e\uff1a\u201d\u201c\u5f15\u7528\uff1a\u201d\u4e09\u90e8\u5206\uff1b\u4e0d\u8981 Markdown \u52a0\u7c97\uff1b\u8bc1\u636e\u4e0d\u8db3\u65f6\u53ea\u56de\u7b54\u53ef\u786e\u8ba4\u5185\u5bb9\uff1b500\u5b57\u4ee5\u5185\u3002\n\n\u95ee\u9898\uff1a{question}\n\n\u6587\u672c\u5757\u8bc1\u636e\uff1a\n{doc_context}",
                            },
                        ],
                        max_tokens=760,
                    )
                )
            except Exception:
                pass
        return fallback_answer(docs)

    def answer(self, question: str, top_k: int = 5) -> dict[str, Any]:
        started = time.perf_counter()
        trace: list[dict[str, Any]] = []
        retrieve_started = time.perf_counter()
        docs = self.retrieve_documents(question, top_k)
        self.trace_step(
            trace,
            "VectorRetriever",
            "text chunk vector retrieval only",
            {"documents": len(docs), "sources": sorted({doc.get("retrieval_source", "") for doc in docs}), "top_chunks": [doc["id"] for doc in docs[:5]]},
            retrieve_started,
        )
        answer_started = time.perf_counter()
        answer = self.generate_answer(question, docs)
        self.trace_step(trace, "AnswerGenerator", "LLM answer generation from vector contexts", {"answer_chars": len(answer), "llm": self.deepseek.model}, answer_started)
        verify_started = time.perf_counter()
        verification = {
            "grounded": bool(docs),
            "has_required_sections": all(marker in answer for marker in ("\u7ed3\u8bba", "\u4f9d\u636e", "\u5f15\u7528")),
            "document_evidence": len(docs),
            "graph_evidence": 0,
        }
        self.trace_step(trace, "BaselineVerifier", "document evidence and format verification", verification, verify_started)
        return {
            "question": question,
            "answer": answer,
            "linked_entities": [],
            "evidence": {"documents": docs, "graph": []},
            "metadata": {
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "chapter": "\u7b2c\u4e94\u7ae0 \u8239\u4f53\u5206\u6bb5\u7684\u88c5\u914d",
                "retrieval_mode": "chapter5_vector_only_rag_baseline",
                "graph_entities": 0,
                "graph_relations": 0,
                "verification": verification,
                "agent_trace": trace,
            },
        }


def fallback_answer(docs: list[dict[str, Any]]) -> str:
    lines = [f"{doc['id']}\uff1a{doc.get('text','')[:130]}" for doc in docs[:3]]
    return (
        "\u7ed3\u8bba\uff1a\u5df2\u68c0\u7d22\u5230\u7b2c\u4e94\u7ae0\u76f8\u5173\u6587\u672c\u5757\uff0c\u53ef\u636e\u6b64\u7ed9\u51fa\u57fa\u7ebf\u56de\u7b54\u3002\n"
        f"\u4f9d\u636e\uff1a{'\uff1b'.join(lines) or '\u65e0'}\u3002\n"
        f"\u5f15\u7528\uff1a{', '.join(doc['id'] for doc in docs[:3]) or '\u65e0'}\u3002"
    )


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=10)
    graph_hops: int = Field(default=1, ge=1, le=2)


rag = Chapter5VectorBaselineRAG()
app = FastAPI(title="Chapter 5 Vector-only RAG Baseline")
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "chapter": "\u7b2c\u4e94\u7ae0 \u8239\u4f53\u5206\u6bb5\u7684\u88c5\u914d",
        "chunks": len(rag.chunks),
        "entities": 0,
        "relations": 0,
        "qdrant_enabled": rag.qdrant_enabled,
        "qdrant_collection": rag.qdrant.collection if rag.qdrant else None,
        "qdrant_error": rag.qdrant_error,
        "model": rag.deepseek.health(),
        "baseline": "vector_only_no_knowledge_graph",
    }


@app.post("/ask")
def ask(payload: AskRequest) -> dict[str, Any]:
    return rag.answer(payload.question, payload.top_k)


@app.get("/graph/summary")
def graph_summary() -> dict[str, Any]:
    return {"provider": "none", "baseline": "vector_only", "entities": 0, "relations": 0, "chunks": len(rag.chunks)}
