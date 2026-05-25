# Pangu 知识图谱抽取流水线

本目录用于基于远程部署的 openPangu 7B 服务，从已预处理的《中级船体装配工工艺学》文本块中抽取实体和知识三元组，并导入 Neo4j 形成知识图谱。

## 目录结构

- `config.example.env`：Pangu 与 Neo4j 连接配置模板。
- `prompts/kg_extraction_prompt.md`：实体识别和关系抽取提示词。
- `extract_triples.py`：调用 Pangu 逐块抽取实体和三元组，支持断点续跑。
- `build_graph_data.py`：清洗、归一化、去重，生成高连接度图谱数据。
- `import_neo4j.py`：清空 Neo4j 旧图谱并导入新图谱。
- `outputs/`：抽取和图谱数据输出目录。

## 运行步骤

1. 复制配置：

```powershell
Copy-Item pangu\config.example.env pangu\.env
```

2. 按你的 Neo4j 配置修改 `pangu\.env`。

3. 抽取整本书三元组：

```powershell
python pangu\extract_triples.py --all
```

4. 构建高质量图谱数据：

```powershell
python pangu\build_graph_data.py
```

5. 清空 Neo4j 并导入新图谱：

```powershell
python pangu\import_neo4j.py --clear
```

如果只想先清空旧图谱：

```powershell
python pangu\import_neo4j.py --clear-only
```

## 说明

抽取脚本会读取 `data/processed/ship_textbook_chunks.jsonl`。每个 chunk 的结果会立即写入 `pangu/outputs/raw_extractions.jsonl`，中途失败后再次运行会自动跳过已完成 chunk。
