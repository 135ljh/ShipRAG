# ShipRAG RAG 评估报告

本报告按照 `RAG评估体系.docx` 中的三层指标体系重新计算：检索层、生成层、系统层。

- 评估样本数：43
- 任务完成率：44.19%
- 路由准确率：100.00%
- 噪声鲁棒性：100.00%
- 负样本拒绝率：100.00%
- 严格非预设样本数：33
- 严格非预设通过率：27.27%

## 核心指标

| 层级 | 指标 | 分数 |
|---|---|---:|
| 检索层 | Context Precision | 38.37% |
| 检索层 | Context Recall | 53.88% |
| 检索层 | Hit@K | 65.12% |
| 检索层 | MRR | 55.70% |
| 检索层 | NDCG | 57.62% |
| 生成层 | Faithfulness/Groundedness | 86.82% |
| 生成层 | Answer Relevance | 53.18% |
| 生成层 | Answer Completeness | 53.18% |
| 生成层 | Answer Correctness | 71.47% |
| 生成层 | Fluency | 100.00% |
| 系统层 | Context Utilization | 29.85% |
| 系统层 | Task Completion | 44.19% |
| 系统层 | Negative Rejection | 100.00% |
| 系统层 | Noise Robustness | 100.00% |

## 质量辅助指标

- 关键词覆盖率均值：53.18%
- 期望页命中率：65.12%
- 引用完整率：100.00%
- 答案结构完整率：100.00%
- 无法确定率：48.84%
- 乱码率：0.00%
- Markdown 粗体符号率：0.00%

## 响应耗时

| 指标 | 平均 | P50 | P90 | P95 | 最大 |
|---|---:|---:|---:|---:|---:|
| 首次 wall time/ms | 2813.3 | 2945.03 | 4178.3 | 7410.829 | 10492.24 |
| 系统 reported/ms | 2808.81 | 2939.1 | 4173.218 | 7406.408 | 10486.63 |
| 缓存 wall time/ms | 0.0 | 0.0 | 0.0 | - | 0.0 |

## 分类结果

| 类别 | 样本数 | 通过率 | Context Precision | Context Recall | Faithfulness | Answer Relevance | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| book_profile | 2 | 100.00% | 75.00% | 75.00% | 100.00% | 100.00% | 3.31 |
| domain_qa | 8 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.65 |
| graph_rag | 29 | 17.24% | 10.35% | 33.33% | 80.46% | 31.72% | 3746.85 |
| negative | 4 | 100.00% | 100.00% | 100.00% | 100.00% | 91.67% | 3073.35 |

## 预设样本隔离

为避免把 `domain_qa.py` 中的规则问答当作真实 RAG 能力，本次评估把样本拆成两组：

| 子集 | 样本数 | 通过率 | Context Precision | Context Recall | Hit@K | Faithfulness | Answer Relevance | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| strict_non_preset | 33 | 27.27% | 21.21% | 41.41% | 54.55% | 82.83% | 38.99% | 3665.22 |
| preset_or_rule_based | 10 | 100.00% | 95.00% | 95.00% | 100.00% | 100.00% | 100.00% | 1.98 |

## 评估结论

- 严格非预设样本通过率为 27.27%，明显低于规则路径，说明此前只用少量 `domain_qa.py` 预设题无法代表真实 RAG 能力。
- 非预设样本 Hit@K 为 54.55%，Context Precision 为 21.21%，主要瓶颈在教材证据召回和页码命中，而不是答案格式。
- 生成层 Faithfulness 为 82.83%，说明在检索证据不足时系统倾向于保守拒答，降低了幻觉风险，但也导致大量教材内问题回答为“无法确定”。
- 后续优化重点应放在：重建 Qdrant 切片与元数据、增强章节/页码/术语索引、把 Neo4j 实体别名回填到向量检索查询、并减少“证据不足”判断过严的问题。

## 明细

