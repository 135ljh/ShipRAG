# ShipRAG 图谱数据汇总

本目录统一整理项目中已经生成的四份知识图谱数据，便于课程报告、Neo4j 导入、图谱可视化和后续对比实验使用。

## 目录结构

```text
graph_data_exports/
├── whole_book/
│   ├── pangu/
│   │   ├── entities.jsonl
│   │   ├── relations.jsonl
│   │   ├── entities.csv
│   │   ├── relations.csv
│   │   └── summary.json
│   └── deepseek/
│       ├── entities.jsonl
│       ├── relations.jsonl
│       ├── entities.csv
│       ├── relations.csv
│       └── summary.json
└── chapter5/
    ├── pangu/
    │   ├── entities.jsonl
    │   ├── relations.jsonl
    │   └── summary.json
    └── deepseek/
        ├── entities.jsonl
        ├── relations.jsonl
        └── summary.json
```

## 四份图谱数据

| 图谱 | 来源目录 | 实体数 | 关系数 | 说明 |
|---|---|---:|---:|---|
| 全文 Pangu 图谱 | `pangu/outputs/graph/` | 1003 | 1747 | 使用自部署 Pangu 7B 对整本书抽取并后处理得到 |
| 全文 DeepSeek 图谱 | `deepseek/outputs/graph/` | 830 | 1450 | 使用 DeepSeek 对整本书抽取并后处理得到 |
| 第五章 Pangu 图谱 | `chapter5_rag/outputs/graph/` | 205 | 257 | 面向第五章“船体分段的装配”的 Pangu 独立图谱 |
| 第五章 DeepSeek 图谱 | `chapter5_rag/deepseek_outputs/graph/` | 192 | 335 | 面向第五章“船体分段的装配”的 DeepSeek 独立图谱 |

## 文件说明

### `entities.jsonl`

实体表，每行一个实体。常见字段包括：

- `id`：实体唯一标识；
- `name`：实体名称；
- `type`：实体类型；
- `definition`：实体定义或说明；
- `source_pages` / `source_page`：来源页码；
- `source_chunks` / `source_chunk`：来源文本块；
- `confidence`：置信度。

### `relations.jsonl`

关系表，每行一条图谱关系或三元组。常见字段包括：

- `head` / `head_id`：头实体；
- `relation`：关系类型；
- `tail` / `tail_id`：尾实体；
- `evidence`：原文证据；
- `source_pages` / `source_page`：来源页码；
- `source_chunks` / `source_chunk`：来源文本块；
- `confidence`：置信度。

### `entities.csv` / `relations.csv`

CSV 版本，主要用于表格查看、Neo4j 批量导入或报告中快速检查数据。当前全文 Pangu 和全文 DeepSeek 图谱均已整理 CSV；第五章图谱当前主要使用 JSONL。

### `summary.json`

图谱摘要文件，包含：

- raw rows；
- 实体数；
- 关系数；
- 孤立实体数；
- 实体类型分布；
- 关系类型分布；
- 高连接实体。

## 使用建议

1. 报告展示全文图谱时，优先使用 `whole_book/pangu/`，因为这是课程要求中“使用 Pangu 7B 构建整本书图谱”的主成果。
2. 对比不同模型抽取覆盖时，可使用 `whole_book/pangu/` 与 `whole_book/deepseek/`。
3. 展示精细化章节实验时，优先使用 `chapter5/pangu/` 和 `chapter5/deepseek/`。
4. 如果要导入 Neo4j，建议仍使用项目原始导入脚本：
   - 全文 Pangu：`python pangu/import_neo4j.py --clear`
   - 第五章 Pangu：`python chapter5_rag/import_neo4j.py --clear-chapter5`
   - 第五章 DeepSeek：`python chapter5_rag/import_deepseek_neo4j.py --clear-deepseek`

## 注意事项

- 本目录是图谱数据汇总副本，原始产物仍保留在各自模块目录中。
- 本目录不包含 API key、`.env` 文件和模型调用配置。
- 本目录只整理图谱实体、关系和摘要，不包含原始大模型响应 `raw_extractions.jsonl`。
