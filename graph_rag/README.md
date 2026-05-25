# ShipRAG Graph RAG API

本目录实现基于 Neo4j 知识图谱和 Qdrant 向量库的混合 RAG 问答系统。

## 1. 配置

复制配置模板到项目根目录：

```powershell
Copy-Item graph_rag\.env.example .env
```

然后填写：

```env
NEO4J_PASSWORD=你的 Neo4j 密码
OPENAI_API_KEY=你的云雾 API Key
OPENAI_BASE_URL=https://yunwu.ai/v1
OPENAI_CHAT_MODEL=gpt-5.4-mini
```

真实 `.env` 已在 `.gitignore` 中排除，不会提交到远程仓库。

当前默认使用本地哈希向量跑通 Qdrant 检索，问答生成走云雾 OpenAI 兼容接口：

```env
EMBEDDING_PROVIDER=hash
OPENAI_EMBEDDING_DIM=384
```

## 2. 写入 Qdrant

确保 Qdrant 已启动：

```powershell
curl http://localhost:6333/collections
```

写入教材 chunk：

```powershell
python -m graph_rag.ingest.qdrant_ingest
```

可先小批量测试：

```powershell
python -m graph_rag.ingest.qdrant_ingest --limit 5
```

## 3. 启动 API

```powershell
uvicorn graph_rag.main:app --host 127.0.0.1 --port 8090
```

健康检查：

```powershell
curl http://127.0.0.1:8090/health
```

前端工作台：

```text
http://127.0.0.1:8090/
```

## 4. 问答

```powershell
curl -X POST http://127.0.0.1:8090/ask `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"激光经纬仪在船体装配中有什么用途？\",\"top_k\":6,\"graph_hops\":1}"
```

## 5. 图谱检索

```powershell
curl -X POST http://127.0.0.1:8090/graph/search `
  -H "Content-Type: application/json" `
  -d "{\"entity\":\"激光经纬仪\",\"hops\":2,\"limit\":50}"
```

## 6. 向量检索

```powershell
curl -X POST http://127.0.0.1:8090/vector/search `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"船体装配中激光经纬仪如何测量垂直度？\",\"top_k\":8}"
```
