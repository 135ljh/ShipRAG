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

## 待用户提供

完整 RAG 问答还需要：

```text
OPENAI_API_KEY
```

填入项目根目录 `.env` 后即可继续执行 Qdrant 入库和 `/ask` 问答测试。

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

由于 OpenAI API Key 尚未提供，以下功能代码已实现但还未做端到端实测：

1. OpenAI Embedding 生成。
2. Qdrant 全量 chunk 入库。
3. Qdrant 向量检索。
4. Graph + Vector 混合问答。
5. LLM 答案生成。

