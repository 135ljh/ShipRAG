# ShipRAG Graph RAG 问答系统设计方案

## 1. 设计目标

本系统基于已经构建好的船体装配知识图谱，进一步设计一个 Graph RAG + Vector RAG 混合问答系统。系统目标是让用户能够用自然语言提问，并基于 Neo4j 中的结构化图谱事实与 Qdrant 中的教材原文证据生成可追溯答案。

核心链路如下：

```text
用户问题
↓
问题理解与实体链接
↓
Neo4j 图谱检索
↓
Qdrant 向量检索
↓
图谱事实与文档证据融合
↓
上下文构建
↓
OpenAI LLM 生成答案
↓
答案引用与证据校验
↓
返回答案、图谱路径、文档来源
```

本系统不是单纯把问题丢给 LLM，而是要求 LLM 只基于检索到的图谱事实和文档证据回答，从而降低幻觉，提高答案可解释性。

## 2. 当前基础

当前项目已经完成：

| 模块 | 当前状态 |
|---|---|
| PDF 预处理 | 已完成，192 页 OCR 与清洗 |
| 文本切片 | 已完成，生成 `ship_textbook_chunks.jsonl` |
| Pangu 三元组抽取 | 已完成，最终成功覆盖率 95.1% |
| 知识图谱构建 | 已完成，规范化实体 1003，关系 1747 |
| Neo4j 导入 | 已完成，节点 1003，关系 1700 |
| Qdrant | 用户已安装并启动 |
| OpenAI API Key | 用户后续提供 |

已存在的重要文件：

```text
data/processed/ship_textbook_chunks.jsonl
pangu/outputs/graph/entities.jsonl
pangu/outputs/graph/relations.jsonl
pangu/outputs/raw_extractions.jsonl
```

Neo4j 中当前图谱规模：

```text
节点数：1003
关系数：1700
```

## 3. 系统总体架构

建议采用以下技术栈：

| 组件 | 技术选型 |
|---|---|
| Web/API 后端 | FastAPI |
| 图数据库 | Neo4j |
| 向量数据库 | Qdrant |
| Embedding | OpenAI `text-embedding-3-small` 或 `text-embedding-3-large` |
| LLM | OpenAI Chat Model，例如 `gpt-4.1-mini` 或后续指定模型 |
| 文档数据源 | `data/processed/ship_textbook_chunks.jsonl` |
| 图谱数据源 | Neo4j 已导入图谱 |
| 配置管理 | `.env` |

系统模块：

```text
graph_rag/
├── config.py
├── main.py
├── db/
│   ├── neo4j_client.py
│   └── qdrant_client.py
├── ingest/
│   ├── chunk_loader.py
│   ├── embedder.py
│   └── qdrant_writer.py
├── retrievers/
│   ├── graph_retriever.py
│   ├── vector_retriever.py
│   └── hybrid_retriever.py
├── rag/
│   ├── entity_linker.py
│   ├── query_planner.py
│   ├── context_builder.py
│   ├── answer_generator.py
│   └── answer_verifier.py
├── schemas/
│   ├── request.py
│   └── response.py
└── prompts/
    ├── answer_prompt.txt
    └── verifier_prompt.txt
```

## 4. 数据设计

### 4.1 Neo4j 图谱数据

Neo4j 负责存储结构化领域知识，包括：

- 船体构件
- 工艺对象
- 工艺过程
- 工序操作
- 工具设备
- 测量指标
- 质量要求
- 缺陷与修理
- 章节知识单元

节点统一具有以下属性：

```json
{
  "id": "Component_外板",
  "name": "外板",
  "type": "Component",
  "definition": "",
  "source_pages": [120, 121],
  "source_chunks": ["shiprag_p120_00138"],
  "confidence": 0.82
}
```

关系示例：

```text
(激光经纬仪)-[:MEASURES]->(垂直度)
(船体放样)-[:PROVIDES_BASIS_FOR]->(船体装配)
(底部分段)-[:ASSEMBLED_WITH]->(舷侧分段)
(第五章船体分段的装配)-[:CONTAINS]->(双层底分段)
```

Neo4j 适合回答：

- 某个工具用于什么？
- 某个分段和哪些构件有关？
- 某个工艺过程有哪些前后关系？
- 某个实体在图谱中的一跳/两跳邻域是什么？
- 两个实体之间有什么路径？

### 4.2 Qdrant 向量数据

Qdrant 负责存储教材原文 chunk 的向量，用于提供语义证据。

Collection 名称建议：

```text
shiprag_chunks
```

如果使用 OpenAI `text-embedding-3-small`，向量维度为 1536。若使用 `text-embedding-3-large`，向量维度为 3072。

Qdrant payload 设计：

```json
{
  "chunk_id": "shiprag_p008_00008",
  "source": "中级船体装配工工艺学_11934890.pdf",
  "page_start": 8,
  "page_end": 8,
  "chapter_hint": "第一章工艺基础及相关工种知识",
  "text": "激光经纬仪是船厂广泛使用的精密光学测量仪器...",
  "entities": ["激光经纬仪", "垂直度", "船体建造"],
  "entity_ids": ["ToolEquipment_激光经纬仪", "Measurement_垂直度"]
}
```

