from __future__ import annotations


class RouterAgent:
    def route(self, question: str) -> str:
        text = "".join(question.split())
        if any(term in text for term in ("多少章", "几章", "目录", "讲什么", "主要内容", "作者", "出版社")):
            return "book_profile"
        if any(
            term in text
            for term in (
                "肋骨框架",
                "船台装配",
                "总装配",
                "测量工具",
                "结构编码",
                "分段装配前",
            )
        ):
            return "domain_qa"
        return "graph_rag"
