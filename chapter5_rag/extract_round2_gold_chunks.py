from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import json5
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "chapter5_rag"
DATA_PATH = BASE_DIR / "data" / "chapter5_chunks.jsonl"
GOLD_PATH = BASE_DIR / "eval" / "gold_annotations.json"

ENTITY_TYPES = [
    "分段类型", "装配方式", "船体构件", "工装设备", "工艺工序",
    "图纸资料", "质量问题", "控制措施", "数据指标", "其他",
]
RELATION_TYPES = [
    "包括", "属于", "可采用", "适用于", "用于", "指导", "依据", "组成",
    "装配于", "连接", "定位", "对准", "控制", "导致", "校正", "代表",
    "反映", "表达", "具有", "设置依据", "标准范围", "允许界限",
    "约占", "同时提供", "装配程序包括", "装配顺序", "装配基面",
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def selected_chunks() -> list[dict[str, Any]]:
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    ids = [row["chunk_id"] for row in gold]
    chunks = {row["id"]: row for row in read_jsonl(DATA_PATH)}
    return [chunks[chunk_id] for chunk_id in ids]


def extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found.")
    candidate = re.sub(r",\s*([}\]])", r"\1", text[start : end + 1])
    try:
        return json.loads(candidate)
    except Exception:
        return json5.loads(candidate)


def normalize_payload(payload: dict[str, Any], chunk: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    entities = []
    triples = []
    for item in payload.get("entities", []) or []:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        typ = str(item.get("type", "")).strip() or "其他"
        if typ not in ENTITY_TYPES:
            typ = "其他"
        entities.append(
            {
                "name": name,
                "type": typ,
                "evidence": str(item.get("evidence", "")).strip(),
                "source_chunk": chunk["id"],
                "source_page": chunk.get("page_start"),
            }
        )
    for item in payload.get("triples", []) or []:
        head = str(item.get("head", "")).strip()
        relation = str(item.get("relation", "")).strip()
        tail = str(item.get("tail", "")).strip()
        if not (head and relation and tail):
            continue
        triples.append(
            {
                "head": head,
                "relation": relation,
                "tail": tail,
                "evidence": str(item.get("evidence", "")).strip(),
                "source_chunk": chunk["id"],
                "source_page": chunk.get("page_start"),
            }
        )
    return {"entities": entities, "triples": triples}


def build_prompt(chunk: dict[str, Any]) -> str:
    return f"""你是船体装配工艺知识图谱抽取助手。请从给定文本中抽取实体和知识三元组。

要求：
1. 实体数量尽量完整，每个 chunk 抽取 12-15 个重要实体。
2. 三元组数量尽量完整，每个 chunk 抽取 10-20 条重要三元组。
3. 不要只抽概括关系，要覆盖概念定义、分类、组成、适用场景、装配流程、定位关系、工装设备、质量标准等知识。
4. 对于“包括 A、B、C”这类句子，要拆成多条三元组。
5. 对于工艺流程“步骤1--步骤2--步骤3”，要抽取“装配程序包括”关系。
6. 对于表格中的标准范围和允许界限，要分别抽取。
7. “正装、倒装、侧装、卧装、放射式、插入式、框架式”等枚举项要分别抽取。
8. 三元组必须能被原文 evidence 支撑；evidence 必须是原文短句或表格行。
9. 只输出 JSON，不要解释，不要 Markdown，不要代码块。

实体类型限定：{", ".join(ENTITY_TYPES)}
关系类型优先使用：{", ".join(RELATION_TYPES)}

输出 JSON 格式：
{{
  "entities": [
    {{"name": "实体名", "type": "实体类型", "evidence": "原文依据"}}
  ],
  "triples": [
    {{"head": "头实体", "relation": "关系", "tail": "尾实体", "evidence": "原文依据"}}
  ]
}}

source_chunk: {chunk["id"]}
section: {chunk.get("chapter_hint", "")}

text:
{chunk.get("text", "")}
"""


class PanguClient:
    def __init__(self) -> None:
        load_dotenv(ROOT / "pangu" / ".env")
        load_dotenv(BASE_DIR / ".env", override=False)
        self.base_url = os.getenv("PANGU_BASE_URL", "http://10.21.77.7:8000").rstrip("/")
        self.generate_path = os.getenv("PANGU_GENERATE_PATH", "/generate")
        self.timeout = int(os.getenv("PANGU_TIMEOUT", "240"))

    def generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}{self.generate_path}",
            json={"prompt": prompt, "max_new_tokens": 2600, "temperature": 0.0},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("content") or data.get("text") or data.get("response") or json.dumps(data, ensure_ascii=False)


class DeepSeekClient:
    def __init__(self) -> None:
        load_dotenv(ROOT / ".env")
        load_dotenv(BASE_DIR / ".env", override=False)
        self.api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("CHAPTER5_DEEPSEEK_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY.")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout = int(os.getenv("DEEPSEEK_TIMEOUT", "180"))

    def generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是严谨的知识图谱抽取助手，只输出 JSON。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 3200,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def run_model(model: str) -> None:
    chunks = selected_chunks()
    out_dir = BASE_DIR / "outputs" / "round2" / model
    raw_path = out_dir / "raw_extractions.jsonl"
    entity_path = out_dir / "kg_entities.jsonl"
    triple_path = out_dir / "kg_triples.jsonl"
    client = PanguClient() if model == "pangu" else DeepSeekClient()

    raw_rows = []
    all_entities = []
    all_triples = []
    for chunk in chunks:
        prompt = build_prompt(chunk)
        raw = ""
        error = None
        parsed: dict[str, Any] | None = None
        for attempt in range(2):
            try:
                raw = client.generate(prompt)
                parsed = extract_json(raw)
                break
            except Exception as exc:
                error = repr(exc)
                if attempt == 0:
                    time.sleep(1.0)
        if parsed is None:
            row = {
                "source_chunk": chunk["id"],
                "section": chunk.get("chapter_hint", ""),
                "text": chunk.get("text", ""),
                "raw_response": raw,
                "error": error,
                "entities": [],
                "triples": [],
            }
        else:
            normalized = normalize_payload(parsed, chunk)
            row = {
                "source_chunk": chunk["id"],
                "section": chunk.get("chapter_hint", ""),
                "text": chunk.get("text", ""),
                "raw_response": raw,
                "entities": normalized["entities"],
                "triples": normalized["triples"],
            }
            all_entities.extend(normalized["entities"])
            all_triples.extend(normalized["triples"])
        raw_rows.append(row)
        print(f"{model} {chunk['id']} entities={len(row['entities'])} triples={len(row['triples'])} error={bool(row.get('error'))}")

    write_jsonl(raw_path, raw_rows)
    write_jsonl(entity_path, all_entities)
    write_jsonl(triple_path, all_triples)
    print(json.dumps({"model": model, "raw": str(raw_path), "entities": len(all_entities), "triples": len(all_triples)}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Round2 extraction for the five gold chunks only.")
    parser.add_argument("--model", choices=["pangu", "deepseek"], required=True)
    args = parser.parse_args()
    run_model(args.model)


if __name__ == "__main__":
    main()