Qdrant 适合回答：

- 教材原文怎么描述某个概念？
- 某个工艺步骤的详细说明是什么？
- 某个工具的使用场景有哪些？
- 某个质量要求在原文中有哪些依据？

## 5. 核心问答流程

### 5.1 用户提问

示例：

```text
激光经纬仪在船体装配中可以测量哪些指标？
```

### 5.2 问题理解

系统识别：

```json
{
  "intent": "tool_usage_query",
  "entities": ["激光经纬仪"],
  "target": "Measurement",
  "need_graph": true,
  "need_vector": true
}
```

第一版可以不使用 LLM 做复杂规划，而采用规则策略：

1. 从 Neo4j 实体名称中做精确匹配。
2. 若命中实体，则执行一跳/两跳图谱查询。
3. 使用问题原文和图谱实体名称增强向量检索。
4. 合并证据后交给 LLM 回答。

### 5.3 实体链接

实体链接目标是把用户问题中的自然语言实体映射到 Neo4j 节点。

第一版实体链接策略：

1. 精确匹配 `name`。
2. 包含匹配，例如问题中包含“激光经纬仪”。
3. 按实体名称长度排序，优先匹配更长实体。

后续可扩展：

1. 别名匹配。
2. 拼写/OCR 变体匹配。
3. 向量相似度匹配。
4. LLM 消歧。

### 5.4 Neo4j 图谱检索

图谱检索返回结构化事实和图谱路径。

一跳邻域查询：

```cypher
MATCH p=(n:Entity {id: $entity_id})-[r]-(m:Entity)
RETURN p
LIMIT 50
```

两跳邻域查询：

```cypher
MATCH p=(n:Entity {id: $entity_id})-[*1..2]-(m:Entity)
RETURN p
LIMIT 100
```

关键词实体查询：

```cypher
MATCH (n:Entity)
WHERE n.name CONTAINS $keyword
RETURN n
LIMIT 20
```

图谱事实统一转换为文本：

```text
激光经纬仪 --测量指标--> 垂直度
激光经纬仪 --用于--> 船体建造测量
```

### 5.5 Qdrant 向量检索

向量检索流程：

```text
用户问题
↓
OpenAI Embedding
↓
Qdrant top-k 检索
↓
返回相关教材 chunk
```

如果实体链接命中 Neo4j 实体，则增强 query：

```text
原问题 + 命中实体名称 + 邻接实体名称
```

例如：

```text
激光经纬仪 在船体装配中 测量 指标 垂直度 水平度 直线度
```

第一版 top-k 建议：

```text
top_k = 8
```

### 5.6 混合检索

混合检索合并两类证据：

1. Graph Evidence：来自 Neo4j 的三元组和路径。
2. Document Evidence：来自 Qdrant 的教材原文 chunk。

统一证据结构：

```json
{
  "type": "graph",
  "content": "激光经纬仪 --measures--> 垂直度",
  "source": "neo4j",
  "score": 0.95,
  "path": "(激光经纬仪)-[:MEASURES]->(垂直度)"
}
```

```json
{
  "type": "document",
  "content": "激光经纬仪是船厂广泛使用的精密光学测量仪器...",
  "source": "中级船体装配工工艺学_11934890.pdf",
  "page": 8,
  "chunk_id": "shiprag_p008_00008",
  "score": 0.88
}
```

### 5.7 上下文构建

上下文分为三部分：

```text
【知识图谱事实】
1. 激光经纬仪 --measures--> 垂直度。
2. 激光经纬仪 --used_for--> 船体建造测量。

【教材原文证据】
1. 第 8 页：激光经纬仪是船厂广泛使用的精密光学测量仪器...
2. 第 8 页：形成铅垂面测结构垂直度...

【回答要求】
只基于以上证据回答。
如果证据不足，请回答“根据当前知识库无法确定”。
回答必须包含结论、依据和引用。
```

### 5.8 LLM 答案生成

答案生成 Prompt：

```text
你是一个严谨的船体装配知识图谱问答助手。
请只基于给定的知识图谱事实和教材原文证据回答用户问题。
不要使用外部知识。
如果证据不足，请回答“根据当前知识库无法确定”。
回答必须包含“结论”“依据”“引用”。

用户问题：
{question}

知识图谱事实：
{graph_facts}

教材原文证据：
{document_evidence}
```

输出格式：

```text
结论：
...

依据：
1. ...
2. ...

引用：
- 图谱路径：...
- 文档：第 x 页，chunk_id=...
```

## 6. API 设计

推荐使用 FastAPI。

### 6.1 问答接口

```text
POST /ask
```

请求：

```json
{
  "question": "激光经纬仪在船体装配中可以测量哪些指标？",
  "top_k": 8,
  "graph_hops": 2
}
```

返回：

