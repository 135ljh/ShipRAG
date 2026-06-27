# 整本书 ShipRAG 全流程成果说明

本文档单独整理《中级船体装配工工艺学》整本书级 RAG 系统已经完成的全过程成果。注意：本文档只汇总整本书 RAG 的构建流程、系统实现、数据产物和可运行能力，不包含此前针对整本书 RAG 做过的评测指标。

## 1. 项目目标

整本书级 ShipRAG 的目标是把扫描版教材《中级船体装配工工艺学》处理为可检索、可追溯、可问答的知识系统。系统不是单纯把 PDF 转为文本后交给大模型回答，而是完成了以下闭环：

```text
扫描版 PDF
-> OCR 与文本清洗
-> 文本分块
-> Pangu 7B 知识抽取
-> 知识图谱构建
-> Neo4j 图数据库存储
-> Qdrant 文本向量库
-> Graph + Vector 混合检索
-> 多智能体 RAG 问答
-> 前端可视化问答工作台
```

整本书系统主要服务于三个目的：

1. 将教材中的船体装配工艺知识组织为结构化知识图谱。
2. 让用户能够通过自然语言查询教材原文和图谱事实。
3. 让答案能够同时返回文本证据、图谱证据和智能体执行链路，增强可解释性。

## 2. 原始语料与数据预处理成果

整本书原始语料为：

```text
中级船体装配工工艺学_11934890.pdf
```

该 PDF 是扫描图像型文档，不能直接提取高质量文本。因此项目实现了 OCR 预处理流程：

1. 使用 PyMuPDF 读取 PDF 页面。
2. 将页面渲染为图像。
3. 使用 RapidOCR 识别中文文本。
4. 对 OCR 结果进行清洗，包括去除页码、空行、无意义字符、异常空白和明显噪声。
5. 保留页码、行文本、OCR 置信度和清洗文本，便于后续追溯。
6. 将清洗文本切分为适合知识抽取和 RAG 检索的 chunk。

整本书预处理统计如下：

| 项目 | 数值 |
|---|---:|
| PDF 总页数 | 192 |
| 已处理页数 | 192 |
| 清洗后总字符数 | 122270 |
| 文本 chunk 数 | 230 |
| 平均 OCR 置信度 | 0.808 |
| 预处理耗时 | 94.74 秒 |

主要输出文件：

| 文件 | 作用 |
|---|---|
| `data/processed/ship_textbook_pages.cleaned.jsonl` | 逐页 OCR 与清洗结果 |
| `data/processed/ship_textbook.cleaned.md` | 按页组织的整书 Markdown 文本 |
| `data/processed/ship_textbook_chunks.jsonl` | 面向知识抽取和 RAG 的文本块 |
| `data/processed/preprocess_metadata.json` | 页数、字符数、chunk 数、OCR 置信度等统计信息 |
| `data/processed/README.md` | 数据预处理产物说明 |

复现命令：

```powershell
python scripts\preprocess_ship_pdf.py --zoom 1.2 --out-dir data\processed
```

## 3. 整本书知识图谱本体设计成果

整本书级知识图谱面向船体装配工艺领域设计。本体文件位于：

```text
docs/kg_design/ontology_design.md
```

实体类型包括：

| 类型 | 含义 |
|---|---|
| Chapter | 章节、节、知识单元 |
| ProcessObject | 工艺对象，如船体、分段、底部分段、舷侧分段 |
| Component | 船体构件，如外板、甲板、肋骨、肘板 |
| Process | 工艺过程，如船体放样、分段装配、船体总装配 |
| Operation | 工序操作，如划线、定位、测量、吊装、合拢 |
| ToolEquipment | 工具设备，如激光经纬仪、胎架、线锤、卷尺 |
| Measurement | 测量对象或指标，如高度、宽度、垂直度、直线度 |
| Parameter | 工艺参数、基准、公式、施工条件 |
| Material | 材料或介质 |
| QualityRequirement | 质量要求或检查项 |
| Defect | 缺陷、问题或变形 |
| StandardSafety | 标准、安全规范 |

关系类型包括：

```text
contains, belongs_to, used_for, uses_tool, operates_on,
precedes, follows, measures, controls, provides_basis_for,
composed_of, assembled_with, located_at, causes, checks, repairs
```

本体设计的重点是让图谱能够表达“章节包含知识点、工艺使用工具、工具测量指标、构件组成分段、工序存在前后顺序、缺陷由原因导致、质量措施控制缺陷”等工业工艺知识。

## 4. Pangu 7B 知识抽取成果

