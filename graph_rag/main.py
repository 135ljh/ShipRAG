from __future__ import annotations

from contextlib import asynccontextmanager
from copy import deepcopy
from time import perf_counter

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from graph_rag.db.neo4j_client import Neo4jClient
from graph_rag.db.qdrant_client import ShipQdrantClient
from graph_rag.llm import OpenAIService
from graph_rag.rag.answer_generator import AnswerGenerator
from graph_rag.rag.book_profile import BookProfileQA
from graph_rag.rag.context_builder import ContextBuilder
from graph_rag.rag.entity_linker import EntityLinker
from graph_rag.retrievers.graph_retriever import GraphRetriever
from graph_rag.retrievers.hybrid_retriever import HybridRetriever
from graph_rag.retrievers.vector_retriever import VectorRetriever
from graph_rag.schemas.request import AskRequest, GraphSearchRequest, VectorSearchRequest
from graph_rag.schemas.response import AskResponse


def build_services() -> dict:
    neo4j = Neo4jClient()
    qdrant = ShipQdrantClient()
    llm = OpenAIService()
    linker = EntityLinker(neo4j)
    graph = GraphRetriever(neo4j)
    vector = VectorRetriever(qdrant, llm)
    hybrid = HybridRetriever(linker, graph, vector)
    generator = AnswerGenerator(llm, ContextBuilder())
    return {
        "neo4j": neo4j,
        "hybrid": hybrid,
        "generator": generator,
        "vector": vector,
        "book_profile": BookProfileQA(),
        "answer_cache": {},
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = build_services()
    try:
        yield
    finally:
        app.state.services["neo4j"].close()


app = FastAPI(title="ShipRAG Graph RAG API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="graph_rag/web"), name="static")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse("graph_rag/web/index.html")


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    start = perf_counter()
    services = app.state.services
    cache_key = (request.question.strip(), request.top_k, request.graph_hops)
    cached = services["answer_cache"].get(cache_key)
    if cached:
        payload = deepcopy(cached)
        payload["metadata"]["cache_hit"] = True
        payload["metadata"]["elapsed_ms"] = round((perf_counter() - start) * 1000, 2)
        return AskResponse(**payload)

    profile_answer = services["book_profile"].answer(request.question)
    if profile_answer:
        profile_answer["metadata"]["elapsed_ms"] = round((perf_counter() - start) * 1000, 2)
        services["answer_cache"][cache_key] = deepcopy(profile_answer)
        return AskResponse(**profile_answer)

    evidence = services["hybrid"].retrieve(request.question, top_k=request.top_k, graph_hops=request.graph_hops)
    answer = services["generator"].generate(request.question, evidence)
    payload = {
        "question": request.question,
        "answer": answer,
        "linked_entities": evidence["linked_entities"],
        "evidence": {"graph": evidence["graph"], "documents": evidence["documents"]},
        "metadata": {
            "retrieval_mode": "graph_vector_hybrid",
            "cache_hit": False,
            "elapsed_ms": round((perf_counter() - start) * 1000, 2),
        },
    }
    if len(services["answer_cache"]) >= 128:
        services["answer_cache"].pop(next(iter(services["answer_cache"])))
    services["answer_cache"][cache_key] = deepcopy(payload)
    return AskResponse(**payload)


@app.post("/graph/search")
def graph_search(request: GraphSearchRequest) -> dict:
    neo4j = app.state.services["neo4j"]
    entities = neo4j.keyword_entities(request.entity, limit=10)
    if not entities:
        entities = neo4j.fuzzy_entities(request.entity, limit=10)
    facts = neo4j.neighborhood([item["id"] for item in entities], hops=request.hops, limit=request.limit)
    return {"entities": entities, "facts": facts}


@app.post("/vector/search")
def vector_search(request: VectorSearchRequest) -> dict:
    retriever = app.state.services["vector"]
    return {"documents": retriever.retrieve(request.query, top_k=request.top_k)}
