# 第五章 Graph-RAG 问答系统

本目录是面向《第五章 船体分段的装配》的独立 RAG 系统，不依赖整本书主 RAG 的 Neo4j/Qdrant 服务。

## 数据流程

1. `第五章.txt`：第五章清洗文本。
2. `data/chapter5_chunks.jsonl`：第五章文本块。
3. `outputs/raw_extractions.jsonl`：Pangu 远程模型抽取的实体和三元组原始结果。
4. `outputs/graph/entities.jsonl`：第五章实体表。
5. `outputs/graph/relations.jsonl`：第五章关系表。
6. `chapter5_app.py`：第五章本地图谱检索 + 教材检索 + Pangu 生成答案服务。

## 重新运行

```powershell
python chapter5_rag\chapter5_pipeline.py chunk --max-chars 850 --overlap 100
python chapter5_rag\chapter5_pipeline.py extract --retries 2 --max-new-tokens 900 --sleep 0.1
python chapter5_rag\chapter5_pipeline.py build-graph --min-confidence 0.55
uvicorn chapter5_rag.chapter5_app:app --host 127.0.0.1 --port 8092
```

## 当前图谱规模

详见 `outputs/graph/summary.json`。