整本书级知识抽取使用远程自部署的 openPangu 7B 模型。远程服务测试时显示 GPU 可用：

```json
{"status":"ok","cuda":true,"device":"NVIDIA GeForce RTX 3090"}
```

Pangu 相关目录：

```text
pangu/
```

核心文件：

| 文件 | 作用 |
|---|---|
| `pangu/prompts/kg_extraction_prompt.md` | Pangu 知识抽取 Prompt |
| `pangu/extract_triples.py` | 调用 Pangu 抽取实体和三元组 |
| `pangu/retry_failed_minimal.py` | 针对失败 chunk 的极简补抽 |
| `pangu/compact_raw_extractions.py` | 合并首次抽取和补抽结果 |
| `pangu/build_graph_data.py` | 构建规范化图谱数据 |
| `pangu/import_neo4j.py` | 导入 Neo4j |
| `pangu/run_pipeline.ps1` | 流程脚本 |

整本书 Pangu 抽取采用了“首次全量抽取 + 失败 chunk 补抽”的策略。首次抽取对有效 chunk 调用 Pangu，并记录每个 chunk 的 raw response、实体和三元组。对于 JSON 不完整或无法解析的 chunk，后续采用更短输入、更少输出、更严格 JSON 要求的极简 Prompt 进行补抽，降低输出截断概率。

主要输出文件：

| 文件 | 作用 |
|---|---|
| `pangu/outputs/raw_extractions.jsonl` | Pangu 抽取原始结果 |
| `pangu/outputs/sample_raw_extractions.jsonl` | 抽样结果 |
| `pangu/outputs/graph/entities.jsonl` | 规范化实体表 |
| `pangu/outputs/graph/relations.jsonl` | 规范化关系表 |
| `pangu/outputs/graph/entities.csv` | Neo4j/表格查看用实体 CSV |
| `pangu/outputs/graph/relations.csv` | Neo4j/表格查看用关系 CSV |
| `pangu/outputs/graph/summary.json` | 图谱规模与类型分布统计 |

## 5. 整本书知识图谱构建成果

整本书 Pangu 图谱构建时进行了以下后处理：

1. 实体清洗：删除空实体、过长实体、出版信息实体和明显非领域实体。
2. 实体规范化：修正部分 OCR 错字和同义实体，减少重复节点。
3. 关系规范化：将中文关系或模型输出关系映射为本体中的标准关系类型。
4. 三元组去重：对相同 head、relation、tail 的三元组进行合并。
5. 章节连接增强：增加教材、章节、知识点之间的 `contains` 关系，提高图谱连通性。
6. 低质量过滤：过滤低置信度、字段缺失、自环或不合法关系。

整本书最终图谱规模如下：

| 指标 | 数值 |
|---|---:|
| Pangu raw rows | 224 |
| 规范化实体数 | 1003 |
| 规范化关系数 | 1747 |
| 孤立实体数 | 33 |

实体类型分布：

| 类型 | 数量 |
|---|---:|
| Component | 290 |
| ProcessObject | 156 |
| Process | 150 |
| Operation | 94 |
| Parameter | 71 |
| ToolEquipment | 70 |
| Measurement | 63 |
| QualityRequirement | 48 |
| Defect | 26 |
| Chapter | 22 |
| Material | 7 |
| StandardSafety | 6 |

关系类型分布：

| 关系 | 数量 |
|---|---:|
| contains | 1160 |
| uses_tool | 106 |
| assembled_with | 74 |
| precedes | 72 |
| used_for | 68 |
| measures | 44 |
| composed_of | 39 |
| operates_on | 39 |
| located_at | 38 |
| controls | 27 |
| causes | 26 |
| follows | 16 |
| belongs_to | 13 |
| provides_basis_for | 11 |
| repairs | 8 |
| checks | 6 |

高连接实体包括：

| 实体 | 度数 |
|---|---:|
| 第五章船体分段的装配 | 208 |
| 第五章 | 192 |
| 第二章舟 | 174 |
| 第六章 | 156 |
| 第三章 | 152 |
| 第七章船体修理 | 104 |
| 第四章 | 92 |
| 外板 | 25 |
| 激光经纬仪 | 21 |
| 胎架 | 15 |
| 底部分段 | 15 |
| 双层底分段 | 12 |
| 肋骨 | 12 |
| 内底板 | 11 |

这些节点说明整本书图谱已经围绕章节、船体构件、测量工具、分段和装配工艺形成了较完整的结构化知识网络。

## 6. Neo4j 存储与可视化成果

整本书图谱已支持导入 Neo4j。导入脚本为：

```text
pangu/import_neo4j.py
```

