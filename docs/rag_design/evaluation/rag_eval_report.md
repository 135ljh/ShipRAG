# ShipRAG RAG 评估报告

本报告按照 `RAG评估体系.docx` 中的三层指标体系重新计算：检索层、生成层、系统层。

- 评估样本数：200
- 样本构成：43 条人工/控制样本 + 157 条 Pangu 图谱关系与教材页证据自动构造样本；自动样本均标记为非预设。
- 任务完成率：80.50%
- 路由准确率：100.00%
- 噪声鲁棒性：100.00%
- 负样本拒绝率：100.00%
- 严格非预设样本数：190
- 严格非预设通过率：79.47%

## 核心指标

| 层级 | 指标 | 分数 |
|---|---|---:|
| 检索层 | Context Precision | 17.50% |
| 检索层 | Context Recall | 94.21% |
| 检索层 | Hit@K | 95.00% |
| 检索层 | MRR | 90.49% |
| 检索层 | NDCG | 89.56% |
| 生成层 | Faithfulness/Groundedness | 96.00% |
| 生成层 | Answer Relevance | 75.54% |
| 生成层 | Answer Completeness | 75.54% |
| 生成层 | Answer Correctness | 88.12% |
| 生成层 | Fluency | 100.00% |
| 系统层 | Context Utilization | 16.58% |
| 系统层 | Task Completion | 80.50% |
| 系统层 | Negative Rejection | 100.00% |
| 系统层 | Noise Robustness | 100.00% |

## 质量辅助指标

- 关键词覆盖率均值：75.54%
- 期望页命中率：95.00%
- 引用完整率：100.00%
- 答案结构完整率：100.00%
- 无法确定率：14.00%
- 乱码率：0.00%
- Markdown 粗体符号率：0.00%

## 响应耗时

| 指标 | 平均 | P50 | P90 | P95 | 最大 |
|---|---:|---:|---:|---:|---:|
| 首次 wall time/ms | 4279.95 | 3072.4 | 4389.972 | 5658.8115 | 150380.24 |
| 系统 reported/ms | 4273.51 | 3065.955 | 4383.507 | 5653.546 | 150376.8 |
| 缓存 wall time/ms | 0.0 | 0.0 | 0.0 | - | 0.0 |

## 分类结果

| 类别 | 样本数 | 通过率 | Context Precision | Context Recall | Faithfulness | Answer Relevance | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| book_profile | 2 | 100.00% | 75.00% | 75.00% | 100.00% | 100.00% | 2.62 |
| domain_qa | 8 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.12 |
| graph_rag | 29 | 31.03% | 10.38% | 61.78% | 91.95% | 60.00% | 3726.62 |
| graph_rag_auto | 157 | 87.90% | 11.77% | 100.00% | 96.39% | 77.28% | 4652.82 |
| negative | 4 | 100.00% | 100.00% | 100.00% | 100.00% | 58.33% | 4352.78 |

## 预设样本隔离

为避免把 `domain_qa.py` 中的规则问答当作真实 RAG 能力，本次评估把样本拆成两组：

| 子集 | 样本数 | 通过率 | Context Precision | Context Recall | Hit@K | Faithfulness | Answer Relevance | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| strict_non_preset | 190 | 79.47% | 13.42% | 94.17% | 94.74% | 95.79% | 74.25% | 4505.14 |
| preset_or_rule_based | 10 | 100.00% | 95.00% | 95.00% | 100.00% | 100.00% | 100.00% | 1.42 |

## 评估结论

- 严格非预设样本通过率为 79.47%，明显低于规则路径，说明此前只用少量 `domain_qa.py` 预设题无法代表真实 RAG 能力。
- 非预设样本 Hit@K 为 94.74%，页码命中已经明显改善；Context Precision 为 13.42%，说明混合检索和页邻近扩展提高了覆盖率，但也引入了较多辅助证据。
- 生成层 Faithfulness 为 95.79%，说明答案总体能被证据支撑；后续主要优化点不再是“找不到证据”，而是候选证据重排序和人工开放题的答案完整性。
- 157 条自动样本采用 Pangu 抽取的实体关系、关系来源页和教材证据作为弱标注，适合评估图谱事实能否被检索、定位并转化为答案；其口径与人工精选题不同，应单独观察。
- 后续优化重点应放在：加入 RerankerAgent 提升 Context Precision、继续扩充人工开放问答样本、优化非页码题的证据定位，并对超长耗时请求增加超时与降级策略。

