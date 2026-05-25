from __future__ import annotations

from graph_rag.rag.entity_linker import EntityLinker
from graph_rag.retrievers.graph_retriever import GraphRetriever
from graph_rag.retrievers.vector_retriever import VectorRetriever


class HybridRetriever:
    def __init__(
        self,
        entity_linker: EntityLinker,
        graph_retriever: GraphRetriever,
        vector_retriever: VectorRetriever,
    ) -> None:
        self.entity_linker = entity_linker
        self.graph_retriever = graph_retriever
        self.vector_retriever = vector_retriever

    def retrieve(self, question: str, top_k: int = 8, graph_hops: int = 2) -> dict:
        entities = self.entity_linker.link(question)
        graph_facts = self.graph_retriever.retrieve(entities, hops=graph_hops)
        entity_terms = " ".join(item["name"] for item in entities)
        graph_terms = " ".join(f"{item['head']} {item['tail']}" for item in graph_facts[:10])
        vector_query = f"{question} {entity_terms} {graph_terms}".strip()
        documents = self.vector_retriever.retrieve(vector_query or question, top_k=top_k)
        return {
            "linked_entities": entities,
            "graph": graph_facts[:80],
            "documents": documents,
        }

