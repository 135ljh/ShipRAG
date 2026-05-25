# Pangu 大模型实体识别与关系抽取智能体设计

## 1. 是否必须下载并部署 Pangu 7B

不一定是“本体设计”这一步必须完成的动作。

课程要求中的“知识图谱设计”主要包括：

- 定义知识图谱本体。
- 设计实体识别和关系抽取的大模型指令。
- 说明如何用 Pangu 大模型或智能体完成抽取。

如果只是完成报告中的设计部分，可以先给出本体、Prompt 和智能体流程。真正下载、部署并调用 Pangu 7B，属于后续“知识抽取实现”和“系统运行”部分。

如果目标是冲击 90 分以上，报告要求提到“用 7B 或以下的 openpangu 模型抽取整本书的知识三元组，并形成高质量图谱”，这时就应该实际部署或调用 7B 级别 openPangu 模型完成全书抽取。

## 2. Pangu 模型选型建议

可选路线：

| 路线 | 说明 | 适用情况 |
|---|---|---|
| 本地部署 openPangu 7B | 下载官方开源模型权重，在本地或服务器推理 | 有合适 GPU/NPU 资源，想完整体现本地化方案 |
| 平台/API 调用 Pangu | 使用可访问的 Pangu 服务接口 | 学校或团队已有平台资源 |
| 先用兼容 OpenAI 接口的本地模型模拟 | 先完成流程和数据格式，后续替换为 Pangu | 时间紧、硬件不足、先保证项目能运行 |

注意：当前官方 openPangu 7B 相关模型在 Hugging Face 有权重和推理代码，但部分模型说明推荐昇腾 NPU 环境。若普通 Windows 笔记本没有足够显存，本地直接部署 7B 可能很慢或无法运行。

## 3. 智能体分工

本项目设计 4 个智能体，形成流水线：

| 智能体 | 输入 | 输出 | 作用 |
|---|---|---|---|
| OntologyAgent | 教材目录、样本文本、本体草案 | 本体类别和关系集合 | 辅助优化实体类型和关系类型 |
| ExtractionAgent | `ship_textbook_chunks.jsonl` 中的文本块 | 实体和三元组 JSON | 主体抽取 |
| NormalizeAgent | 抽取结果、实体词表 | 规范化实体和去重结果 | 处理 OCR 错字、同义词、别名 |
| ReviewAgent | 三元组、原文 evidence | 通过/驳回/修正建议 | 检查证据支持和关系方向 |

## 4. 抽取流程

1. 读取 `data/processed/ship_textbook_chunks.jsonl`。
2. 对每个 chunk 调用 ExtractionAgent，使用 Pangu Prompt 抽取实体和三元组。
3. 将所有 chunk 的抽取结果合并为原始三元组表。
4. NormalizeAgent 对实体名称进行统一，例如“船侧分段/舷侧分段”等 OCR 或术语变体需要归一。
5. ReviewAgent 检查三元组是否有原文证据，过滤低置信度或无法支持的关系。
6. 导出为：
   - `entities.csv`
   - `relations.csv`
   - `triples.jsonl`
   - Neo4j `cypher` 导入脚本

## 5. 推荐抽取参数

| 参数 | 建议值 |
|---|---|
| chunk 长度 | 800-1000 中文字符 |
| overlap | 100-150 字符 |
| temperature | 0.1-0.2 |
| top_p | 0.8-0.9 |
| max_new_tokens | 1200-2000 |
| 输出格式 | JSON |
| 低置信度阈值 | `< 0.65` 的三元组进入人工复核 |

## 6. 输出数据格式

建议原始抽取结果使用 JSONL：

```json
{
  "source_chunk": "shiprag_p008_00008",
  "source_page": 8,
  "entities": [],
  "triples": []
}
```

最终进入图数据库前拆为实体表和关系表：

```csv
id,name,type,aliases,definition,source_pages,confidence
```

```csv
head,relation,tail,evidence,source_page,source_chunk,confidence
```

## 7. 报告中可写的表述

本项目在知识图谱设计阶段首先基于《中级船体装配工工艺学》的教材目录和预处理文本构建领域本体，将教材知识划分为章节、工艺对象、船体构件、工艺过程、工序操作、工具设备、测量指标、工艺参数、质量要求、缺陷和安全规范等实体类型，并设计包含“用于、使用工具、操作对象、测量指标、控制指标、前置工序、组成关系、装配关系”等关系类型的图谱模式。

在知识抽取阶段，设计基于 Pangu 大模型的多智能体流水线。其中 ExtractionAgent 负责从清洗后的文本块中抽取实体和三元组，NormalizeAgent 负责实体归一化和 OCR 错误修正，ReviewAgent 负责证据一致性检查和低质量三元组过滤。每条三元组均保留来源页码、文本证据和置信度，以保证图谱的可追溯性和可评测性。

