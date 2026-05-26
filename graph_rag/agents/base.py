from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable


@dataclass
class AgentStep:
    agent: str
    role: str
    status: str
    detail: str
    elapsed_ms: float

    def as_dict(self) -> dict:
        return {
            "agent": self.agent,
            "role": self.role,
            "status": self.status,
            "detail": self.detail,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


class TraceRecorder:
    def __init__(self) -> None:
        self.steps: list[AgentStep] = []

    def run(self, agent: str, role: str, detail: str, fn: Callable[[], Any]) -> Any:
        start = perf_counter()
        try:
            result = fn()
        except Exception:
            self.steps.append(
                AgentStep(
                    agent=agent,
                    role=role,
                    status="error",
                    detail=detail,
                    elapsed_ms=(perf_counter() - start) * 1000,
                )
            )
            raise
        self.steps.append(
            AgentStep(
                agent=agent,
                role=role,
                status="success",
                detail=detail,
                elapsed_ms=(perf_counter() - start) * 1000,
            )
        )
        return result

    def as_list(self) -> list[dict]:
        return [step.as_dict() for step in self.steps]
