from __future__ import annotations


class ContextBuilder:
    def build_graph_context(self, facts: list[dict], limit: int = 18) -> str:
        lines = []
        for index, fact in enumerate(facts[:limit], start=1):
            relation = fact.get("relation_zh") or fact.get("relation") or fact.get("relation_type")
            lines.append(
                f"{index}. {fact.get('head')} --{relation}--> {fact.get('tail')} "
                f"(路径: {fact.get('path')}; 页码: {fact.get('source_pages')})"
            )
        return "\n".join(lines)

    def build_document_context(self, documents: list[dict], limit: int = 4) -> str:
        lines = []
        for index, doc in enumerate(documents[:limit], start=1):
            text = (doc.get("text") or "")[:360]
            lines.append(
                f"{index}. chunk={doc.get('chunk_id')} 页码={doc.get('page_start')} "
                f"score={doc.get('score'):.4f}\n{text}"
            )
        return "\n\n".join(lines)
