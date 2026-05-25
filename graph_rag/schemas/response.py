from __future__ import annotations

from pydantic import BaseModel


class AskResponse(BaseModel):
    question: str
    answer: str
    linked_entities: list[dict]
    evidence: dict
    metadata: dict

