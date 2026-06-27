# 第五章 RAG 全流程成果说明

本文档单独整理第五章“船体分段的装配”RAG 系统已经完成的全过程成果。与整本书 ShipRAG 不同，第五章系统是一个独立、精细化、可评测的实验子系统，重点体现高质量文本整理、知识图谱构建、人工标注评测、Pangu 与 DeepSeek 对比、纯向量 RAG 基线和 Graph-RAG 多方案对比。

## 1. 第五章实验目标

第五章 RAG 的目标是围绕“船体分段的装配”这一重点章节，构建一个更精细、更可控、更适合评测的知识图谱与问答系统。该系统主要回答以下类型问题：

1. 分段装配概念定义问题。
2. 装配方式分类和对比问题。
3. 双层底分段、舷侧分段、艏艉分段等工艺流程问题。
4. 分段工作图、分段组立树、装配数据等图纸资料问题。
5. 焊接变形、制造精度、质量控制措施等质量标准问题。
6. 表格数据类问题，例如标准范围和允许界限。

第五章系统的完整流程为：

```text
第五章清洗文本
-> chunk 切分
-> Pangu / DeepSeek 知识抽取
-> 第五章知识图谱构建
-> Neo4j 独立子图存储
-> Qdrant 独立向量库
-> Pangu Graph-RAG / DeepSeek Graph-RAG / 纯向量 RAG
-> 多智能体执行链路
-> 前端问答与图谱可视化
-> 人工标注评测与方案对比
```

## 2. 第五章语料整理成果

第五章清洗文本来源于《中级船体装配工工艺学》第五章“船体分段的装配”。项目将第五章单独整理为：

```text
chapter5_rag/第五章.txt
```

同时生成了结构化数据目录：

```text
chapter5_rag/data/
```

主要文件：

| 文件 | 作用 |
|---|---|
| `chapter5_rag/第五章.txt` | 第五章原始清洗文本 |
| `chapter5_rag/data/chapter5.cleaned.md` | 第五章 Markdown 清洗版 |
| `chapter5_rag/data/chapter5_chunks.jsonl` | 第五章 RAG 与知识抽取 chunk |

第五章文本清洗重点包括：

1. 修正 OCR 错误。
2. 去除无关页码、图注干扰和重复换行。
3. 保留工艺流程的完整顺序。
4. 保留图纸资料、表格数据和质量标准相关文本。
5. 保留可作为 evidence 的原文短句。

最终第五章被切分为 29 个 chunk。每个 chunk 保留：

| 字段 | 含义 |
|---|---|
| `id` | chunk 编号，如 `chapter5_012` |
| `source` | 来源文件 |
| `page_start` / `page_end` | 页码范围 |
| `chapter_hint` | 章节或小节标题 |
| `text` | 正文内容 |
| `char_count` | 字符数 |

该元数据设计使后续抽取、图谱构建、RAG 检索和人工评测能够使用统一的 `chunk_id` 进行追溯。

## 3. 第五章 Pangu 知识抽取与图谱成果

第五章 Pangu 版本使用远程自部署 Pangu 7B 模型抽取实体和三元组。核心脚本为：

```text
chapter5_rag/chapter5_pipeline.py
```

Pangu Prompt 位于：

```text
chapter5_rag/prompts/kg_extraction_prompt.md
```

Pangu 完整流程包括：

```powershell
python chapter5_rag\chapter5_pipeline.py chunk --max-chars 850 --overlap 100
python chapter5_rag\chapter5_pipeline.py extract --retries 2 --max-new-tokens 900 --sleep 0.1
python chapter5_rag\chapter5_pipeline.py build-graph --min-confidence 0.55
```

Pangu 输出文件：

| 文件 | 作用 |
|---|---|
| `chapter5_rag/outputs/raw_extractions.jsonl` | Pangu 第五章原始抽取结果 |
| `chapter5_rag/outputs/graph/entities.jsonl` | 第五章 Pangu 实体表 |
| `chapter5_rag/outputs/graph/relations.jsonl` | 第五章 Pangu 关系表 |
| `chapter5_rag/outputs/graph/summary.json` | 第五章 Pangu 图谱摘要 |

