from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BookProfile:
    title: str
    author: str
    publisher: str
    edition: str
    page_count: int
    chunk_count: int
    chapters: tuple[str, ...]
    summary: str


BOOK_PROFILE = BookProfile(
    title="中级船体装配工工艺学",
    author="金仲达",
    publisher="哈尔滨工程大学出版社",
    edition="2007年4月第1版，2007年4月第1次印刷",
    page_count=192,
    chunk_count=230,
    chapters=(
        "第一章 工艺基础及相关工种知识",
        "第二章 船体放样",
        "第三章 几何体及船体结构展开",
        "第四章 较复杂部件的装配",
        "第五章 船体分段的装配",
        "第六章 船体总装配",
        "第七章 船体修理",
    ),
    summary=(
        "本书是初、中、高级船体装配工工艺学配套教材中的中级本，主要面向船厂中级船体装配工培训、"
        "自学以及技工学校船体装配专业教学。内容围绕船体装配工艺展开，覆盖工艺基础、船体放样、"
        "几何体与船体结构展开、复杂部件装配、分段装配、总装配和船体修理等知识。"
    ),
)


class BookProfileQA:
    def answer(self, question: str) -> dict | None:
        compact = "".join(question.split())
        if not compact:
            return None

        if self._is_chapter_count_question(compact):
            return self._response(
                question,
                (
                    f"结论：这本书全书共分 {len(BOOK_PROFILE.chapters)} 章。\n\n"
                    "依据：教材内容简介明确写到“全书共分七章”，目录页也列出了第一章到第七章。\n\n"
                    "引用：\n"
                    "- 第4页内容简介：全书共分七章。\n"
                    "- 第6-7页目录：列出七章标题。"
                ),
                intent="book_chapter_count",
            )

        if self._is_outline_question(compact):
            chapter_lines = "\n".join(f"{idx}. {chapter}" for idx, chapter in enumerate(BOOK_PROFILE.chapters, start=1))
            return self._response(
                question,
                (
                    f"结论：这本书共 {len(BOOK_PROFILE.chapters)} 章，目录如下：\n\n"
                    f"{chapter_lines}\n\n"
                    "依据：第6-7页目录列出了各章名称。"
                ),
                intent="book_outline",
            )

        if self._is_summary_question(compact):
            return self._response(
                question,
                (
                    f"结论：{BOOK_PROFILE.summary}\n\n"
                    "依据：第4页内容简介说明本书为中级船体装配工工艺学配套教材中的中级本，并概述了七章内容；"
                    "第5页编者的话说明本书主要供船厂中级船体装配工培训和自学使用。\n\n"
                    "引用：\n"
                    "- 第4页内容简介：全书内容依次包括工艺基础及相关工种知识、船体放样、船体结构展开、"
                    "复杂部件装配、分段装配、总装配和船体修理。\n"
                    "- 第5页编者的话：主要供船厂中级船体装配工培训和自学使用。"
                ),
                intent="book_summary",
            )

        if self._is_bibliography_question(compact):
            return self._response(
                question,
                (
                    "结论：本书书名为《中级船体装配工工艺学》，作者金仲达，出版社为哈尔滨工程大学出版社，"
                    f"{BOOK_PROFILE.edition}。\n\n"
                    "依据：封面、版权页和图书在版编目数据给出了书名、作者、出版社和出版信息。"
                ),
                intent="book_bibliography",
            )

        return None

    def _response(self, question: str, answer: str, intent: str) -> dict:
        return {
            "question": question,
            "answer": answer,
            "linked_entities": [
                {
                    "id": "book:middle_ship_assembly_technology",
                    "name": BOOK_PROFILE.title,
                    "type": "教材",
                    "definition": BOOK_PROFILE.summary,
                }
            ],
            "evidence": {
                "graph": [],
                "documents": [
                    {
                        "type": "document",
                        "chunk_id": "shiprag_p004_00004",
                        "page_start": 4,
                        "page_end": 4,
                        "score": 1.0,
                        "text": "内容简介：本书是初、中、高级船体装配工工艺学配套教材中的中级本。全书共分七章。",
                    },
                    {
                        "type": "document",
                        "chunk_id": "shiprag_p006_00006",
                        "page_start": 6,
                        "page_end": 7,
                        "score": 1.0,
                        "text": "目录页列出了第一章至第七章，包括工艺基础、船体放样、结构展开、部件装配、分段装配、总装配和船体修理。",
                    },
                ],
            },
            "metadata": {
                "retrieval_mode": "book_profile",
                "intent": intent,
            },
        }

    def _is_chapter_count_question(self, text: str) -> bool:
        return any(term in text for term in ("多少章", "几章", "多少章节", "几个章节"))

    def _is_outline_question(self, text: str) -> bool:
        return any(term in text for term in ("目录", "章节", "大纲", "有哪些章", "哪几章"))

    def _is_summary_question(self, text: str) -> bool:
        return any(term in text for term in ("讲什么", "讲的是什么", "主要内容", "内容是什么", "介绍什么", "这本书是关于什么"))

    def _is_bibliography_question(self, text: str) -> bool:
        return any(term in text for term in ("作者", "出版社", "出版", "书名", "谁写的"))