导入命令：

```powershell
python pangu\import_neo4j.py --clear
```

Neo4j 中每个实体统一保存为 `:Entity` 节点，并根据实体类型附加额外标签，例如：

```text
:Entity:Component
:Entity:Process
:Entity:ToolEquipment
:Entity:Measurement
```

关系使用大写英文关系类型，例如：

```text
CONTAINS
USES_TOOL
USED_FOR
MEASURES
ASSEMBLED_WITH
PRECEDES
```

Neo4j 导入时使用 `MERGE` 合并重复关系，因此文件中的 1747 条关系导入 Neo4j 后约为 1700 条去重关系。

可视化查询示例：

```cypher
MATCH p=(a:ToolEquipment)-[r:MEASURES|USED_FOR|USES_TOOL]-(b)
RETURN p
LIMIT 50;
```

```cypher
MATCH p=(a)-[r]-(b)
WHERE a.name CONTAINS "分段" OR b.name CONTAINS "分段"
RETURN p
LIMIT 80;
```

```cypher
MATCH p=(c:Chapter)-[:CONTAINS]->(e:Entity)
RETURN p
LIMIT 100;
```

```cypher
MATCH (n:Entity)-[r]-()
RETURN n.name AS name, n.type AS type, count(r) AS degree
ORDER BY degree DESC
LIMIT 20;
```

这些查询可以用于报告截图，展示工具设备、测量指标、分段装配、章节知识单元和高连接实体的图谱结构。

## 7. Qdrant 向量库成果

整本书 RAG 系统使用 Qdrant 存储教材 chunk 向量。向量库写入脚本为：

```text
graph_rag/ingest/qdrant_ingest.py
```

数据来源：

```text
data/processed/ship_textbook_chunks.jsonl
```

Qdrant collection：

```text
shiprag_chunks
```

写入结果：

| 项目 | 数值 |
|---|---:|
| collection | `shiprag_chunks` |
| chunk 数 | 230 |
| embedding provider | hash |
| embedding dim | 384 |

项目当前使用本地 hash embedding 写入 Qdrant，目的是保证系统在第三方 embedding 服务不稳定或接口不可用时，仍能跑通完整 RAG 检索闭环。问答生成层则使用 OpenAI 兼容接口。

Qdrant payload 设计包括：

```json
{
  "chunk_id": "shiprag_p008_00008",
  "source": "中级船体装配工工艺学_11934890.pdf",
  "page_start": 8,
  "page_end": 8,
  "chapter_hint": "章节提示",
  "text": "教材原文片段",
  "char_count": 800
}
```

向量检索接口能够根据用户问题返回相关教材原文 chunk，并保留页码和 chunk_id 作为引用。

## 8. 整本书 Graph-RAG 系统实现成果

整本书 RAG 工程目录为：

```text
graph_rag/
```

已实现模块如下：

| 模块 | 文件 | 作用 |
|---|---|---|
| 配置管理 | `graph_rag/config.py` | 读取 Neo4j、Qdrant、LLM、chunk 路径等配置 |
| Neo4j 客户端 | `graph_rag/db/neo4j_client.py` | 查询实体、邻域、图谱路径 |
| Qdrant 客户端 | `graph_rag/db/qdrant_client.py` | 向量检索 |
| LLM 封装 | `graph_rag/llm.py` | OpenAI 兼容接口，支持云雾 API |
| chunk 加载 | `graph_rag/ingest/chunk_loader.py` | 加载整本书 chunk |
| Qdrant 入库 | `graph_rag/ingest/qdrant_ingest.py` | 写入 Qdrant |
| 实体链接 | `graph_rag/rag/entity_linker.py` | 精确、包含和模糊匹配实体 |
| 图谱检索 | `graph_rag/retrievers/graph_retriever.py` | 从 Neo4j 获取图谱证据 |
| 向量检索 | `graph_rag/retrievers/vector_retriever.py` | 从 Qdrant 获取文本证据 |
| 混合检索 | `graph_rag/retrievers/hybrid_retriever.py` | 融合图谱与文本 |
| 上下文构建 | `graph_rag/rag/context_builder.py` | 构造 LLM 输入上下文 |
| 答案生成 | `graph_rag/rag/answer_generator.py` | 生成带依据答案 |
| 多智能体编排 | `graph_rag/agents/orchestrator.py` | 编排多个 Agent |
| FastAPI 服务 | `graph_rag/main.py` | 对外提供 API 与前端 |
| 前端工作台 | `graph_rag/web/` | 问答、图谱检索、向量检索页面 |

整本书系统支持以下接口：

