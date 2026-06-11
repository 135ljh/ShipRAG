# DeepSeek baseline 与 Pangu Graph-RAG 对比评测报告

## 评测口径

- 评测集：`data\evaluation\deepseek_vs_pangu_eval_dataset.jsonl`。
- 样本数：200 条。
- 样本来源：从清洗后的教材 chunk 均匀采样生成，未使用 Pangu 或 DeepSeek 图谱关系生成问题。
- 对比对象：DeepSeek 抽取图谱作为强模型 baseline；Pangu 抽取图谱作为课程要求模型。
- 检索方式：同一套离线 Graph-RAG 检索器，同一份教材 chunk，只切换图谱文件。
- 说明：本轮评测聚焦图谱质量与证据召回，不使用手写 domain 预设问答规则。
- 读数说明：Context Precision/Recall 按“是否命中隐藏标准页码”计算，属于严格页码级指标；Graph Page Hit 衡量图谱事实是否覆盖标准页；Evidence Keyword Recall 衡量检索证据是否覆盖问题关键词。

## 核心指标对比

| 指标 | Pangu RAG | DeepSeek baseline | DeepSeek-Pangu |
|---|---:|---:|---:|
| Context Precision | 5.58% | 5.50% | -0.08pp |
| Context Recall | 33.00% | 32.50% | -0.50pp |
| Hit@K | 33.00% | 32.50% | -0.50pp |
| MRR | 17.77% | 17.71% | -0.06pp |
| NDCG | 21.73% | 21.57% | -0.16pp |
| Graph Page Hit | 84.00% | 84.50% | +0.50pp |
| Evidence Keyword Recall | 96.40% | 96.90% | +0.50pp |
| Extractive Answer Keyword Recall | 79.87% | 79.70% | -0.17pp |
| Answerable Rate | 88.50% | 88.50% | +0.00pp |

## 图谱结构对比

| 指标 | Pangu | DeepSeek baseline |
|---|---:|---:|
| Entities | 1003 | 830 |
| Relations | 1747 | 1450 |
| Isolated Entities | 33 | 0 |
| Relation Page Coverage | 186 | 185 |
| Avg Relation Confidence | 0.8082 | 0.8290 |

## 结论

- DeepSeek baseline 的 Answerable Rate 为 88.50%，Pangu 为 88.50%，说明强模型图谱在当前离线 Graph-RAG 口径下整体证据可用性更强或相当。
- DeepSeek 图谱孤立实体为 0，Pangu 为 33，可用于观察图谱连接紧密度。
- 两套系统的页码级 Context Precision 均不高，说明主要瓶颈仍在“从主题问题精确定位到教材页/chunk”，而不是最终答案格式。
- 两套系统的 Graph Page Hit 均超过 80%，说明图谱事实对教材主题覆盖较好，可作为 RAG 证据补充；后续应把图谱命中的页码更强地反馈给文档召回排序。
- 如果后续要进一步提升 Pangu RAG，优先优化实体规范化、同义词合并、关系证据页码对齐和图谱检索排序。

## 输出文件

- 明细结果：`docs\rag_design\evaluation\deepseek_vs_pangu\deepseek_vs_pangu_results.json`
- 评测数据集：`data\evaluation\deepseek_vs_pangu_eval_dataset.jsonl`
