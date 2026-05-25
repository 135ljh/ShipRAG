from __future__ import annotations

import argparse
import json
import re
import statistics
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import fitz
import numpy as np
from rapidocr_onnxruntime import RapidOCR


PAGE_NO_RE = re.compile(r"^\s*[-—_]*\s*\d{1,3}\s*[-—_]*\s*$")
CHAPTER_RE = re.compile(r"^(第[一二三四五六七八九十]+章)\s*(.+)?$")
SECTION_RE = re.compile(r"^([一二三四五六七八九十]+、|\d+(?:\.\d+)*[.、])\s*(.+)$")


@dataclass
class PageRecord:
    page: int
    text: str
    lines: list[str]
    avg_confidence: float | None
    ocr_items: int


def find_source_pdf(root: Path, explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = root / path
        return path
    pdfs = sorted(root.glob("*.pdf"), key=lambda p: p.stat().st_size, reverse=True)
    if not pdfs:
        raise FileNotFoundError("No PDF file found in project root.")
    return pdfs[0]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "－": "-",
        "—": "-",
        "−": "-",
        "（": "(",
        "）": ")",
        "，": ",",
        "。": "。",
        "：": ":",
        "；": ";",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:!?，。；：！？])", r"\1", text)
    text = re.sub(r"([（(])\s+", r"\1", text)
    text = re.sub(r"\s+([）)])", r"\1", text)
    return text.strip()


def clean_lines(lines: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in lines:
        line = normalize_text(raw)
        if not line:
            continue
        if PAGE_NO_RE.match(line):
            continue
        if line in {"目录", "前言"}:
            cleaned.append(line)
            continue
        if len(line) == 1 and line in {"·", ".", "-", "_"}:
            continue
        cleaned.append(line)
    return cleaned


def join_lines(lines: list[str]) -> str:
    paragraphs: list[str] = []
    buf = ""
    for line in lines:
        is_heading = bool(CHAPTER_RE.match(line) or SECTION_RE.match(line)) or line in {"目录", "前言"}
        if is_heading:
            if buf:
                paragraphs.append(buf)
                buf = ""
            paragraphs.append(line)
            continue
        if not buf:
            buf = line
        elif re.search(r"[。！？;:：]$", buf):
            paragraphs.append(buf)
            buf = line
        else:
            buf += line
    if buf:
        paragraphs.append(buf)
    return "\n".join(paragraphs)


def page_to_image(page: fitz.Page, zoom: float) -> np.ndarray:
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)


def ocr_page(ocr: RapidOCR, page: fitz.Page, zoom: float) -> PageRecord:
    text = page.get_text("text").strip()
    if text:
        lines = clean_lines(text.splitlines())
        return PageRecord(page=page.number + 1, text=join_lines(lines), lines=lines, avg_confidence=None, ocr_items=0)

    result, _ = ocr(page_to_image(page, zoom))
    result = result or []
    lines = [item[1] for item in result if len(item) >= 3 and float(item[2]) >= 0.35]
    confidence = [float(item[2]) for item in result if len(item) >= 3]
    cleaned = clean_lines(lines)
    return PageRecord(
        page=page.number + 1,
        text=join_lines(cleaned),
        lines=cleaned,
        avg_confidence=round(statistics.mean(confidence), 4) if confidence else None,
        ocr_items=len(result),
    )


