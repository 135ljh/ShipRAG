# Pangu 知识抽取质量评测报告

## 评测对象

- Pangu 原始抽取文件：`pangu\outputs\raw_extractions.jsonl`。
- Pangu 图谱实体文件：`pangu\outputs\graph\entities.jsonl`。
- Pangu 图谱关系文件：`pangu\outputs\graph\relations.jsonl`。
- 参考 baseline：`deepseek` 图谱，用于观察重合度，不作为绝对标准答案。

## 抽取完成度

| 指标 | 数值 |
|---|---:|
| Raw rows | 224 |
| Success rows | 224 |
| Failed rows | 0 |
| Rows With Historical Error Marker | 11 |
| Success Rate | 100.00% |
| Raw Entities | 846 |
| Raw Triples | 762 |
| Avg Entities / Chunk | 3.78 |
| Avg Triples / Chunk | 3.40 |

## 实体质量

| 指标 | Pangu | DeepSeek baseline |
|---|---:|---:|
| Unique Entities | 1003 | 830 |
| Valid Type Rate | 100.00% | 100.00% |
| With Definition Rate | 60.92% | 86.14% |
| With Source Page Rate | 99.90% | 99.88% |
| Duplicate Name Rate | 9.97% | 6.51% |
| Avg Confidence | 0.8292 | 0.8705 |

## 关系质量

| 指标 | Pangu | DeepSeek baseline |
|---|---:|---:|
| Unique Relations | 1747 | 1450 |
| Valid Relation Type Rate | 100.00% | 100.00% |
| With Evidence Rate | 100.00% | 100.00% |
| With Source Page Rate | 100.00% | 100.00% |
| Evidence Grounded Rate | 39.27% | 36.97% |
| Endpoint Linked Rate | 97.31% | 100.00% |
| Endpoint In Evidence Avg | 0.5544 | 0.5480 |
| Duplicate Relation Rate | 5.09% | 3.03% |
| Self Loop Rate | 0.00% | 0.00% |
| Avg Confidence | 0.8082 | 0.8290 |

## 图谱连通性

| 指标 | Pangu | DeepSeek baseline |
|---|---:|---:|
| Isolated Entities | 33 | 0 |
| Isolation Rate | 3.29% | 0.00% |
| Connected Components | 35 | 1 |
| Largest Component Ratio | 96.51% | 100.00% |
| Small Components | 34 | 0 |

## 与 DeepSeek baseline 的重合度

| 指标 | 数值 |
|---|---:|
| Entity Name Overlap | 364 |
| Entity Precision vs Reference | 40.31% |
| Entity Recall vs Reference | 46.91% |
| Relation Exact Overlap | 426 |
| Relation Precision vs Reference | 25.69% |
| Relation Recall vs Reference | 30.30% |

## 结论

- Pangu 抽取成功率为 100.00%，说明补抽后整本书抽取流程已经跑通。
- Pangu 生成 1003 个实体、1747 条关系，规模高于 DeepSeek baseline，但存在 33 个孤立实体，连接紧密度弱于 DeepSeek baseline。
- Pangu 关系类型合法率、证据字段完整率和端点链接率均为 97.31% 以上，说明结构化格式基本可靠。
- Evidence Grounded Rate 为 39.27%，表示约四成关系证据能被脚本严格回溯到教材 chunk；未完全达到 100% 的原因主要是证据经过省略号、改写或 OCR 差异处理。
- 与 DeepSeek baseline 的精确关系重合度较低，这不一定表示错误，因为两个模型可能抽取不同粒度的三元组；更适合把 DeepSeek 作为强参考，而不是唯一标准答案。

## 建议

- 对 Pangu 图谱做实体规范化和同义词合并，重点处理章节名、OCR 乱码实体、同一工具/构件的多种写法。
- 减少 `contains` 类粗粒度章节包含关系在检索排序中的权重，提高 `uses_tool`、`precedes`、`controls`、`checks` 等工艺关系权重。
- 对孤立实体进行二次关系补抽，优先补齐高频构件、工具、测量项与工艺步骤之间的关系。

## 输出文件

- 详细 JSON：`docs\kg_design\evaluation\pangu_kg_extraction_quality.json`
