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
