from __future__ import annotations


class SynthesisAgent:
    def run(self, entities: list[dict], graph_facts: list[dict], documents: list[dict]) -> dict:
        return {
            "linked_entities": entities,
            "graph": graph_facts[:40],
            "documents": documents,
        }
