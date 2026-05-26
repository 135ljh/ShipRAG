# ShipRAG RAG 问答系统开发进度

## 已完成

本轮已经按 `方案.docx` 和 `docs/rag_design/shiprag_graph_rag_design.md` 落地开发 Graph RAG 问答系统，新增工程目录：

```text
graph_rag/
```

已实现模块：

| 模块 | 文件 | 状态 |
|---|---|---|
| 配置管理 | `graph_rag/config.py` | 已完成 |
| Neo4j 客户端 | `graph_rag/db/neo4j_client.py` | 已完成 |
| Qdrant 客户端 | `graph_rag/db/qdrant_client.py` | 已完成 |
| OpenAI 兼容接口封装 | `graph_rag/llm.py` | 已完成，支持云雾 API |
| chunk 加载 | `graph_rag/ingest/chunk_loader.py` | 已完成 |
| Qdrant 入库脚本 | `graph_rag/ingest/qdrant_ingest.py` | 已完成 |
| 实体链接 | `graph_rag/rag/entity_linker.py` | 已完成，支持精确、包含和模糊匹配 |
| 图谱检索 | `graph_rag/retrievers/graph_retriever.py` | 已完成 |
| 向量检索 | `graph_rag/retrievers/vector_retriever.py` | 已完成 |
| 混合检索 | `graph_rag/retrievers/hybrid_retriever.py` | 已完成 |
| 上下文构建 | `graph_rag/rag/context_builder.py` | 已完成 |
| 答案生成 | `graph_rag/rag/answer_generator.py` | 已完成 |
| FastAPI API | `graph_rag/main.py` | 已完成 |
| 前端问答工作台 | `graph_rag/web/` | 已完成 |

## 已验证

代码编译：

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

当前使用本地哈希 embedding 将 `ship_textbook_chunks.jsonl` 写入 Qdrant，保证在第三方 embedding 接口不可用时仍可跑通检索闭环。

混合问答：

```text
POST /ask
```

已能完成：

1. 实体链接。
2. Neo4j 图谱检索。
3. Qdrant 文档检索。
4. 图谱事实和文档证据融合。
5. 调用云雾 OpenAI 兼容接口生成答案。
6. 对“这本书讲什么”“这本书有多少章”“目录是什么”等基础元信息问题进行快速回答。
7. 对重复问题进行内存缓存，减少重复调用大模型的等待时间。

示例问题：

```text
激光经纬仪在船体装配中有什么用途？
```

系统能够返回结论、依据、教材原文引用和知识图谱事实引用。

基础问题示例：

```text
这本书有多少章？
```

系统直接使用教材内容简介和目录信息回答“全书共分 7 章”，无需调用大模型。

前端页面：

```text
GET /
```

已实现管理后台风格的问答工作台，包含问答、图谱检索、向量检索三个视图。

## 本地配置

根目录 `.env` 使用本地私有配置，不提交到 Git：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=你的 Neo4j 密码
NEO4J_DATABASE=neo4j

QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=shiprag_chunks

OPENAI_API_KEY=你的云雾 API Key
OPENAI_BASE_URL=https://yunwu.ai/v1
OPENAI_CHAT_MODEL=gpt-5.4-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_PROVIDER=hash
OPENAI_EMBEDDING_DIM=384

SHIPRAG_CHUNKS_PATH=data/processed/ship_textbook_chunks.jsonl
```

说明：当前 `EMBEDDING_PROVIDER=hash`，表示 Qdrant 使用本地哈希向量。这样做的好处是避免第三方 embedding 端点或模型名称不稳定影响系统演示；问答生成已经使用云雾 API。

## 运行顺序

1. 确认 Neo4j 和 Qdrant 已启动。

2. 写入 Qdrant：

```powershell
python -m graph_rag.ingest.qdrant_ingest
```

3. 启动 API：

```powershell
uvicorn graph_rag.main:app --host 127.0.0.1 --port 8090
```

4. 打开前端：

```text
http://127.0.0.1:8090/
```

5. 调用问答接口：

```powershell
curl -X POST http://127.0.0.1:8090/ask `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"激光经纬仪在船体装配中有什么用途？\",\"top_k\":6,\"graph_hops\":1}"
```
