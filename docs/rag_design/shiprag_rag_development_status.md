# ShipRAG RAG 问答系统开发进度

## 已完成

本轮已经开始按照 `方案.docx` 和 `docs/rag_design/shiprag_graph_rag_design.md` 落地开发 Graph RAG 问答系统。

新增工程目录：

```text
graph_rag/
```

已实现模块：

| 模块 | 文件 | 状态 |
|---|---|---|
| 配置管理 | `graph_rag/config.py` | 已完成 |
| Neo4j 客户端 | `graph_rag/db/neo4j_client.py` | 已完成 |
| Qdrant 客户端 | `graph_rag/db/qdrant_client.py` | 已完成 |
| OpenAI 封装 | `graph_rag/llm.py` | 已完成，等待 API Key |
| chunk 加载 | `graph_rag/ingest/chunk_loader.py` | 已完成 |
| Qdrant 入库脚本 | `graph_rag/ingest/qdrant_ingest.py` | 已完成，等待 API Key |
| 实体链接 | `graph_rag/rag/entity_linker.py` | 已完成，支持精确、包含和模糊匹配 |
| 图谱检索 | `graph_rag/retrievers/graph_retriever.py` | 已完成 |
| 向量检索 | `graph_rag/retrievers/vector_retriever.py` | 已完成，等待 Qdrant 入库 |
| 混合检索 | `graph_rag/retrievers/hybrid_retriever.py` | 已完成 |
| 上下文构建 | `graph_rag/rag/context_builder.py` | 已完成 |
| 答案生成 | `graph_rag/rag/answer_generator.py` | 已完成，等待 API Key |
| FastAPI API | `graph_rag/main.py` | 已完成 |
| 前端问答工作台 | `graph_rag/web/` | 已完成 |

## 已测试

无需 OpenAI API Key 的部分已经测试通过：

```text
python -m compileall graph_rag
```

FastAPI health：

```text
GET /health -> {"status": "ok"}
```

Neo4j 图谱检索：

```text
POST /graph/search
```

已能根据“激光经纬仪”检索到 Neo4j 中的实体和邻域关系。

Qdrant 向量库：

```text
collection: shiprag_chunks
chunk 数：230
```

当前已使用本地哈希 embedding 将 `ship_textbook_chunks.jsonl` 写入 Qdrant，便于在 OpenAI Key 不可用时先跑通检索闭环。

混合问答：

```text
POST /ask
```

已能完成：

1. 实体链接。
2. Neo4j 图谱检索。
3. Qdrant 文档检索。
4. 图谱事实和文档证据融合。
5. 答案生成 fallback。

前端页面：

```text
GET /
```

已实现管理后台风格的问答工作台，包含问答、图谱检索、向量检索三个视图。

## 待用户提供

完整 LLM 生成还需要可用的 OpenAI 兼容接口：

```text
OPENAI_API_KEY
OPENAI_BASE_URL
```

当前提供的 key 在官方 `https://api.openai.com/v1` 上返回 `invalid_api_key`。如果该 key 来自中转服务，需要同时提供对应的 `OPENAI_BASE_URL`。在此之前，系统使用本地哈希 embedding 和答案 fallback 保持链路可运行。

## 下一步运行顺序

1. 复制配置：

```powershell
Copy-Item graph_rag\.env.example .env
```

2. 填写 `.env`：

```env
NEO4J_PASSWORD=lineo4j123
OPENAI_API_KEY=你的 OpenAI API Key
```

3. 写入 Qdrant：

```powershell
python -m graph_rag.ingest.qdrant_ingest
```

4. 启动 API：

```powershell
uvicorn graph_rag.main:app --host 0.0.0.0 --port 8080
```

5. 调用问答接口：

```powershell
curl -X POST http://localhost:8080/ask `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"激光经纬仪在船体装配中有什么用途？\",\"top_k\":8,\"graph_hops\":2}"
```

## 当前限制

由于当前 OpenAI Key 无法通过官方接口认证，以下能力处于 fallback 或待切换状态：

1. OpenAI Embedding 生成暂未启用，当前使用本地哈希 embedding。
2. LLM 答案生成暂未启用，当前返回基于证据的 fallback 摘要。
3. 若提供可用的 `OPENAI_BASE_URL` 和 key，可直接切换回 OpenAI embedding 和 chat。
