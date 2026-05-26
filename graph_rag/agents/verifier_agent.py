from __future__ import annotations


class VerifierAgent:
    def run(self, answer: str, evidence: dict) -> dict:
        graph_count = len(evidence.get("graph", []))
        doc_count = len(evidence.get("documents", []))
        supported = graph_count > 0 or doc_count > 0
        return {
            "answer": answer.replace("**", "").strip(),
            "verified": supported,
            "detail": f"graph_evidence={graph_count}, document_evidence={doc_count}",
        }
