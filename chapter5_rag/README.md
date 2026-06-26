# 第五章 Graph-RAG 问答系统

本目录是面向《第五章 船体分段的装配》的独立 RAG 系统，不依赖整本书主 RAG 的 Neo4j/Qdrant 服务。

## 数据流程

1. `第五章.txt`：第五章清洗文本。
2. `data/chapter5_chunks.jsonl`：第五章文本块。
3. `outputs/raw_extractions.jsonl`：Pangu 远程模型抽取的实体和三元组原始结果。
4. `outputs/graph/entities.jsonl`：第五章实体表。
5. `outputs/graph/relations.jsonl`：第五章关系表。
6. `chapter5_vector.py`：第五章 chunk 向量化并写入 Qdrant。
7. `chapter5_app.py`：第五章 Qdrant 向量检索 + 本地关键词检索 + 图谱检索 + Pangu 生成答案服务。
8. `multi_agent_design.md`：第五章多智能体 RAG 设计说明。

## 多智能体

当前第五章 RAG 已实现多智能体执行链路：PlannerAgent、VectorAgent、GraphAgent、FusionAgent、AnswerAgent、VerifierAgent。前端会展示 `AGENT TRACE`，后端 `/ask` 接口会在 `metadata.agent_trace` 中返回每个智能体的执行动作和耗时。

## 重新运行

```powershell
python chapter5_rag\chapter5_pipeline.py chunk --max-chars 850 --overlap 100
python chapter5_rag\chapter5_pipeline.py extract --retries 2 --max-new-tokens 900 --sleep 0.1
python chapter5_rag\chapter5_pipeline.py build-graph --min-confidence 0.55
python chapter5_rag\chapter5_vector.py --recreate
uvicorn chapter5_rag.chapter5_app:app --host 127.0.0.1 --port 8092
```

## 当前图谱规模

详见 `outputs/graph/summary.json`。

## 向量数据库

第五章 RAG 使用独立 Qdrant collection：`chapter5_rag_chunks`。系统优先连接 `QDRANT_URL`/`CHAPTER5_QDRANT_URL` 指向的 HTTP Qdrant 服务；如果本地 6333 未启动，会自动 fallback 到 `chapter5_rag/qdrant_storage/` 的 Qdrant embedded local 模式。该目录是运行产物，可通过 `python chapter5_rag\chapter5_vector.py --recreate` 重建。

注意：Qdrant embedded local 模式同一时间只能被一个 Python 进程打开。如果第五章 RAG 服务正在运行并占用 `qdrant_storage`，需要先停止服务，再重新执行向量入库命令。使用独立 Qdrant Server 时没有这个限制。

## Neo4j 独立存储

第五章知识图谱可以单独写入 Neo4j，并且不会影响整本书图谱。导入脚本为：

```powershell
python chapter5_rag\import_neo4j.py
```

脚本使用独立命名空间：

- 第五章节点标签：`:Chapter5Entity`
- 节点 id 前缀：`chapter5::`
- 关系属性：`scope = "chapter5"`

如果需要重导第五章图谱，只删除第五章子图，不清空整本书图谱：

```powershell
python chapter5_rag\import_neo4j.py --clear-chapter5
```

查看 Neo4j 中第五章子图规模：

```powershell
python chapter5_rag\import_neo4j.py --stats-only
```

Neo4j Browser 可视化查询：

```cypher
MATCH p=(n:Chapter5Entity)-[r {scope: "chapter5"}]->(m:Chapter5Entity)
RETURN p
LIMIT 80;
```

## DeepSeek 版第五章 RAG

本目录同时提供 DeepSeek 版第五章流程，不覆盖 Pangu 版产物。DeepSeek 输出目录为：

- `deepseek_outputs/raw_extractions.jsonl`：DeepSeek 抽取原始结果。
- `deepseek_outputs/graph/entities.jsonl`：DeepSeek 版实体表。
- `deepseek_outputs/graph/relations.jsonl`：DeepSeek 版关系表。
- `deepseek_outputs/graph/summary.json`：DeepSeek 版图谱摘要。

运行抽取与构图：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
python chapter5_rag\deepseek_pipeline.py extract --retries 2 --sleep 0.1 --max-tokens 1800
python chapter5_rag\deepseek_pipeline.py build-graph --min-confidence 0.55
```

启动 DeepSeek 版 RAG：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uvicorn chapter5_rag.deepseek_app:app --host 127.0.0.1 --port 8094
```

当前 DeepSeek 版第五章图谱规模：

- 原始抽取 chunk：29
- 失败 chunk：0
- 实体：192
- 关系：335
- 孤立实体：1

访问地址：

```text
http://127.0.0.1:8094/
```

DeepSeek 版图谱也可以独立导入 Neo4j，不影响 Pangu 版第五章图谱和整本书图谱：

```powershell
python chapter5_rag\import_deepseek_neo4j.py --clear-deepseek
```

脚本使用独立命名空间：

- 节点标签：`:Chapter5DeepSeekEntity`
- 节点 id 前缀：`chapter5_deepseek::`
- 关系属性：`scope = "chapter5_deepseek"`

查看 Neo4j 中 DeepSeek 第五章子图规模：

```powershell
python chapter5_rag\import_deepseek_neo4j.py --stats-only
```

Neo4j Browser 查看 DeepSeek 完整图谱：

```cypher
MATCH p=(n:Chapter5DeepSeekEntity)-[r {scope: "chapter5_deepseek"}]->(m:Chapter5DeepSeekEntity)
RETURN p;
```

## 纯向量 RAG 基线方案

为了和知识图谱增强 RAG 做对照，本目录新增纯向量 RAG 基线服务。该方案不读取、不构建、不使用任何知识图谱，只依赖第五章文本块的向量检索结果生成答案。

特点：

- 不使用 `outputs/graph/`。
- 不使用 `deepseek_outputs/graph/`。
- `linked_entities` 固定为空。
- `evidence.graph` 固定为空。
- 只返回文本块证据 `evidence.documents`。
- 执行链路为 `VectorRetriever -> AnswerGenerator -> BaselineVerifier`。

启动命令：

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uvicorn chapter5_rag.vector_baseline_app:app --host 127.0.0.1 --port 8095
```

访问地址：

```text
http://127.0.0.1:8095/
```

该基线适合作为后续评估中的对比项，用来衡量“知识图谱增强”相对于“仅向量检索”的提升。
