# DeepSeek 知识图谱与 RAG 对比管线

本目录用于使用 DeepSeek 强模型从同一本教材重新抽取知识三元组、构建独立图谱数据，并作为 ShipRAG/Pangu GraphRAG 的外部强模型 baseline。

## 运行

```powershell
Copy-Item deepseek\config.example.env deepseek\.env
# 填写 DEEPSEEK_API_KEY

python deepseek\extract_triples.py --all
python pangu\build_graph_data.py --raw deepseek\outputs\raw_extractions.jsonl --out-dir deepseek\outputs\graph
```

说明：DeepSeek 官方 API 当前用于 chat/completions，本项目仍复用现有 Qdrant 向量库作为教材文档检索层；DeepSeek baseline 的差异主要体现在三元组抽取图谱和最终答案生成模型。
