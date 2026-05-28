# ShipRAG RAG 评估报告

本报告按照 `RAG评估体系.docx` 中的三层指标体系重新计算：检索层、生成层、系统层。

- 评估样本数：17
- 任务完成率：100.00%
- 路由准确率：100.00%
- 噪声鲁棒性：100.00%
- 负样本拒绝率：100.00%

## 核心指标

| 层级 | 指标 | 分数 |
|---|---|---:|
| 检索层 | Context Precision | 75.98% |
| 检索层 | Context Recall | 94.12% |
| 检索层 | Hit@K | 100.00% |
| 检索层 | MRR | 97.06% |
| 检索层 | NDCG | 96.63% |
| 生成层 | Faithfulness/Groundedness | 100.00% |
| 生成层 | Answer Relevance | 97.65% |
| 生成层 | Answer Completeness | 97.65% |
| 生成层 | Answer Correctness | 99.22% |
| 生成层 | Fluency | 100.00% |
| 系统层 | Context Utilization | 68.14% |
| 系统层 | Task Completion | 100.00% |
| 系统层 | Negative Rejection | 100.00% |
| 系统层 | Noise Robustness | 100.00% |

## 质量辅助指标

- 关键词覆盖率均值：97.65%
- 期望页命中率：100.00%
- 引用完整率：100.00%
- 答案结构完整率：100.00%
- 无法确定率：11.76%
- 乱码率：0.00%
- Markdown 粗体符号率：0.00%

## 响应耗时

| 指标 | 平均 | P50 | P90 | P95 | 最大 |
|---|---:|---:|---:|---:|---:|
| 首次 wall time/ms | 1060.5 | 1.69 | 2782.438 | 3445.99 | 5554.15 |
| 系统 reported/ms | 1057.68 | 0.04 | 2777.696 | 3440.652 | 5549.98 |
| 缓存 wall time/ms | 2.85 | 1.92 | 5.214 | - | 7.38 |

## 分类结果

| 类别 | 样本数 | 通过率 | Context Precision | Context Recall | Faithfulness | Answer Relevance | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| book_profile | 2 | 100.00% | 75.00% | 75.00% | 100.00% | 100.00% | 2.79 |
| domain_qa | 9 | 100.00% | 92.59% | 100.00% | 100.00% | 100.00% | 1.52 |
| graph_rag | 4 | 100.00% | 27.08% | 87.50% | 100.00% | 90.00% | 3172.94 |
| negative | 2 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2658.73 |

## 明细

| ID | 类别 | 通过 | 模式 | C.Precision | C.Recall | MRR | NDCG | Faithfulness | Relevance | 耗时/ms |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| book_chapter_count | book_profile | 是 | multi_agent_book_profile | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4.21 |
| book_summary | book_profile | 是 | multi_agent_book_profile | 50.00% | 50.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.38 |
| domain_block_prepare | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.31 |
| domain_rib_frame | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.69 |
| domain_slipway_vs_block | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.28 |
| domain_total_quality | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.26 |
| domain_measure_tools | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.12 |
| domain_structure_code | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0.9 |
| domain_welding_deformation_4_1 | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0.94 |
| domain_welding_deformation_6_2 | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0.91 |
| graph_laser_use | graph_rag | 是 | multi_agent_graph_rag | 25.00% | 100.00% | 100.00% | 100.00% | 100.00% | 80.00% | 5554.15 |
| graph_lofting_tasks | graph_rag | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 2918.95 |
| graph_baseline_marking | graph_rag | 是 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 100.00% | 2680.53 |
| graph_block_positioning | domain_qa | 是 | multi_agent_domain_qa | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4.23 |
| graph_segment_modes | graph_rag | 是 | multi_agent_graph_rag | 33.33% | 50.00% | 100.00% | 91.97% | 100.00% | 80.00% | 1538.15 |
| negative_mars_population | negative | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2626.04 |
| negative_reactor_repair | negative | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2691.43 |

## 说明

本评估根据 `RAG评估体系.docx` 中的指标进行工程化近似实现，不额外调用 LLM-as-Judge。
Context Precision、Context Recall、MRR、NDCG 基于期望页码与返回文档页码计算。
Faithfulness、Answer Relevance、Completeness、Correctness、Fluency 采用证据命中、引用、关键词覆盖、格式与乱码检测等规则近似计算。
Graph RAG 类问题会调用云雾模型，因此耗时显著高于 book_profile 和 domain_qa 快速路径。