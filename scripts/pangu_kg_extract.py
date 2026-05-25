from __future__ import annotations

import argparse
import json
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import requests
from tqdm import tqdm


SYSTEM_PROMPT = """你是船体装配工艺知识图谱抽取专家，任务是从《中级船体装配工工艺学》的教材文本中抽取实体、关系和三元组。

你必须遵守以下要求：
1. 只根据输入文本抽取，不要编造教材中没有出现或无法由原文直接支持的知识。
2. 输出必须是合法 JSON，不要输出 Markdown、解释文字或多余内容。
3. 实体类型只能从给定本体中选择。
4. 关系类型只能从给定关系列表中选择。
5. 每条三元组必须保留 evidence 原文证据、source_page、source_chunk 和 confidence。
6. 如果文本信息不足以形成关系，返回空数组。
"""

ONTOLOGY_PROMPT = """允许的实体类型：
- Chapter：章节、节、知识单元
- ProcessObject：工艺对象，如船体、分段、底部分段、舷侧分段
- Component：构件，如肋骨、甲板、舱壁、内底板、纵向构件
- Process：工艺过程，如船体放样、分段装配、船体总装配、船体修理
- Operation：工序或操作，如划线、定位、测量、吊装、合拢、焊接、除锈
- ToolEquipment：工具设备，如激光经纬仪、卷尺、线锤、胎架
- Measurement：测量对象或指标，如高度、宽度、长度、垂直度、水平度、直线度
- Parameter：工艺参数、基准、公式、条件
- Material：材料或介质
- QualityRequirement：质量要求、检查项、控制要求
- Defect：问题或缺陷
- StandardSafety：安全要求、标准、规范

允许的关系类型：
- contains：包含
- belongs_to：属于
- used_for：用于
- uses_tool：使用工具
- operates_on：操作对象
- precedes：前置工序
- follows：后续工序
- measures：测量指标
- controls：控制指标
- provides_basis_for：产生依据
- composed_of：由……组成
- assembled_with：连接/装配
- located_at：位置关系
- causes：导致
- checks：检查/评估
- repairs：修理对象
"""


def build_user_prompt(chunk: dict[str, Any]) -> str:
    return f"""{ONTOLOGY_PROMPT}

请从以下教材片段中抽取知识图谱三元组。

source_chunk: {chunk["id"]}
source_page: {chunk["page_start"]}
chapter_hint: {chunk.get("chapter_hint", "")}

文本：
{chunk["text"]}

输出 JSON 格式：
{{
  "entities": [
    {{
      "name": "实体名称",
      "type": "实体类型",
      "aliases": [],
      "definition": "基于原文的一句话定义，没有则为空字符串",
      "source_page": {chunk["page_start"]},
      "source_chunk": "{chunk["id"]}",
      "confidence": 0.0
    }}
  ],
  "triples": [
    {{
      "head": "头实体名称",
      "head_type": "头实体类型",
      "relation": "关系类型",
      "tail": "尾实体名称",
      "tail_type": "尾实体类型",
      "evidence": "支持该三元组的原文短句",
      "source_page": {chunk["page_start"]},
      "source_chunk": "{chunk["id"]}",
      "confidence": 0.0
    }}
  ]
}}
"""


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


class LLMClient(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class OpenAICompatibleClient(LLMClient):
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 180):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "top_p": 0.85,
                "max_tokens": 1800,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


class LocalTransformersClient(LLMClient):
    def __init__(self, model_path: str, device_map: str = "auto"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            device_map=device_map,
            torch_dtype=dtype,
            low_cpu_mem_usage=True,
        )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        import torch

        prompt = f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>\n"
        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=1800,
                temperature=0.1,
                top_p=0.85,
                do_sample=False,
            )
        generated = output[0][inputs["input_ids"].shape[-1] :]
        return self.tokenizer.decode(generated, skip_special_tokens=True)


def get_client(args: argparse.Namespace) -> LLMClient:
    if args.backend == "openai-compatible":
        return OpenAICompatibleClient(
            base_url=args.base_url or os.environ.get("PANGU_BASE_URL", "http://localhost:8000/v1"),
            api_key=args.api_key or os.environ.get("PANGU_API_KEY", "EMPTY"),
            model=args.model,
        )
    return LocalTransformersClient(args.model_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract shipbuilding KG triples with Pangu-compatible LLM.")
    parser.add_argument("--chunks", default="data/processed/ship_textbook_chunks.jsonl")
    parser.add_argument("--out", default="data/kg/pangu_raw_extractions.jsonl")
    parser.add_argument("--backend", choices=["local-transformers", "openai-compatible"], default="openai-compatible")
    parser.add_argument("--model-path", default="models/openPangu-Embedded-7B-model")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--model", default="openpangu-7b")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    chunks_path = Path(args.chunks)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = [json.loads(line) for line in chunks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        chunks = chunks[: args.limit]

    done: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["source_chunk"])

    client = get_client(args)
    with out_path.open("a", encoding="utf-8") as f:
        for chunk in tqdm(chunks, desc="extract"):
            if chunk["id"] in done:
                continue
            user_prompt = build_user_prompt(chunk)
            raw = client.generate(SYSTEM_PROMPT, user_prompt)
            parsed = extract_json(raw)
            row = {
                "source_chunk": chunk["id"],
                "source_page": chunk["page_start"],
                "chapter_hint": chunk.get("chapter_hint", ""),
                "raw_response": raw,
                "entities": parsed.get("entities", []),
                "triples": parsed.get("triples", []),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()


if __name__ == "__main__":
    main()

