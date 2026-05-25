# openPangu 7B 下载部署说明

## 1. 目标

为了满足高分路线，本项目使用 7B 级 openPangu 模型参与知识抽取。模型负责从预处理后的 `ship_textbook_chunks.jsonl` 中抽取实体和关系，输出可追溯的三元组。

## 2. 模型选择

优先选择：

- `openpangu/openPangu-Embedded-7B-model`

原因：

- 属于 openPangu 7B 级开源模型。
- Hugging Face 仓库包含 tokenizer、config、safetensors 权重和自定义 modeling 代码。
- 更适合用 `transformers` 方式集成到抽取脚本中。

备选：

- `openpangu/openPangu-7B-Diffusion-Base`

该模型官方说明推荐昇腾 NPU、CANN、torch-npu 环境，更适合有昇腾服务器时部署。

## 3. 本机硬件评估

当前机器检测结果：

- GPU：NVIDIA GeForce RTX 3060 Laptop
- 显存：6GB
- 磁盘：D 盘剩余空间充足

风险：

- 7B 模型半精度推理通常需要 14GB 以上显存，6GB 显存大概率无法直接本地加载完整模型。
- 如果没有 4bit/GGUF 量化权重，Windows 本地推理可能只能 CPU 跑，速度会非常慢。

因此项目采用“双后端”设计：

- `local-transformers`：在有足够 GPU/NPU 的机器上本地加载 openPangu 7B。
- `openai-compatible`：通过兼容 OpenAI Chat Completions 的 Pangu/vLLM 服务调用。

## 4. 环境创建

```powershell
conda env create -f environment-pangu.yml
conda activate shiprag-pangu
```

## 5. 下载官方模型

```powershell
powershell -ExecutionPolicy Bypass -File scripts\download_pangu_model.ps1
```

模型默认下载到：

```text
models/openPangu-Embedded-7B-model
```

## 6. 本地 Transformers 抽取

适用于有足够显存的 GPU/NPU 服务器：

```powershell
conda activate shiprag-pangu
python scripts\pangu_kg_extract.py `
  --backend local-transformers `
  --model-path models\openPangu-Embedded-7B-model `
  --chunks data\processed\ship_textbook_chunks.jsonl `
  --out data\kg\pangu_raw_extractions.jsonl
```

## 7. 远程 Pangu API 抽取

如果 Pangu 部署在服务器，或使用 vLLM/OpenAI 兼容服务：

```powershell
$env:PANGU_BASE_URL="http://服务器地址:8000/v1"
$env:PANGU_API_KEY="EMPTY"

python scripts\pangu_kg_extract.py `
  --backend openai-compatible `
  --model openpangu-7b `
  --chunks data\processed\ship_textbook_chunks.jsonl `
  --out data\kg\pangu_raw_extractions.jsonl
```

## 8. 报告写法

本项目采用 openPangu 7B 作为知识抽取模型。首先将扫描版教材经过 OCR、清洗和分块，形成面向大模型输入的 chunk 数据；随后基于船体装配领域本体设计 Pangu 抽取指令，将每个文本块输入 Pangu 模型，要求模型输出实体、关系和带证据的三元组。为提高图谱质量，系统进一步设计 NormalizeAgent 和 ReviewAgent，对实体同义词、OCR 错字、关系方向和证据一致性进行检查。