def split_chunks(pages: list[PageRecord], max_chars: int, overlap: int) -> list[dict]:
    chunks: list[dict] = []
    current_heading = ""

    for record in pages:
        page_text = record.text.strip()
        if not page_text:
            continue
        for line in record.lines:
            if CHAPTER_RE.match(line):
                current_heading = line
                break

        start = 0
        while start < len(page_text):
            end = min(len(page_text), start + max_chars)
            if end < len(page_text):
                boundary = max(page_text.rfind("。", start, end), page_text.rfind("\n", start, end))
                if boundary > start + max_chars * 0.55:
                    end = boundary + 1
            chunk_text = page_text[start:end].strip()
            if chunk_text:
                chunk_id = f"shiprag_p{record.page:03d}_{len(chunks) + 1:05d}"
                chunks.append(
                    {
                        "id": chunk_id,
                        "source": "中级船体装配工工艺学_11934890.pdf",
                        "page_start": record.page,
                        "page_end": record.page,
                        "chapter_hint": current_heading,
                        "text": chunk_text,
                        "char_count": len(chunk_text),
                    }
                )
            if end >= len(page_text):
                break
            start = max(end - overlap, start + 1)
    return chunks


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR and clean the ship assembly textbook PDF.")
    parser.add_argument("--pdf", default=None, help="PDF path. Defaults to the largest PDF in project root.")
    parser.add_argument("--out-dir", default="data/processed", help="Output directory.")
    parser.add_argument("--zoom", type=float, default=1.5, help="Render zoom for OCR pages.")
    parser.add_argument("--max-chars", type=int, default=900, help="Maximum characters per RAG chunk.")
    parser.add_argument("--overlap", type=int, default=120, help="Character overlap between chunks from the same page.")
    parser.add_argument("--finalize-only", action="store_true", help="Only build final outputs from existing page JSONL.")
    args = parser.parse_args()

    root = Path.cwd()
    pdf_path = find_source_pdf(root, args.pdf)
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    started = time.time()
    doc = fitz.open(str(pdf_path))
    ocr = RapidOCR()
    pages: list[PageRecord] = []
    pages_path = out_dir / "ship_textbook_pages.cleaned.jsonl"
    existing_rows: dict[int, dict] = {}
    if pages_path.exists():
        with pages_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                existing_rows[int(row["page"])] = row

    if args.finalize_only:
        print(f"Finalize only: using {len(existing_rows)} existing pages.", flush=True)
    else:
        with pages_path.open("a", encoding="utf-8") as page_file:
            for index, page in enumerate(doc, start=1):
                if index in existing_rows:
                    row = existing_rows[index]
                    pages.append(
                        PageRecord(
                            page=row["page"],
                            text=row["text"],
                            lines=row["lines"],
                            avg_confidence=row["avg_confidence"],
                            ocr_items=row["ocr_items"],
                        )
                    )
                    print(f"[{index:03d}/{doc.page_count}] skipped existing", flush=True)
                    continue

                record = ocr_page(ocr, page, args.zoom)
                pages.append(record)
                row = {
                    "source": pdf_path.name,
                    "page": record.page,
                    "text": record.text,
                    "lines": record.lines,
                    "char_count": len(record.text),
                    "avg_confidence": record.avg_confidence,
                    "ocr_items": record.ocr_items,
                }
                page_file.write(json.dumps(row, ensure_ascii=False) + "\n")
                page_file.flush()
                print(
                    f"[{index:03d}/{doc.page_count}] chars={len(record.text):04d} "
                    f"items={record.ocr_items:03d} conf={record.avg_confidence}",
                    flush=True,
                )

    page_rows = []
    with pages_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                page_rows.append(json.loads(line))
    page_rows = sorted({int(row["page"]): row for row in page_rows}.values(), key=lambda row: int(row["page"]))
    pages = [
        PageRecord(
            page=row["page"],
            text=row["text"],
            lines=row["lines"],
            avg_confidence=row["avg_confidence"],
            ocr_items=row["ocr_items"],
        )
        for row in page_rows
    ]
    pages_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in page_rows),
        encoding="utf-8",
    )

    page_rows = [
        {
            "source": pdf_path.name,
            "page": p.page,
            "text": p.text,
            "lines": p.lines,
            "char_count": len(p.text),
            "avg_confidence": p.avg_confidence,
            "ocr_items": p.ocr_items,
        }
        for p in pages
    ]
    chunks = split_chunks(pages, args.max_chars, args.overlap)

    write_jsonl(out_dir / "ship_textbook_pages.cleaned.jsonl", page_rows)
    write_jsonl(out_dir / "ship_textbook_chunks.jsonl", chunks)

    markdown_lines = [f"# {pdf_path.stem}", ""]
    for p in pages:
        if not p.text.strip():
            continue
        markdown_lines.extend([f"## Page {p.page}", "", p.text.strip(), ""])
    (out_dir / "ship_textbook.cleaned.md").write_text("\n".join(markdown_lines), encoding="utf-8")

    metadata = {
        "source_pdf": pdf_path.name,
        "page_count": doc.page_count,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "toolchain": {
            "pdf": "PyMuPDF",
            "ocr": "rapidocr_onnxruntime",
            "render_zoom": args.zoom,
        },
        "outputs": {
            "pages_jsonl": "ship_textbook_pages.cleaned.jsonl",
            "chunks_jsonl": "ship_textbook_chunks.jsonl",
            "markdown": "ship_textbook.cleaned.md",
        },
        "statistics": {
            "pages_with_text": sum(1 for p in pages if p.text.strip()),
            "total_clean_chars": sum(len(p.text) for p in pages),
            "chunks": len(chunks),
            "avg_page_confidence": round(
                statistics.mean([p.avg_confidence for p in pages if p.avg_confidence is not None]), 4
            ),
            "elapsed_seconds": round(time.time() - started, 2),
        },
    }
    (out_dir / "preprocess_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
