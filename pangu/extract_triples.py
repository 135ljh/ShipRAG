from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests
import json5
from dotenv import load_dotenv
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[1]
PANGU_DIR = ROOT / "pangu"
DEFAULT_CHUNKS = ROOT / "data" / "processed" / "ship_textbook_chunks.jsonl"
DEFAULT_OUT = PANGU_DIR / "outputs" / "raw_extractions.jsonl"
PROMPT_PATH = PANGU_DIR / "prompts" / "kg_extraction_prompt.md"


def load_chunks(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if not row.get("error"):
                done.add(row["source_chunk"])
    return done


def extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    text = text.replace("[unused16]", "").replace("[unused17]", "").replace("[unused10]", "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return json5.loads(text)
        except Exception:
            pass
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
            repaired = repaired.replace("\n  }\n  {", "\n  },\n  {")
            repaired = repaired.replace("\n    }\n    {", "\n    },\n    {")
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                return json5.loads(repaired)


def build_prompt(template: str, chunk: dict[str, Any], max_chars: int) -> str:
    text = chunk["text"]
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "\n[文本已截断，请只抽取以上片段中的高置信知识。]"
    return f"""{template}

现在请抽取下面教材片段。

source_chunk: {chunk["id"]}
source_page: {chunk["page_start"]}
chapter_hint: {chunk.get("chapter_hint", "")}

text:
{text}

请只返回合法 JSON。/no_think
"""


class PanguClient:
    def __init__(self) -> None:
        load_dotenv(PANGU_DIR / ".env")
        self.base_url = os.getenv("PANGU_BASE_URL", "http://10.21.77.7:8000").rstrip("/")
        self.generate_path = os.getenv("PANGU_GENERATE_PATH", "/generate")
        self.health_path = os.getenv("PANGU_HEALTH_PATH", "/health")
        self.timeout = int(os.getenv("PANGU_TIMEOUT", "240"))

    def health(self) -> str:
        response = requests.get(f"{self.base_url}{self.health_path}", timeout=20)
        response.raise_for_status()
        return response.text

    def generate(self, prompt: str, max_new_tokens: int = 900, temperature: float = 0.0) -> str:
        payload = {
            "prompt": prompt,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
        }
        response = requests.post(f"{self.base_url}{self.generate_path}", json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("content") or data.get("text") or data.get("response") or json.dumps(data, ensure_ascii=False)


def should_skip_front_matter(chunk: dict[str, Any]) -> bool:
    text = chunk.get("text", "")
    page = int(chunk.get("page_start", 0))
    if page <= 4:
        return True
    if page in {6, 7}:
        return True
    bad_terms = ["ISBN", "定价", "出版社", "责任编辑", "CIP", "出版发行"]
    return page <= 7 and any(term in text for term in bad_terms)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract KG triples from processed textbook chunks via remote Pangu.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None, help="Only process first N chunks for testing.")
    parser.add_argument("--all", action="store_true", help="Process all chunks, excluding obvious publishing front matter.")
    parser.add_argument("--include-front-matter", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-input-chars", type=int, default=650)
    parser.add_argument("--max-new-tokens", type=int, default=900)
    args = parser.parse_args()

    chunks = load_chunks(args.chunks)
    if not args.include_front_matter:
        chunks = [chunk for chunk in chunks if not should_skip_front_matter(chunk)]
    if args.limit:
        chunks = chunks[: args.limit]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(args.out)
    template = PROMPT_PATH.read_text(encoding="utf-8")
    client = PanguClient()

    print(f"Pangu service: {client.base_url}")
    try:
        print(f"Health: {client.health()[:200]}")
    except Exception as exc:
        print(f"Warning: health check failed: {exc!r}")

    with args.out.open("a", encoding="utf-8") as f:
        for chunk in tqdm(chunks, desc="Pangu extracting"):
            if chunk["id"] in done:
                continue
            prompt = build_prompt(template, chunk, args.max_input_chars)
            last_error = None
            raw = ""
            for attempt in range(1, args.retries + 1):
                try:
                    raw = client.generate(prompt, max_new_tokens=args.max_new_tokens)
                    parsed = extract_json(raw)
                    row = {
                        "source_chunk": chunk["id"],
                        "source_page": chunk["page_start"],
                        "chapter_hint": chunk.get("chapter_hint", ""),
                        "text": chunk["text"],
                        "raw_response": raw,
                        "entities": parsed.get("entities", []),
                        "triples": parsed.get("triples", []),
                    }
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
                    break
                except Exception as exc:
                    last_error = exc
                    time.sleep(2 * attempt)
            else:
                err_row = {
                    "source_chunk": chunk["id"],
                    "source_page": chunk["page_start"],
                    "chapter_hint": chunk.get("chapter_hint", ""),
                    "text": chunk["text"],
                    "error": repr(last_error),
                    "raw_response": raw,
                    "entities": [],
                    "triples": [],
                }
                f.write(json.dumps(err_row, ensure_ascii=False) + "\n")
                f.flush()
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