Pangu 第五章完整图谱规模：

| 指标 | 数值 |
|---|---:|
| raw rows | 31 |
| 实体数 | 205 |
| 关系数 | 257 |
| 孤立实体数 | 27 |

Pangu 第五章实体类型分布：

| 类型 | 数量 |
|---|---:|
| ProcessObject | 52 |
| Chapter | 33 |
| Component | 29 |
| Process | 26 |
| Operation | 22 |
| ToolEquipment | 15 |
| Parameter | 10 |
| Defect | 8 |
| QualityRequirement | 7 |
| Measurement | 2 |
| StandardSafety | 1 |

Pangu 高连接节点包括：

| 节点 | 度数 |
|---|---:|
| 第五章船体分段的装配 | 25 |
| 装配方式按构架装配顺序或结构单元分类 | 24 |
| 分段装配 | 10 |
| 分段工作图 | 10 |
| 双层底分段 | 9 |
| 焊接变形 | 9 |
| 分段装配相关数据 | 9 |
| 装纵桁和肋板 | 9 |
| 肋板 | 7 |
| 胎架 | 7 |

这些结果说明 Pangu 图谱能够围绕第五章主题形成以“分段装配、双层底分段、焊接变形、胎架、肋板”等为核心的知识网络。

## 4. 第五章 DeepSeek 知识抽取与图谱成果

为了与 Pangu 对比，项目另外实现了 DeepSeek 版本第五章知识抽取与 RAG。核心脚本为：

```text
chapter5_rag/deepseek_pipeline.py
chapter5_rag/deepseek_app.py
```