## 明细

| ID | 类别 | 预设 | 通过 | 模式 | C.Precision | C.Recall | MRR | NDCG | Faithfulness | Relevance | 耗时/ms |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| book_chapter_count | book_profile | 是 | 是 | multi_agent_book_profile | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3.42 |
| book_summary | book_profile | 是 | 是 | multi_agent_book_profile | 50.00% | 50.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.81 |
| domain_block_prepare | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.24 |
| domain_rib_frame | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.13 |
| domain_slipway_vs_block | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.11 |
| domain_total_quality | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.14 |
| domain_measure_tools | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.1 |
| domain_structure_code | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.1 |
| domain_welding_deformation_4_1 | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.06 |
| domain_welding_deformation_6_2 | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.09 |
| graph_laser_use | graph_rag | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 6998.17 |
| graph_laser_features | graph_rag | 否 | 否 | multi_agent_graph_rag | 18.18% | 66.67% | 100.00% | 91.97% | 100.00% | 40.00% | 3645.67 |
| graph_theodolite_parts | graph_rag | 否 | 否 | multi_agent_graph_rag | 27.27% | 100.00% | 100.00% | 83.96% | 100.00% | 40.00% | 4004.67 |
| graph_inclined_slipway_height | graph_rag | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 10.00% | 28.91% | 100.00% | 60.00% | 3260.81 |
| graph_side_block_height | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 40.00% | 3043.29 |
| graph_block_division_factors | graph_rag | 否 | 否 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 100.00% | 66.67% | 100.00% | 2938.72 |
| graph_block_joint_principle | graph_rag | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 25.00% | 48.25% | 100.00% | 80.00% | 3293.38 |
| graph_cargo_ship_blocks | graph_rag | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 20.00% | 3384.07 |
| graph_code_levels | graph_rag | 否 | 是 | multi_agent_graph_rag | 30.00% | 100.00% | 25.00% | 50.49% | 100.00% | 60.00% | 8178.54 |
| graph_code_information | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3940.27 |
| graph_lofting_tasks | graph_rag | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3137.71 |
| graph_molded_table | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 60.00% | 3923.1 |
| graph_flexible_template | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 100.00% | 3580.43 |
| graph_assembly_modes | graph_rag | 否 | 是 | multi_agent_graph_rag | 30.00% | 75.00% | 50.00% | 66.53% | 100.00% | 80.00% | 5253.76 |
| graph_upright_assembly | graph_rag | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 16.67% | 35.62% | 100.00% | 100.00% | 2730.98 |
| graph_reverse_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 9.09% | 50.00% | 11.11% | 30.10% | 100.00% | 0.00% | 2969.33 |
| graph_frame_assembly | graph_rag | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 50.00% | 63.09% | 100.00% | 80.00% | 2840.86 |
| graph_block_drawing_content | graph_rag | 否 | 否 | multi_agent_graph_rag | 9.09% | 100.00% | 25.00% | 43.07% | 100.00% | 40.00% | 3067.51 |
| graph_double_bottom_process | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 100.00% | 3511.85 |
| graph_block_after_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 80.00% | 3383.58 |
| graph_slipway_preparation | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 40.00% | 3554.47 |
| graph_baseline_marker | graph_rag | 否 | 否 | multi_agent_graph_rag | 20.00% | 100.00% | 25.00% | 48.25% | 66.67% | 100.00% | 3307.69 |
| graph_lifting_plan | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 3277.96 |
| graph_transverse_bulkhead_position | graph_rag | 否 | 否 | multi_agent_graph_rag | 18.18% | 100.00% | 100.00% | 91.97% | 66.67% | 60.00% | 4583.75 |
| graph_deck_block_prepare | graph_rag | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 33.33% | 57.06% | 100.00% | 80.00% | 4306.69 |
| graph_superstructure_position | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 60.00% | 3072.06 |
| graph_repair_survey | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 40.00% | 2863.81 |
| graph_plate_thickness_measure | graph_rag | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 11.11% | 30.10% | 66.67% | 20.00% | 3069.02 |
| graph_deformation_measure | graph_rag | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 16.67% | 35.62% | 66.67% | 40.00% | 2949.91 |
| negative_mars_population | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5651.79 |
| negative_reactor_repair | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 33.33% | 4380.83 |
| negative_aircraft_wing | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4121.31 |
| negative_latest_standard | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3257.21 |
| auto_relation_001 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 3802.65 |
| auto_relation_002 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 3379.46 |
| auto_relation_003 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2159.14 |
| auto_relation_004 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3194.23 |
| auto_relation_005 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 66.67% | 100.00% | 3348.55 |
| auto_relation_006 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2765.32 |
| auto_relation_007 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3173.89 |
| auto_relation_008 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3396.6 |
| auto_relation_009 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4073.83 |
| auto_relation_010 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 11127.19 |
| auto_relation_011 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 66.67% | 100.00% | 2778.09 |
| auto_relation_012 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2888.7 |
| auto_relation_013 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2184.64 |
| auto_relation_014 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3440.44 |
| auto_relation_015 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3081.31 |
| auto_relation_016 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2958.73 |
| auto_relation_017 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 2363.32 |
| auto_relation_018 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 2551.18 |
| auto_relation_019 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2515.73 |
| auto_relation_020 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2499.85 |
| auto_relation_021 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2356.97 |
| auto_relation_022 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4701.89 |
| auto_relation_023 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2460.87 |
| auto_relation_024 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2277.92 |
| auto_relation_025 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 2722.33 |
| auto_relation_026 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 2813.02 |
| auto_relation_027 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 2717.83 |
| auto_relation_028 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2954.7 |
| auto_relation_029 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2792.11 |
| auto_relation_030 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3378.2 |
| auto_relation_031 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 33.33% | 3281.23 |
| auto_relation_032 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 33.33% | 2553.5 |
| auto_relation_033 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3282.6 |
| auto_relation_034 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2680.2 |
| auto_relation_035 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 3098.17 |
| auto_relation_036 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 2710.55 |
| auto_relation_037 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 2765.0 |
| auto_relation_038 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 18.18% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 2610.91 |
| auto_relation_039 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3444.21 |
| auto_relation_040 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3590.71 |
| auto_relation_041 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3072.74 |
| auto_relation_042 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 4150.73 |
| auto_relation_043 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 4596.65 |
| auto_relation_044 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 2749.05 |
| auto_relation_045 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2708.74 |
| auto_relation_046 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2459.96 |
| auto_relation_047 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3884.94 |
| auto_relation_048 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3482.92 |
| auto_relation_049 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 18.18% | 100.00% | 100.00% | 87.72% | 66.67% | 66.67% | 3277.54 |
| auto_relation_050 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 2764.99 |
| auto_relation_051 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 18.18% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 2589.31 |
| auto_relation_052 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2907.15 |
| auto_relation_053 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3201.58 |
| auto_relation_054 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4012.74 |
| auto_relation_055 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4313.66 |
| auto_relation_056 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3134.56 |
| auto_relation_057 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3459.58 |
| auto_relation_058 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3297.89 |
| auto_relation_059 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2611.39 |
| auto_relation_060 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3538.48 |
| auto_relation_061 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2761.91 |
| auto_relation_062 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3284.04 |
| auto_relation_063 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 3135.36 |
| auto_relation_064 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 3609.28 |
| auto_relation_065 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3276.24 |
| auto_relation_066 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3038.27 |
| auto_relation_067 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2695.59 |
| auto_relation_068 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3017.69 |
| auto_relation_069 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 66.67% | 66.67% | 3078.68 |
| auto_relation_070 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 3222.57 |
| auto_relation_071 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2759.46 |
| auto_relation_072 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2956.81 |
| auto_relation_073 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 18.18% | 100.00% | 100.00% | 87.72% | 66.67% | 66.67% | 3390.2 |
| auto_relation_074 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3005.77 |
| auto_relation_075 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2929.29 |
| auto_relation_076 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3576.11 |
| auto_relation_077 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 2770.07 |
| auto_relation_078 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2469.0 |
| auto_relation_079 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2520.04 |
| auto_relation_080 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3204.99 |
| auto_relation_081 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 150380.24 |
| auto_relation_082 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4135.84 |
| auto_relation_083 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 2428.32 |
| auto_relation_084 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 3176.97 |
| auto_relation_085 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2288.29 |
| auto_relation_086 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4030.57 |
| auto_relation_087 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 2530.39 |
| auto_relation_088 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 2549.7 |
| auto_relation_089 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2459.18 |
| auto_relation_090 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2756.34 |
| auto_relation_091 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 59289.98 |
| auto_relation_092 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3147.31 |
| auto_relation_093 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2824.9 |
| auto_relation_094 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2628.59 |
| auto_relation_095 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4472.25 |
| auto_relation_096 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2696.32 |
| auto_relation_097 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 3375.02 |
| auto_relation_098 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 2869.8 |
| auto_relation_099 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 12.50% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2963.31 |
| auto_relation_100 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 12.50% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2851.46 |
| auto_relation_101 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3408.52 |
| auto_relation_102 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3242.81 |
| auto_relation_103 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3362.5 |
| auto_relation_104 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2396.19 |
| auto_relation_105 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2760.39 |
| auto_relation_106 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 7574.62 |
| auto_relation_107 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 66.67% | 100.00% | 2870.54 |
| auto_relation_108 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3053.28 |
| auto_relation_109 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2043.01 |
| auto_relation_110 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2778.46 |
| auto_relation_111 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3247.93 |
| auto_relation_112 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2595.48 |
| auto_relation_113 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3685.79 |
| auto_relation_114 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3929.15 |
| auto_relation_115 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2669.31 |
| auto_relation_116 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2795.14 |
| auto_relation_117 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2268.15 |
| auto_relation_118 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2562.47 |
| auto_relation_119 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 2960.27 |
| auto_relation_120 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3585.65 |
| auto_relation_121 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3022.67 |
| auto_relation_122 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2608.64 |
| auto_relation_123 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2983.95 |
| auto_relation_124 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2850.1 |
| auto_relation_125 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2971.41 |
| auto_relation_126 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2455.67 |
| auto_relation_127 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3597.82 |
| auto_relation_128 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3083.06 |
| auto_relation_129 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3797.75 |
| auto_relation_130 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4058.71 |
| auto_relation_131 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5134.8 |
| auto_relation_132 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3478.02 |
| auto_relation_133 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 2789.3 |
| auto_relation_134 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3316.15 |
| auto_relation_135 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 5448.07 |
| auto_relation_136 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 66.67% | 100.00% | 2659.7 |
| auto_relation_137 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3199.19 |
| auto_relation_138 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3265.86 |
| auto_relation_139 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2721.72 |
| auto_relation_140 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2791.1 |
| auto_relation_141 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 18.18% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 2454.23 |
| auto_relation_142 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 3271.77 |
| auto_relation_143 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3714.28 |
| auto_relation_144 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3148.59 |
| auto_relation_145 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2705.71 |
| auto_relation_146 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2513.79 |
| auto_relation_147 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2195.41 |
| auto_relation_148 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 17669.87 |
| auto_relation_149 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 5528.97 |
| auto_relation_150 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4297.73 |
| auto_relation_151 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5792.22 |
| auto_relation_152 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 8496.34 |
| auto_relation_153 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 5489.71 |
| auto_relation_154 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 9.09% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2799.12 |
| auto_relation_155 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 3333.09 |
| auto_relation_156 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 20.00% | 100.00% | 100.00% | 87.72% | 100.00% | 66.67% | 3166.54 |
| auto_relation_157 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 10.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 6245.94 |

## 说明

本评估根据 `RAG评估体系.docx` 中的指标进行工程化近似实现，不额外调用 LLM-as-Judge。
默认评估集来自 `data/evaluation/rag_eval_dataset.jsonl`，其中 `is_preset=false` 的样本作为严格主评估集；`is_preset=true` 的样本仅用于验证规则智能体与快捷路径。
Context Precision、Context Recall、MRR、NDCG 基于期望页码与返回文档页码计算。
Faithfulness、Answer Relevance、Completeness、Correctness、Fluency 采用证据命中、引用、关键词覆盖、格式与乱码检测等规则近似计算。
Graph RAG 类问题会调用云雾模型，因此耗时显著高于 book_profile 和 domain_qa 快速路径。