```json
{
  "answer": "激光经纬仪可用于测量结构垂直度、直线度等指标...",
  "evidence": {
    "graph": [
      {
        "fact": "激光经纬仪 --measures--> 垂直度",
        "path": "(激光经纬仪)-[:MEASURES]->(垂直度)"
      }
    ],
    "documents": [
      {
        "chunk_id": "shiprag_p008_00008",
        "page": 8,
        "content": "激光经纬仪是船厂广泛使用的精密光学测量仪器..."
      }
    ]
  },
  "metadata": {
    "retrieval_mode": "graph_vector_hybrid",
    "linked_entities": ["激光经纬仪"]
  }
}
```

### 6.2 图谱检索接口

```text
POST /graph/search
```

请求：

```json
{
  "entity": "胎架",
  "hops": 2,
  "limit": 50
}
```

### 6.3 向量检索接口

```text
POST /vector/search
```

请求：

```json
{
  "query": "船体分段装配中胎架有什么作用？",
  "top_k": 8
}
```

## 7. Qdrant 建库与写入设计

### 7.1 Collection

建议 collection：

```text
shiprag_chunks
```

如果使用 `text-embedding-3-small`：

```text
vector_size = 1536
distance = cosine
```

如果使用 `text-embedding-3-large`：

```text
vector_size = 3072
distance = cosine
```

### 7.2 写入数据来源

直接使用：

```text
data/processed/ship_textbook_chunks.jsonl
```

每条 chunk 写入 Qdrant 的 payload：

```json
{
  "chunk_id": "shiprag_p008_00008",
  "source": "中级船体装配工工艺学_11934890.pdf",
  "page_start": 8,
  "page_end": 8,
  "chapter_hint": "第一章工艺基础及相关工种知识",
  "text": "激光经纬仪是船厂广泛使用的精密光学测量仪器..."
}
```

后续可以进一步把 Neo4j 命中的实体写入 payload 的 `entities` 和 `entity_ids` 字段，增强图谱与向量库的关联。

## 8. 配置设计

建议新增 `.env` 配置：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=你的密码
NEO4J_DATABASE=neo4j

QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=shiprag_chunks

OPENAI_API_KEY=后续填写
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

注意：真实 `.env` 不应提交到 GitHub，只提交 `.env.example`。

## 9. 开发阶段规划

### 第一阶段：最小 Graph QA

目标：不依赖 Qdrant，只使用 Neo4j + LLM 回答。

任务：

1. 连接 Neo4j。
2. 实现实体名称匹配。
3. 查询实体一跳/两跳邻域。
4. 将图谱路径转换为文本证据。
5. 调用 LLM 生成带依据答案。

### 第二阶段：Qdrant 文档检索

目标：把教材 chunk 写入 Qdrant，实现语义检索。

任务：

1. 读取 `ship_textbook_chunks.jsonl`。
2. 调用 OpenAI Embedding。
3. 创建 Qdrant collection。
4. 写入 chunk 向量和 payload。
5. 实现 `/vector/search`。

### 第三阶段：Graph + Vector Hybrid RAG

目标：融合 Neo4j 图谱事实与 Qdrant 文档证据。

任务：

1. 实体链接。
2. Neo4j 图谱检索。
3. Qdrant 向量检索。
4. 候选证据合并与去重。
5. 上下文构建。
6. LLM 生成答案和引用。

### 第四阶段：答案校验与评测

目标：降低幻觉并评估系统质量。

任务：

1. 判断答案中的实体是否出现在证据中。
2. 判断答案中的关系是否有图谱路径支持。
3. 判断引用 chunk 是否真实存在。
4. 无证据时拒答。
5. 准备测试问题集，统计检索命中率、答案准确率、引用准确率。

## 10. 评测指标

建议评测：

| 指标 | 说明 |
|---|---|
| 实体链接准确率 | 用户问题中的实体是否正确匹配 Neo4j 节点 |
| 图谱路径命中率 | 检索到的图谱路径是否支持答案 |
| 向量检索命中率 | Qdrant top-k 是否包含正确文档证据 |
| 答案准确率 | 生成答案是否正确 |
| 引用准确率 | 引用页码、chunk、图谱路径是否真实有效 |
| 幻觉率 | 答案中无证据支持内容比例 |
| 拒答正确率 | 证据不足时是否正确拒答 |
| 响应时间 | 平均问答耗时 |

测试样例：

```json
{
  "question": "激光经纬仪在船体装配中有什么用途？",
  "expected_entities": ["激光经纬仪"],
  "expected_evidence_types": ["graph", "document"],
  "expected_answer_keywords": ["测量", "画线", "垂直度"]
}
```

## 11. 最终落地版本

最推荐的 ShipRAG 落地版本是：

```text
Neo4j 图谱
+ Qdrant 向量库
+ OpenAI Embedding
+ OpenAI Chat Model
+ FastAPI
+ Graph Retriever
+ Vector Retriever
+ Hybrid Retriever
+ Context Builder
+ Answer Generator
+ Evidence Citation
```

该版本能够体现课程高分要求中的三个关键点：

1. 基于 openPangu 7B 抽取整本书知识三元组并形成图谱。
2. 使用 Neo4j 管理和可视化知识图谱。
3. 基于图谱和原始文本证据设计 RAG 问答系统。