DeepSeek 抽取与构图命令：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
python chapter5_rag\deepseek_pipeline.py extract --retries 2 --sleep 0.1 --max-tokens 1800
python chapter5_rag\deepseek_pipeline.py build-graph --min-confidence 0.55
```

DeepSeek 输出目录：

```text
chapter5_rag/deepseek_outputs/
```

主要文件：

| 文件 | 作用 |
|---|---|
| `chapter5_rag/deepseek_outputs/raw_extractions.jsonl` | DeepSeek 第五章原始抽取结果 |
| `chapter5_rag/deepseek_outputs/graph/entities.jsonl` | DeepSeek 第五章实体表 |
| `chapter5_rag/deepseek_outputs/graph/relations.jsonl` | DeepSeek 第五章关系表 |
| `chapter5_rag/deepseek_outputs/graph/summary.json` | DeepSeek 第五章图谱摘要 |

DeepSeek 第五章完整图谱规模：

| 指标 | 数值 |
|---|---:|
| raw rows | 29 |
| failed rows | 0 |
| 实体数 | 192 |
| 关系数 | 335 |
| 孤立实体数 | 1 |

DeepSeek 第五章实体类型分布：

| 类型 | 数量 |
|---|---:|
| Component | 49 |
| Process | 35 |
| Chapter | 30 |
| ProcessObject | 25 |
| Operation | 22 |
| ToolEquipment | 13 |
| Measurement | 7 |
| Parameter | 6 |
| Defect | 4 |
| StandardSafety | 1 |

DeepSeek 高连接节点包括：

| 节点 | 度数 |
|---|---:|
| 第五章船体分段的装配 | 25 |
| 肋板 | 15 |
| 分段装配 | 13 |
| 舷侧纵桁 | 10 |
| 分段工作图 | 10 |
| 分段装配相关数据 | 10 |
| 装配方式按构架装配顺序或结构单元分类 | 10 |
| 分段局部变形精度标准 | 8 |
| 内底板 | 9 |
| 胎架 | 9 |
| 双斜切胎架 | 8 |
| 纵骨 | 8 |

DeepSeek 图谱的关系数量更多，孤立实体更少，说明其语义覆盖和连通性更强；但在人工标注 round2 实验中曾出现复杂 chunk JSON 不完整问题，因此需要结合稳定性评测一起分析。

## 5. 第五章 Neo4j 独立存储成果

第五章 Pangu 图谱和 DeepSeek 图谱都支持独立写入 Neo4j，且不会影响整本书图谱。

### 5.1 Pangu 第五章 Neo4j 子图

导入脚本：

```text
chapter5_rag/import_neo4j.py
```

导入命令：

```powershell
python chapter5_rag\import_neo4j.py --clear-chapter5
```

命名空间设计：

| 项目 | 值 |
|---|---|
| 节点标签 | `:Chapter5Entity` |
| 节点 id 前缀 | `chapter5::` |
| 关系属性 | `scope = "chapter5"` |

Neo4j Browser 查询：

```cypher
MATCH p=(n:Chapter5Entity)-[r {scope: "chapter5"}]->(m:Chapter5Entity)
RETURN p
LIMIT 80;
```

### 5.2 DeepSeek 第五章 Neo4j 子图

导入脚本：

```text
chapter5_rag/import_deepseek_neo4j.py
```

导入命令：

```powershell
python chapter5_rag\import_deepseek_neo4j.py --clear-deepseek
```

命名空间设计：

| 项目 | 值 |
|---|---|
| 节点标签 | `:Chapter5DeepSeekEntity` |
| 节点 id 前缀 | `chapter5_deepseek::` |
| 关系属性 | `scope = "chapter5_deepseek"` |

Neo4j Browser 查询：

```cypher
MATCH p=(n:Chapter5DeepSeekEntity)-[r {scope: "chapter5_deepseek"}]->(m:Chapter5DeepSeekEntity)
RETURN p;
```

这种命名空间设计保证第五章子图可以独立清空、独立导入、独立展示，不会破坏整本书图谱。

## 6. 第五章 Qdrant 向量库成果

第五章 RAG 使用独立 Qdrant collection：

```text
chapter5_rag_chunks
```

向量入库脚本：

```text
chapter5_rag/chapter5_vector.py
```

入库命令：

```powershell
python chapter5_rag\chapter5_vector.py --recreate
```

向量库设计：

| 项目 | 值 |
|---|---|
| 数据来源 | `chapter5_rag/data/chapter5_chunks.jsonl` |
| chunk 数 | 29 |
| collection | `chapter5_rag_chunks` |
| embedding 方法 | 本地 hash embedding |
| 向量维度 | 384 |
| 本地 fallback 存储 | `chapter5_rag/qdrant_storage/` |

第五章向量库 payload 包含 chunk_id、source、page_start、page_end、chapter_hint、text 和 char_count。系统优先连接 Qdrant Server，如果本地 6333 未启动，可以 fallback 到 `chapter5_rag/qdrant_storage/` 的 embedded local 模式。

## 7. 第五章 RAG 系统实现成果

第五章共实现了三套 RAG 应用：

| 方案 | 文件 | 端口 | 说明 |
|---|---|---:|---|
| Pangu Graph-RAG | `chapter5_rag/chapter5_app.py` | 8092 | Pangu 图谱 + 第五章向量检索 + Pangu/LLM 生成 |
| DeepSeek Graph-RAG | `chapter5_rag/deepseek_app.py` | 8094 | DeepSeek 图谱 + 第五章向量检索 + DeepSeek 生成 |
| 纯向量 RAG 基线 | `chapter5_rag/vector_baseline_app.py` | 8095 | 不使用知识图谱，仅使用文本块向量检索 |

启动命令：

```powershell
uvicorn chapter5_rag.chapter5_app:app --host 127.0.0.1 --port 8092
```

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uvicorn chapter5_rag.deepseek_app:app --host 127.0.0.1 --port 8094
```

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uvicorn chapter5_rag.vector_baseline_app:app --host 127.0.0.1 --port 8095
```

三套系统的区别：

| 方案 | 是否使用向量库 | 是否使用知识图谱 | 是否返回图谱证据 | 适用目的 |
|---|---|---|---|---|
| 纯向量 RAG | 是 | 否 | 否 | 基线对比 |
| Pangu Graph-RAG | 是 | 是，Pangu 图谱 | 是 | 稳定可控图谱增强 |
| DeepSeek Graph-RAG | 是 | 是，DeepSeek 图谱 | 是 | 更强语义覆盖对比 |

## 8. 第五章多智能体执行链路成果

第五章 Pangu Graph-RAG 已实现多智能体执行链路。设计说明文件为：

```text
chapter5_rag/multi_agent_design.md
```

智能体包括：

| 智能体 | 职责 |
|---|---|
| PlannerAgent | 判断问题类型，规划检索策略 |
| VectorAgent | 检索 Qdrant 文本证据 |
| GraphAgent | 检索第五章知识图谱证据 |
| FusionAgent | 融合文本证据和图谱证据 |
| AnswerAgent | 生成最终答案 |
| VerifierAgent | 检查答案是否由证据支撑 |

`/ask` 接口会在 `metadata.agent_trace` 中返回执行链路。前端也将核心功能域拆分为：

1. RAG 问答。
2. 智能执行链路。
3. 检索证据。

这种设计让系统过程更透明，便于课程报告展示“多个大模型/多个智能体相互分工”的需求。

## 9. 第五章前端与图谱可视化成果

第五章前端目录：

```text
chapter5_rag/web/
```

前端实现内容：

1. RAG 问答页面。
2. 智能执行链路展示。
3. 检索证据展示。
4. 中文化标签，包括“智能执行链路、关联实体、图谱证据、文本证据”等。
5. 美化布局，避免所有证据长条堆叠在同一页面。

第五章图谱可视化目录：

```text
chapter5_rag/visualization/
```

主要文件：

| 文件 | 作用 |
|---|---|
| `build_visualization_data.py` | 从图谱文件生成前端可视化数据 |
| `visualization/graph_data.js` | 图谱节点和边数据 |
| `visualization/index.html` | 图谱可视化页面 |
| `visualization/app.js` | 交互逻辑 |
| `visualization/styles.css` | 样式 |

图谱可视化支持：

1. 节点自由拖动。
2. 画布缩放。
3. 平移浏览。
4. 查看节点和关系。
5. 展示第五章核心实体之间的连接。

该可视化可以用于报告截图，展示第五章知识图谱不是松散列表，而是围绕分段装配、构件、工艺、质量控制形成的网络。

## 10. 第五章人工标注与知识抽取评测成果

第五章构建了人工 gold 标准集，覆盖 5 个代表性 chunk：

| chunk_id | 内容主题 | 实体数 | 三元组数 |
|---|---|---:|---:|
| chapter5_001 | 分段装配概述与装配方式分类 | 16 | 15 |
| chapter5_005 | 分段工作图及相关资料 | 16 | 15 |
| chapter5_012 | 舷侧分段与双斜切胎架装配 | 19 | 15 |
| chapter5_018 | 艉部下段装配 | 22 | 16 |
| chapter5_025 | 分段制造精度标准 | 20 | 18 |
| 合计 | - | 93 | 79 |

评测相关文件：

| 文件 | 作用 |
|---|---|
| `chapter5_rag/eval/gold_sample_chunks.md` | 5 个样本 chunk 原文 |
| `chapter5_rag/eval/gold_annotations_template.json` | 人工标注模板 |
| `chapter5_rag/eval/gold_annotations.json` | 人工 gold 标准答案 |
| `chapter5_rag/eval/gold_annotations_summary.json` | 标注数量摘要 |
| `chapter5_rag/eval/eval_extraction_quality.py` | 抽取质量评测脚本 |
| `chapter5_rag/eval/extraction_round_comparison.md` | 第一轮/第二轮对比报告 |

第一轮抽取结果：

| 模型 | 预测实体数 | 预测三元组数 | 实体 F1 | Strict 三元组 F1 | JSON 合法率 | 抽取成功率 |
|---|---:|---:|---:|---:|---:|---:|
| Pangu round1 | 23 | 22 | 36.21% | 3.96% | 100.00% | 100.00% |
| DeepSeek round1 | 25 | 28 | 33.90% | 0.00% | 100.00% | 100.00% |

第二轮 Prompt 优化后结果：

| 模型 | 预测实体数 | 预测三元组数 | 实体 F1 | Strict 三元组 F1 | Relaxed 三元组 F1 | Semantic-like F1 | JSON 合法率 | 抽取成功率 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Pangu round2 | 75 | 81 | 63.10% | 0.00% | 7.50% | 7.50% | 100.00% | 100.00% |
| DeepSeek round2 | 78 | 110 | 70.18% | 5.29% | 17.99% | 20.11% | 80.00% | 80.00% |

结论：

1. Pangu 输出稳定，JSON 合法率和抽取成功率更高。
2. DeepSeek 语义覆盖更好，实体 F1、relaxed 三元组 F1 和 semantic-like F1 更高。
3. DeepSeek 在复杂 chunk 上存在 JSON 不完整风险。
4. 两个模型都存在 strict 三元组 F1 偏低问题，主要原因是实体粒度和关系表达与人工标注不完全一致。

## 11. DeepSeek 失败 chunk 补充重试成果

DeepSeek round2 中失败 chunk 为：

```text
chapter5_012
```

首次失败原因：

```text
ValueError('<string>:46 Unexpected end of input at column 199')
```

项目按照相同 Prompt、相同 schema、相同 timeout 和 retry 设置，只对该失败 chunk 做了一次补充重试，没有覆盖原始 round2 结果。

补充输出目录：

```text
chapter5_rag/outputs/round2_retry/deepseek/
```

输出文件：

| 文件 | 结果 |
|---|---|
| `raw_extractions_retry.jsonl` | 保存重试原始输出 |
| `kg_entities_retry.jsonl` | 空结果 |
| `kg_triples_retry.jsonl` | 空结果 |

补充重试结果：

| 指标 | 数值 |
|---|---:|
| 重试是否成功 | 否 |
| JSON 是否可解析 | 否 |
| 新增实体数 | 0 |
| 新增三元组数 | 0 |
| evidence 可追溯率 | 0.00% |
| 原始成功率 | 80.00% |
| after_retry 成功率 | 80.00% |

报告文件：

```text
chapter5_rag/eval/deepseek_retry_analysis.md
chapter5_rag/eval/deepseek_retry_metrics.json
chapter5_rag/eval/round2_after_retry_comparison.md
chapter5_rag/eval/round2_after_retry_extraction_eval_metrics.json
```

该实验说明：首次运行指标用于衡量模型稳定性，after_retry 指标用于衡量加入失败重试机制后的系统可用性，不能用 after_retry 替代首次运行结果。

## 12. 第五章三种 RAG 方案对比成果

第五章最终对比了三种方案：

| 方案 | 说明 |
|---|---|
| A_vector_rag | 纯向量 RAG，不使用知识图谱 |
| B_pangu_graph_rag | Pangu 抽取三元组 + 知识图谱 + 向量 RAG |
| C_deepseek_graph_rag | DeepSeek 抽取三元组 + 知识图谱 + 向量 RAG |

评测问题集：

```text
chapter5_rag/eval/qa_testset.json
```

测试问题数量：

```text
15
```

覆盖类型：

1. 概念定义类。
2. 工艺流程类。
3. 对比类。
4. 图纸资料类。
5. 质量控制类。
6. 表格数据类。

RAG 检索性能结果：

| 方案 | Top1 命中率 | Top3 命中率 | Top5 命中率 | 关键词覆盖率 | 平均检索耗时 |
|---|---:|---:|---:|---:|---:|
| A_vector_rag | 40.00% | 73.33% | 86.67% | 93.00% | 1.11 ms |
| B_pangu_graph_rag | 33.33% | 73.33% | 86.67% | 93.00% | 1.30 ms |
| C_deepseek_graph_rag | 33.33% | 73.33% | 86.67% | 93.00% | 1.37 ms |

说明：本次主要比较检索阶段性能，没有调用生成模型，因此平均生成耗时和答案长度记为 N/A。

图谱结构质量对比：

| 方案 | 实体数 | 三元组数 | 关系类型数 | 平均度数 | 最大连通子图比例 | 孤立实体比例 | 泛化关系比例 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pangu Graph-RAG | 120 | 81 | 43 | 1.3500 | 20.00% | 8.33% | 17.28% |
| DeepSeek Graph-RAG | 117 | 110 | 17 | 1.8803 | 52.14% | 9.40% | 24.55% |

成本对比：

| 方案 | 模型调用次数 | 输入 Token 估计 | 输出 Token 估计 | API 费用估计 | 存储大小 | 是否需要 GPU | 工程复杂度 |
|---|---:|---:|---:|---|---:|---|---:|
| A_vector_rag | 0 | 0 | 0 | 0 | 300.89 KB | 否 | 2 |
| B_pangu_graph_rag | 5 | 2372 | 6336 | N/A/self-hosted | 332.51 KB | 是 | 4 |
| C_deepseek_graph_rag | 5 | 2372 | 9438 | unknown | 334.72 KB | 否 | 3 |

相关报告：

```text
chapter5_rag/reports/graph_quality_report.md
chapter5_rag/reports/scheme_comparison_report.md
chapter5_rag/reports/final_eval_summary.md
chapter5_rag/eval/scheme_comparison_metrics.json
```

## 13. 第五章成果可复现命令

Pangu 第五章流程：

```powershell
python chapter5_rag\chapter5_pipeline.py chunk --max-chars 850 --overlap 100
python chapter5_rag\chapter5_pipeline.py extract --retries 2 --max-new-tokens 900 --sleep 0.1
python chapter5_rag\chapter5_pipeline.py build-graph --min-confidence 0.55
```

第五章向量库：

```powershell
python chapter5_rag\chapter5_vector.py --recreate
```

启动 Pangu Graph-RAG：

```powershell
uvicorn chapter5_rag.chapter5_app:app --host 127.0.0.1 --port 8092
```

DeepSeek 第五章流程：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
python chapter5_rag\deepseek_pipeline.py extract --retries 2 --sleep 0.1 --max-tokens 1800
python chapter5_rag\deepseek_pipeline.py build-graph --min-confidence 0.55
```