| ID | 类别 | 预设 | 通过 | 模式 | C.Precision | C.Recall | MRR | NDCG | Faithfulness | Relevance | 耗时/ms |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| book_chapter_count | book_profile | 是 | 是 | multi_agent_book_profile | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4.45 |
| book_summary | book_profile | 是 | 是 | multi_agent_book_profile | 50.00% | 50.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2.16 |
| domain_block_prepare | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2.66 |
| domain_rib_frame | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2.49 |
| domain_slipway_vs_block | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.76 |
| domain_total_quality | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.56 |
| domain_measure_tools | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.6 |
| domain_structure_code | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.15 |
| domain_welding_deformation_4_1 | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0.97 |
| domain_welding_deformation_6_2 | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.0 |
| graph_laser_use | graph_rag | 否 | 是 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 7745.31 |
| graph_laser_features | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 33.33% | 100.00% | 100.00% | 100.00% | 40.00% | 3080.52 |
| graph_theodolite_parts | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 33.33% | 100.00% | 100.00% | 66.67% | 0.00% | 4201.8 |
| graph_inclined_slipway_height | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 60.00% | 3343.83 |
| graph_side_block_height | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 40.00% | 3129.61 |
| graph_block_division_factors | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 91.97% | 100.00% | 80.00% | 2984.02 |
| graph_block_joint_principle | graph_rag | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 33.33% | 57.06% | 66.67% | 80.00% | 2731.98 |
| graph_cargo_ship_blocks | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 66.67% | 20.00% | 2737.55 |
| graph_code_levels | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 10492.24 |
| graph_code_information | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 3223.44 |
| graph_lofting_tasks | graph_rag | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 87.72% | 100.00% | 40.00% | 3020.64 |
| graph_molded_table | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2773.52 |
| graph_flexible_template | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 10143.32 |
| graph_assembly_modes | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 50.00% | 50.00% | 60.53% | 100.00% | 80.00% | 2563.66 |
| graph_upright_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 3131.39 |
| graph_reverse_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 50.00% | 20.00% | 38.69% | 66.67% | 0.00% | 2996.12 |
| graph_frame_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3599.96 |
| graph_block_drawing_content | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 66.67% | 0.00% | 4084.3 |
| graph_double_bottom_process | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 50.00% | 16.67% | 35.62% | 66.67% | 0.00% | 3586.11 |
| graph_block_after_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 2829.67 |
| graph_slipway_preparation | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 4400.5 |
| graph_baseline_marker | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 50.00% | 50.00% | 63.09% | 100.00% | 40.00% | 1910.92 |
| graph_lifting_plan | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2945.03 |
| graph_transverse_bulkhead_position | graph_rag | 否 | 是 | multi_agent_graph_rag | 16.67% | 50.00% | 100.00% | 100.00% | 100.00% | 80.00% | 1878.77 |
| graph_deck_block_prepare | graph_rag | 否 | 是 | multi_agent_graph_rag | 16.67% | 50.00% | 25.00% | 43.07% | 100.00% | 60.00% | 2738.24 |
| graph_superstructure_position | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 40.00% | 3008.08 |
| graph_repair_survey | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2796.21 |
| graph_plate_thickness_measure | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 3269.57 |
| graph_deformation_measure | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 40.00% | 3312.41 |
| negative_mars_population | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3186.71 |
| negative_reactor_repair | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3725.78 |
| negative_aircraft_wing | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2940.5 |
| negative_latest_standard | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2440.41 |

## 说明

本评估根据 `RAG评估体系.docx` 中的指标进行工程化近似实现，不额外调用 LLM-as-Judge。
默认评估集来自 `data/evaluation/rag_eval_dataset.jsonl`，其中 `is_preset=false` 的样本作为严格主评估集；`is_preset=true` 的样本仅用于验证规则智能体与快捷路径。
Context Precision、Context Recall、MRR、NDCG 基于期望页码与返回文档页码计算。
Faithfulness、Answer Relevance、Completeness、Correctness、Fluency 采用证据命中、引用、关键词覆盖、格式与乱码检测等规则近似计算。
Graph RAG 类问题会调用云雾模型，因此耗时显著高于 book_profile 和 domain_qa 快速路径。