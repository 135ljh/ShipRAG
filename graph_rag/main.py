from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from graph_rag.agents.answer_agent import AnswerAgent
from graph_rag.agents.document_agent import DocumentAgent
from graph_rag.agents.entity_agent import EntityAgent
from graph_rag.agents.graph_agent import GraphAgent
from graph_rag.agents.orchestrator import MultiAgentOrchestrator
from graph_rag.agents.synthesis_agent import SynthesisAgent
from graph_rag.agents.verifier_agent import VerifierAgent
from graph_rag.db.neo4j_client import Neo4jClient
from graph_rag.db.qdrant_client import ShipQdrantClient
from graph_rag.llm import OpenAIService
from graph_rag.rag.answer_generator import AnswerGenerator
from graph_rag.rag.book_profile import BookProfileQA
from graph_rag.rag.context_builder import ContextBuilder
from graph_rag.rag.domain_qa import DomainQA
from graph_rag.rag.entity_linker import EntityLinker
from graph_rag.retrievers.graph_retriever import GraphRetriever
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
    generator = AnswerGenerator(llm, ContextBuilder())
    book_profile = BookProfileQA()
    domain_qa = DomainQA()
    orchestrator = MultiAgentOrchestrator(
        book_profile=book_profile,
        domain_qa=domain_qa,
        entity_agent=EntityAgent(linker),
        graph_agent=GraphAgent(graph),
        document_agent=DocumentAgent(vector),
        synthesis_agent=SynthesisAgent(),
        answer_agent=AnswerAgent(generator),
        verifier_agent=VerifierAgent(),
    )
    return {
        "neo4j": neo4j,
        "vector": vector,
        "orchestrator": orchestrator,
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
    payload = app.state.services["orchestrator"].answer(request.question, request.top_k, request.graph_hops)
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