启动 DeepSeek Graph-RAG：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uvicorn chapter5_rag.deepseek_app:app --host 127.0.0.1 --port 8094
```

启动纯向量 RAG：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uvicorn chapter5_rag.vector_baseline_app:app --host 127.0.0.1 --port 8095
```

导入 Pangu 第五章 Neo4j 子图：

```powershell
python chapter5_rag\import_neo4j.py --clear-chapter5
```

导入 DeepSeek 第五章 Neo4j 子图：

```powershell
python chapter5_rag\import_deepseek_neo4j.py --clear-deepseek
```

生成图谱可视化数据：

```powershell
python chapter5_rag\build_visualization_data.py
```

知识抽取质量评测：

```powershell
python chapter5_rag\eval_extraction_quality.py
python chapter5_rag\compare_extraction_rounds.py
```

图谱结构质量与方案对比：

```powershell
python chapter5_rag\eval_graph_quality.py
python chapter5_rag\eval_scheme_comparison.py
```

DeepSeek 失败 chunk 补充重试：

```powershell
python chapter5_rag\retry_deepseek_round2_failed.py
```

## 14. 第五章 RAG 成果总结

第五章 RAG 已经形成了一个完整的、可独立运行的精细化实验系统。主要成果包括：

1. 整理第五章清洗文本。
2. 切分 29 个第五章 chunk。
3. 构建 Pangu 版本第五章图谱，包含 205 个实体和 257 条关系。
4. 构建 DeepSeek 版本第五章图谱，包含 192 个实体和 335 条关系。
5. 将第五章图谱以独立命名空间导入 Neo4j，不影响整本书图谱。
6. 建立第五章独立 Qdrant 向量库 `chapter5_rag_chunks`。
7. 实现 Pangu Graph-RAG、DeepSeek Graph-RAG 和纯向量 RAG 三套系统。
8. 实现多智能体执行链路和前端展示。
9. 实现第五章图谱可视化页面。
10. 构建 5 个 chunk、93 个实体、79 条三元组的人工 gold 标准集。
11. 完成 Pangu 与 DeepSeek 两轮知识抽取质量评测。
12. 完成 DeepSeek 失败样本补充重试分析。
13. 完成三种 RAG 方案的检索性能、图谱结构质量和成本对比。

第五章 RAG 的意义在于，它不仅是整本书系统的一个子集，而且是一个更精细、更可评测、更适合展示课程高分要求的实验闭环。它能够说明系统具备从文本清洗、知识抽取、图谱构建、向量检索、Graph-RAG 问答、多智能体协作到评测对比的完整能力。
