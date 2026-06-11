from __future__ import annotations

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import json5
import requests
from dotenv import load_dotenv
from tqdm import tqdm


ROOT = Path(__file__).resolve().parents[1]
DEEPSEEK_DIR = ROOT / "deepseek"
DEFAULT_CHUNKS = ROOT / "data" / "processed" / "ship_textbook_chunks.jsonl"
DEFAULT_OUT = DEEPSEEK_DIR / "outputs" / "raw_extractions.jsonl"
PROMPT_PATH = DEEPSEEK_DIR / "prompts" / "kg_extraction_prompt.md"


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
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            return json5.loads(text)
        except Exception:
            pass
        candidates = re.findall(r"\{.*?\}", text, flags=re.S)
        candidates.extend(re.findall(r"\{.*\}", text, flags=re.S))
        candidates = [item for item in candidates if "entities" in item and "triples" in item]
        for candidate in sorted(candidates, key=len, reverse=True):
            repaired = re.sub(r",\s*([}\]])", r"\1", candidate)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                try:
                    return json5.loads(repaired)
                except Exception:
                    continue
        raise


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

只返回 JSON。第一个字符必须是 {{，不要输出任何分析文字。
"""


class DeepSeekClient:
    def __init__(self) -> None:
        load_dotenv(DEEPSEEK_DIR / ".env")
        load_dotenv(ROOT / ".env")
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured. Put it in deepseek/.env or environment.")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
        self.timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "240"))

    def generate(self, prompt: str, max_tokens: int = 1800) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是严谨的中文知识图谱抽取专家。只输出一个 JSON 对象，第一个字符必须是 {，禁止解释和分析。"},
                {"role": "user", "content": prompt},
            ],
            "thinking": {"type": "disabled"},
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0].get("message", {})
        content = message.get("content") or ""
        if not content.strip():
            raise RuntimeError(f"DeepSeek returned empty content: {json.dumps(data, ensure_ascii=False)[:500]}")
        return content


def should_skip_front_matter(chunk: dict[str, Any]) -> bool:
    text = chunk.get("text", "")
    page = int(chunk.get("page_start", 0))
    if page <= 4 or page in {6, 7}:
        return True
    bad_terms = ["ISBN", "定价", "出版社", "责任编辑", "CIP", "出版发行"]
    return page <= 7 and any(term in text for term in bad_terms)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract KG triples from processed textbook chunks via DeepSeek.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--all", action="store_true", help="Process all chunks, excluding obvious publishing front matter.")
    parser.add_argument("--include-front-matter", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-input-chars", type=int, default=650)
    parser.add_argument("--max-tokens", type=int, default=1800)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    chunks = load_chunks(args.chunks)
    if not args.include_front_matter:
        chunks = [chunk for chunk in chunks if not should_skip_front_matter(chunk)]
    if args.limit:
        chunks = chunks[: args.limit]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(args.out)
    template = PROMPT_PATH.read_text(encoding="utf-8")
    client = DeepSeekClient()
    print(f"DeepSeek model: {client.model}")

    def extract_one(chunk: dict[str, Any]) -> dict[str, Any]:
        prompt = build_prompt(template, chunk, args.max_input_chars)
        raw = ""
        last_error = None
        for attempt in range(1, args.retries + 1):
            try:
                raw = client.generate(prompt, max_tokens=args.max_tokens)
                parsed = extract_json(raw)
                return {
                    "source_chunk": chunk["id"],
                    "source_page": chunk["page_start"],
                    "chapter_hint": chunk.get("chapter_hint", ""),
                    "text": chunk["text"],
                    "raw_response": raw,
                    "entities": parsed.get("entities", []),
                    "triples": parsed.get("triples", []),
                }
            except Exception as exc:
                last_error = exc
                time.sleep(2 * attempt)
        return {
            "source_chunk": chunk["id"],
            "source_page": chunk["page_start"],
            "chapter_hint": chunk.get("chapter_hint", ""),
            "text": chunk["text"],
            "error": repr(last_error),
            "raw_response": raw,
            "entities": [],
            "triples": [],
        }

    pending = [chunk for chunk in chunks if chunk["id"] not in done]
    with args.out.open("a", encoding="utf-8") as f:
        if args.workers <= 1:
            for chunk in tqdm(pending, desc="DeepSeek extracting"):
                row = extract_one(chunk)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                time.sleep(args.sleep)
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as executor:
                futures = [executor.submit(extract_one, chunk) for chunk in pending]
                for future in tqdm(as_completed(futures), total=len(futures), desc="DeepSeek extracting"):
                    row = future.result()
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    f.flush()
                    time.sleep(args.sleep)


if __name__ == "__main__":
    main()
