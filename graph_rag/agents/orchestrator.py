from __future__ import annotations

from copy import deepcopy
from time import perf_counter

from graph_rag.agents.answer_agent import AnswerAgent
from graph_rag.agents.base import TraceRecorder
from graph_rag.agents.document_agent import DocumentAgent
from graph_rag.agents.entity_agent import EntityAgent
from graph_rag.agents.graph_agent import GraphAgent
from graph_rag.agents.router_agent import RouterAgent
from graph_rag.agents.synthesis_agent import SynthesisAgent
from graph_rag.agents.verifier_agent import VerifierAgent
from graph_rag.rag.book_profile import BookProfileQA
from graph_rag.rag.domain_qa import DomainQA


class MultiAgentOrchestrator:
    def __init__(
        self,
        book_profile: BookProfileQA,
        domain_qa: DomainQA,
        entity_agent: EntityAgent,
        graph_agent: GraphAgent,
        document_agent: DocumentAgent,
        synthesis_agent: SynthesisAgent,
        answer_agent: AnswerAgent,
        verifier_agent: VerifierAgent,
    ) -> None:
        self.router = RouterAgent()
        self.book_profile = book_profile
        self.domain_qa = domain_qa
        self.entity_agent = entity_agent
        self.graph_agent = graph_agent
        self.document_agent = document_agent
        self.synthesis_agent = synthesis_agent
        self.answer_agent = answer_agent
        self.verifier_agent = verifier_agent
        self.cache: dict[tuple[str, int, int], dict] = {}

    def answer(self, question: str, top_k: int, graph_hops: int) -> dict:
        start = perf_counter()
        trace = TraceRecorder()
        cache_key = (question.strip(), top_k, graph_hops)
        cached = self.cache.get(cache_key)
        if cached:
            payload = deepcopy(cached)
            original_trace = payload["metadata"].get("agent_trace", [])
            payload["metadata"]["cache_hit"] = True
            payload["metadata"]["elapsed_ms"] = self._elapsed(start)
            payload["metadata"]["agent_trace"] = [
                {
                    "agent": "CacheAgent",
                    "role": "缓存命中",
                    "status": "success",
                    "detail": "return cached answer",
                    "elapsed_ms": payload["metadata"]["elapsed_ms"],
                }
            ] + original_trace
            return payload

        route = trace.run("RouterAgent", "问题路由", "判断问题类型", lambda: self.router.route(question))
        if route == "book_profile":
            payload = trace.run(
                "BookProfileAgent",
                "书籍元信息问答",
                "使用教材简介和目录回答",
                lambda: self.book_profile.answer(question),
            )
            return self._finalize_curated(payload, trace, start, cache_key)

        if route == "domain_qa":
            payload = trace.run(
                "DomainQAAgent",
                "核心工艺问答",
                "使用教材核心工艺证据回答",
                lambda: self.domain_qa.answer(question),
            )
            if payload:
                return self._finalize_curated(payload, trace, start, cache_key)

        entities = trace.run("EntityAgent", "实体识别与链接", "从问题中链接 Neo4j 实体", lambda: self.entity_agent.run(question))
        graph_facts = trace.run(
            "GraphAgent",
            "知识图谱检索",
            f"entities={len(entities)}, hops={graph_hops}",
            lambda: self.graph_agent.run(entities, graph_hops),
        )
        documents = trace.run(
            "DocumentAgent",
            "教材文档检索",
            f"top_k={top_k}",
            lambda: self.document_agent.run(question, entities, graph_facts, top_k),
        )
        evidence = trace.run(
            "SynthesisAgent",
            "证据融合",
            f"graph={len(graph_facts)}, documents={len(documents)}",
            lambda: self.synthesis_agent.run(entities, graph_facts, documents),
        )
        draft = trace.run(
            "AnswerAgent",
            "答案生成",
            "调用云雾 OpenAI 兼容模型",
            lambda: self.answer_agent.run(question, evidence),
        )
        verified = trace.run(
            "VerifierAgent",
            "答案校验",
            "检查答案是否有证据支撑",
            lambda: self.verifier_agent.run(draft, evidence),
        )
        payload = {
            "question": question,
            "answer": verified["answer"],
            "linked_entities": evidence["linked_entities"],
            "evidence": {"graph": evidence["graph"], "documents": evidence["documents"]},
            "metadata": {
                "retrieval_mode": "multi_agent_graph_rag",
                "cache_hit": False,
                "verified": verified["verified"],
                "verify_detail": verified["detail"],
                "elapsed_ms": self._elapsed(start),
                "agent_trace": trace.as_list(),
            },
        }
        self._cache(cache_key, payload)
        return payload

    def _finalize_curated(self, payload: dict | None, trace: TraceRecorder, start: float, cache_key: tuple[str, int, int]) -> dict:
        if payload is None:
            payload = {
                "question": cache_key[0],
                "answer": "结论：根据当前知识库无法确定。\n\n依据：未匹配到可用的书籍档案或核心工艺问答规则。\n\n引用：无。",
                "linked_entities": [],
                "evidence": {"graph": [], "documents": []},
                "metadata": {"retrieval_mode": "multi_agent_no_match"},
            }
        verified = trace.run(
            "VerifierAgent",
            "答案校验",
            "检查固定答案是否有证据支撑",
            lambda: self.verifier_agent.run(payload["answer"], payload["evidence"]),
        )
        payload["answer"] = verified["answer"]
        payload["metadata"]["retrieval_mode"] = f"multi_agent_{payload['metadata'].get('retrieval_mode', 'curated')}"
        payload["metadata"]["cache_hit"] = False
        payload["metadata"]["verified"] = verified["verified"]
        payload["metadata"]["verify_detail"] = verified["detail"]
        payload["metadata"]["elapsed_ms"] = self._elapsed(start)
        payload["metadata"]["agent_trace"] = trace.as_list()
        self._cache(cache_key, payload)
        return payload

    def _cache(self, key: tuple[str, int, int], payload: dict) -> None:
        if len(self.cache) >= 128:
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = deepcopy(payload)

    def _elapsed(self, start: float) -> float:
        return round((perf_counter() - start) * 1000, 2)