| 接口 | 作用 |
|---|---|
| `GET /health` | 检查服务状态 |
| `POST /ask` | 混合 RAG 问答 |
| `POST /graph/search` | 图谱检索 |
| `POST /vector/search` | 向量检索 |
| `GET /` | 前端问答工作台 |

启动命令：

```powershell
uvicorn graph_rag.main:app --host 127.0.0.1 --port 8090
```

前端地址：

```text
http://127.0.0.1:8090/
```

## 9. 多智能体 RAG 成果

整本书 RAG 已加入多智能体编排机制。执行链路如下：

```text
RouterAgent
-> EntityAgent
-> GraphAgent
-> DocumentAgent
-> SynthesisAgent
-> AnswerAgent
-> VerifierAgent
```

各智能体职责：

| 智能体 | 职责 |
|---|---|
| RouterAgent | 判断问题类型和检索路线 |
| EntityAgent | 从问题中识别并链接图谱实体 |
| GraphAgent | 查询 Neo4j 图谱事实 |
| DocumentAgent | 查询 Qdrant 文本证据 |
| SynthesisAgent | 合并图谱证据和文本证据 |
| AnswerAgent | 调用 LLM 生成答案 |
| VerifierAgent | 检查答案是否有证据支撑 |

`/ask` 接口会在 `metadata.agent_trace` 中返回每个智能体的执行状态、职责说明和耗时。前端工作台也加入了智能执行链路展示区域，便于说明系统不是单模型直接回答，而是多个模块协同完成检索、生成和校验。

## 10. 前端工作台成果

整本书前端位于：

```text
graph_rag/web/
```

前端实现了管理后台风格的 ShipRAG 工作台，包含：

1. RAG 问答视图：输入问题、Top K、Graph Hops，生成答案。
2. 图谱检索视图：按实体名称检索 Neo4j 图谱邻域。
3. 向量检索视图：按自然语言查询教材原文 chunk。
4. 服务状态区：显示 Neo4j、Qdrant 和多智能体编排状态。
5. 智能执行链路：展示 Agent Trace。
6. 检索证据区：展示 linked entities、graph evidence 和 document evidence。

系统能够回答基础元信息问题，例如“这本书在讲什么”“这本书有多少章”等，也能回答领域问题，例如“激光经纬仪在船体装配中有什么用途”“胎架在分段装配中起什么作用”等。基础问题通过教材简介和目录信息快速回答；领域问题通过 Neo4j 图谱事实和 Qdrant 原文证据共同支撑。

## 11. 整本书 RAG 可复现命令

数据预处理：

```powershell
python scripts\preprocess_ship_pdf.py --zoom 1.2 --out-dir data\processed
```

Pangu 首次抽取：

```powershell
python pangu\extract_triples.py --all --max-input-chars 500
```

失败 chunk 补抽：

```powershell
python pangu\retry_failed_minimal.py --max-input-chars 220 --max-new-tokens 260
python pangu\compact_raw_extractions.py
```

构建图谱文件：

```powershell
python pangu\build_graph_data.py
```

导入 Neo4j：

```powershell
python pangu\import_neo4j.py --clear
```

写入 Qdrant：

```powershell
python -m graph_rag.ingest.qdrant_ingest
```

启动整本书 RAG：

```powershell
uvicorn graph_rag.main:app --host 127.0.0.1 --port 8090
```

访问前端：

```text
http://127.0.0.1:8090/
```

## 12. 整本书 RAG 成果总结

整本书 ShipRAG 已经完成从扫描版教材到可运行 Graph-RAG 系统的完整流程。主要成果包括：

1. 完成 192 页扫描教材 OCR 与清洗。
2. 生成 230 个整本书 RAG 文本块。
3. 使用 Pangu 7B 自部署模型抽取整本书知识。
4. 构建 1003 个实体、1747 条关系的整本书知识图谱。
5. 将图谱导入 Neo4j，并支持 Browser 可视化查询。
6. 将教材文本块写入 Qdrant，形成 `shiprag_chunks` 向量库。
7. 实现 FastAPI 后端，支持 `/ask`、`/graph/search`、`/vector/search`。
8. 实现 Graph + Vector 混合检索和答案生成。
9. 实现多智能体执行链路。
10. 实现前端问答工作台。

整本书 RAG 的意义在于证明系统具备规模化处理教材、构建知识图谱和搭建智能问答应用的能力。它为后续第五章精细化实验提供了工程基础，也为课程报告中的“数据预处理、知识图谱设计、Pangu 知识抽取、Neo4j 存储管理、RAG 系统设计”提供了完整成果支撑。
