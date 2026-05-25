from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from graph_rag.db.neo4j_client import Neo4jClient
from graph_rag.db.qdrant_client import ShipQdrantClient
from graph_rag.llm import OpenAIService
from graph_rag.rag.answer_generator import AnswerGenerator
from graph_rag.rag.context_builder import ContextBuilder
from graph_rag.rag.entity_linker import EntityLinker
from graph_rag.retrievers.graph_retriever import GraphRetriever
from graph_rag.retrievers.hybrid_retriever import HybridRetriever
from graph_rag.retrievers.vector_retriever import VectorRetriever
from graph_rag.schemas.request import AskRequest, GraphSearchRequest, VectorSearchRequest
from graph_rag.schemas.response import AskResponse


app = FastAPI(title="ShipRAG Graph RAG API")
app.mount("/static", StaticFiles(directory="graph_rag/web"), name="static")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse("graph_rag/web/index.html")


def build_services():
    neo4j = Neo4jClient()
    qdrant = ShipQdrantClient()
    llm = OpenAIService()
    linker = EntityLinker(neo4j)
    graph = GraphRetriever(neo4j)
    vector = VectorRetriever(qdrant, llm)
    hybrid = HybridRetriever(linker, graph, vector)
    generator = AnswerGenerator(llm, ContextBuilder())
    return neo4j, hybrid, generator, vector


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    neo4j, hybrid, generator, _ = build_services()
    try:
        evidence = hybrid.retrieve(request.question, top_k=request.top_k, graph_hops=request.graph_hops)
        answer = generator.generate(request.question, evidence)
        return AskResponse(
            question=request.question,
            answer=answer,
            linked_entities=evidence["linked_entities"],
            evidence={"graph": evidence["graph"], "documents": evidence["documents"]},
            metadata={"retrieval_mode": "graph_vector_hybrid"},
        )
    finally:
        neo4j.close()


@app.post("/graph/search")
def graph_search(request: GraphSearchRequest) -> dict:
    neo4j = Neo4jClient()
    try:
        entities = neo4j.keyword_entities(request.entity, limit=10)
        if not entities:
            entities = neo4j.fuzzy_entities(request.entity, limit=10)
        facts = neo4j.neighborhood([item["id"] for item in entities], hops=request.hops, limit=request.limit)
        return {"entities": entities, "facts": facts}
    finally:
        neo4j.close()


@app.post("/vector/search")
def vector_search(request: VectorSearchRequest) -> dict:
    qdrant = ShipQdrantClient()
    llm = OpenAIService()
    retriever = VectorRetriever(qdrant, llm)
    return {"documents": retriever.retrieve(request.query, top_k=request.top_k)}
