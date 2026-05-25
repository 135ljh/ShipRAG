from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2)
    top_k: int = 8
    graph_hops: int = 2


class GraphSearchRequest(BaseModel):
    entity: str
    hops: int = 2
    limit: int = 50


class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 8

