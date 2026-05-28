from __future__ import annotations

import math
import re

from graph_rag.db.qdrant_client import ShipQdrantClient
from graph_rag.ingest.chunk_loader import load_chunks
from graph_rag.llm import OpenAIService


class VectorRetriever:
    def __init__(self, qdrant: ShipQdrantClient, llm: OpenAIService) -> None:
        self.qdrant = qdrant
        self.llm = llm
        self.chunks = load_chunks()
        self.chunk_by_id = {item["id"]: item for item in self.chunks}
        self.chunks_by_page: dict[int, list[dict]] = {}
        for item in self.chunks:
            start = int(item.get("page_start") or 0)
            end = int(item.get("page_end") or start)
            for page in range(start, end + 1):
                self.chunks_by_page.setdefault(page, []).append(item)

    def retrieve(self, query: str, top_k: int = 8) -> list[dict]:
        candidate_k = max(50, top_k * 8)
        vector = self.llm.embed([query])[0]
        vector_results = self.qdrant.search(vector, top_k=candidate_k)
        keyword_results = self._keyword_search(query, top_k=candidate_k)
        page_hint_results = self._page_hint_search(query)
        if page_hint_results:
            fused = self._fuse(vector_results, keyword_results, page_hint_results)
            return self._take_unique([*page_hint_results, *fused], limit=min(top_k, 3))
        fused = self._fuse(vector_results, keyword_results, page_hint_results)
        primary = fused[:top_k]
        return self._expand_neighbor_pages(primary, max_total=top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        terms = extract_query_terms(query)
        if not terms:
            return []
        scored = []
        for chunk in self.chunks:
            score = keyword_score(query, terms, chunk)
            if score <= 0:
                continue
            scored.append(
                {
                    "type": "document",
                    "score": round(score, 4),
                    "retrieval_source": "keyword",
                    "chunk_id": chunk["id"],
                    "source": chunk.get("source"),
                    "page_start": chunk.get("page_start"),
                    "page_end": chunk.get("page_end"),
                    "chapter_hint": chunk.get("chapter_hint", ""),
                    "text": chunk.get("text", ""),
                    "char_count": chunk.get("char_count", len(chunk.get("text", ""))),
                }
            )
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]

    def _page_hint_search(self, query: str) -> list[dict]:
        pages = [int(match) for match in re.findall(r"第\s*(\d{1,3})\s*页", query)]
        results = []
        for page in pages[:3]:
            for chunk in self.chunks_by_page.get(page, []):
                results.append(
                    {
                        "type": "document",
                        "score": 1.0,
                        "retrieval_source": "page_hint",
                        "chunk_id": chunk["id"],
                        "source": chunk.get("source"),
                        "page_start": chunk.get("page_start"),
                        "page_end": chunk.get("page_end"),
                        "chapter_hint": chunk.get("chapter_hint", ""),
                        "text": chunk.get("text", ""),
                        "char_count": chunk.get("char_count", len(chunk.get("text", ""))),
                    }
                )
        return results

    def _fuse(self, vector_results: list[dict], keyword_results: list[dict], page_hint_results: list[dict]) -> list[dict]:
        merged: dict[str, dict] = {}
        rrf_k = 60
        for weight, results in ((2.5, page_hint_results), (1.0, vector_results), (1.35, keyword_results)):
            for rank, item in enumerate(results, start=1):
                chunk_id = item.get("chunk_id")
                if not chunk_id:
                    continue
                current = merged.setdefault(chunk_id, {**item, "score": 0.0, "sources": []})
                current["score"] += weight / (rrf_k + rank)
                current["sources"].append(item.get("retrieval_source") or "vector")
                if item.get("text") and len(item.get("text", "")) > len(current.get("text", "")):
                    current.update({key: value for key, value in item.items() if key != "score"})
        results = list(merged.values())
        for item in results:
            item["score"] = round(float(item["score"]), 6)
            item["retrieval_source"] = "+".join(sorted(set(item.get("sources", []))))
        return sorted(results, key=lambda item: item["score"], reverse=True)

    def _expand_neighbor_pages(self, documents: list[dict], max_total: int) -> list[dict]:
        expanded = []
        seen = set()
        for doc in documents:
            chunk_id = doc.get("chunk_id")
            if chunk_id and chunk_id not in seen:
                expanded.append(doc)
                seen.add(chunk_id)
            for page in neighbor_pages(doc):
                for chunk in self.chunks_by_page.get(page, [])[:1]:
                    if chunk["id"] in seen:
                        continue
                    expanded.append(
                        {
                            "type": "document",
                            "score": max(float(doc.get("score") or 0) * 0.92, 0.0001),
                            "retrieval_source": "page_neighbor",
                            "chunk_id": chunk["id"],
                            "source": chunk.get("source"),
                            "page_start": chunk.get("page_start"),
                            "page_end": chunk.get("page_end"),
                            "chapter_hint": chunk.get("chapter_hint", ""),
                            "text": chunk.get("text", ""),
                            "char_count": chunk.get("char_count", len(chunk.get("text", ""))),
                        }
                    )
                    seen.add(chunk["id"])
                    if len(expanded) >= max_total:
                        return expanded
            if len(expanded) >= max_total:
                return expanded
        return expanded

    def _take_unique(self, documents: list[dict], limit: int) -> list[dict]:
        selected = []
        seen = set()
        for doc in documents:
            chunk_id = doc.get("chunk_id")
            if not chunk_id or chunk_id in seen:
                continue
            selected.append(doc)
            seen.add(chunk_id)
            if len(selected) >= limit:
                break
        return selected


def extract_query_terms(query: str) -> list[str]:
    quoted = re.findall(r"[“\"']([^”\"']{2,20})[”\"']", query)
    candidates = quoted[:]
    candidates.extend(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,12}", query))
    terms = []
    for term in candidates:
        term = term.strip()
        if len(term) < 2 or term in {"教材", "内容", "主要", "说明", "什么", "哪些", "如何", "为什么"}:
            continue
        if term not in terms:
            terms.append(term)
    return terms[:18]


def keyword_score(query: str, terms: list[str], chunk: dict) -> float:
    text = f"{chunk.get('chapter_hint', '')} {chunk.get('text', '')}"
    score = 0.0
    for term in terms:
        count = text.count(term)
        if count:
            score += (8.0 + math.log1p(len(term))) * count
        elif len(term) >= 4:
            overlap = char_bigram_overlap(term, text)
            if overlap >= 0.5:
                score += overlap * len(term)
    if str(chunk.get("page_start") or "") and str(chunk.get("page_start")) in query:
        score += 5.0
    return score


def char_bigram_overlap(term: str, text: str) -> float:
    grams = {term[index : index + 2] for index in range(len(term) - 1)}
    if not grams:
        return 0.0
    hits = sum(1 for gram in grams if gram in text)
    return hits / len(grams)


def neighbor_pages(doc: dict) -> list[int]:
    start = doc.get("page_start")
    end = doc.get("page_end") or start
    if not isinstance(start, int) or not isinstance(end, int):
        return []
    pages = []
    if start > 1:
        pages.append(start - 1)
    pages.append(end + 1)
    return pages
