# ShipRAG RAG 评估报告

本报告按照 `RAG评估体系.docx` 中的三层指标体系重新计算：检索层、生成层、系统层。

- 评估样本数：200
- 样本构成：43 条人工/控制样本 + 157 条 Pangu 图谱关系与教材页证据自动构造样本；自动样本均标记为非预设。
- 任务完成率：79.00%
- 路由准确率：100.00%
- 噪声鲁棒性：100.00%
- 负样本拒绝率：100.00%
- 严格非预设样本数：190
- 严格非预设通过率：77.89%

## 核心指标

| 层级 | 指标 | 分数 |
|---|---|---:|
| 检索层 | Context Precision | 40.42% |
| 检索层 | Context Recall | 92.63% |
| 检索层 | Hit@K | 93.50% |
| 检索层 | MRR | 90.33% |
| 检索层 | NDCG | 91.11% |
| 生成层 | Faithfulness/Groundedness | 95.67% |
| 生成层 | Answer Relevance | 74.17% |
| 生成层 | Answer Completeness | 74.17% |
| 生成层 | Answer Correctness | 87.33% |
| 生成层 | Fluency | 100.00% |
| 系统层 | Context Utilization | 39.92% |
| 系统层 | Task Completion | 79.00% |
| 系统层 | Negative Rejection | 100.00% |
| 系统层 | Noise Robustness | 100.00% |

## 质量辅助指标

- 关键词覆盖率均值：74.17%
- 期望页命中率：93.50%
- 引用完整率：100.00%
- 答案结构完整率：100.00%
- 无法确定率：15.00%
- 乱码率：0.00%
- Markdown 粗体符号率：0.00%

## 响应耗时

| 指标 | 平均 | P50 | P90 | P95 | 最大 |
|---|---:|---:|---:|---:|---:|
| 首次 wall time/ms | 4167.61 | 3882.25 | 5743.99 | 6999.5 | 20647.42 |
| 系统 reported/ms | 4161.1 | 3875.855 | 5735.978 | 6995.6045 | 20639.76 |
| 缓存 wall time/ms | 0.0 | 0.0 | 0.0 | - | 0.0 |

## 分类结果

| 类别 | 样本数 | 通过率 | Context Precision | Context Recall | Faithfulness | Answer Relevance | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| book_profile | 2 | 100.00% | 75.00% | 75.00% | 100.00% | 100.00% | 2.72 |
| domain_qa | 8 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.45 |
| graph_rag | 29 | 37.93% | 14.94% | 50.86% | 96.55% | 55.17% | 4882.33 |
| graph_rag_auto | 157 | 84.71% | 40.13% | 100.00% | 95.12% | 76.44% | 4291.23 |
| negative | 4 | 100.00% | 100.00% | 100.00% | 100.00% | 58.33% | 4548.39 |

## 预设样本隔离

为避免把 `domain_qa.py` 中的规则问答当作真实 RAG 能力，本次评估把样本拆成两组：

| 子集 | 样本数 | 通过率 | Context Precision | Context Recall | Hit@K | Faithfulness | Answer Relevance | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| strict_non_preset | 190 | 77.89% | 37.54% | 92.50% | 93.16% | 95.44% | 72.81% | 4386.86 |
| preset_or_rule_based | 10 | 100.00% | 95.00% | 95.00% | 100.00% | 100.00% | 100.00% | 1.7 |

## 评估结论

- 严格非预设样本通过率为 77.89%，明显低于规则路径，说明此前只用少量 `domain_qa.py` 预设题无法代表真实 RAG 能力。
- 非预设样本 Hit@K 为 93.16%，页码命中保持较高水平；Context Precision 为 37.54%，说明页码证据压缩与融合候选保留策略提升了证据精度。
- 生成层 Faithfulness 为 95.44%，说明答案总体能被证据支撑；后续主要优化点不再是“找不到证据”，而是候选证据重排序和人工开放题的答案完整性。
- 157 条自动样本采用 Pangu 抽取的实体关系、关系来源页和教材证据作为弱标注，适合评估图谱事实能否被检索、定位并转化为答案；其口径与人工精选题不同，应单独观察。
- 后续优化重点应放在：加入 RerankerAgent 提升 Context Precision、继续扩充人工开放问答样本、优化非页码题的证据定位，并对超长耗时请求增加超时与降级策略。

## 明细

| ID | 类别 | 预设 | 通过 | 模式 | C.Precision | C.Recall | MRR | NDCG | Faithfulness | Relevance | 耗时/ms |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| book_chapter_count | book_profile | 是 | 是 | multi_agent_book_profile | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3.5 |
| book_summary | book_profile | 是 | 是 | multi_agent_book_profile | 50.00% | 50.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.94 |
| domain_block_prepare | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2.05 |
| domain_rib_frame | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.27 |
| domain_slipway_vs_block | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.18 |
| domain_total_quality | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.5 |
| domain_measure_tools | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.84 |
| domain_structure_code | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.51 |
| domain_welding_deformation_4_1 | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.13 |
| domain_welding_deformation_6_2 | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.11 |
| graph_laser_use | graph_rag | 否 | 是 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 8410.59 |
| graph_laser_features | graph_rag | 否 | 否 | multi_agent_graph_rag | 33.33% | 66.67% | 100.00% | 91.97% | 100.00% | 40.00% | 7353.08 |
| graph_theodolite_parts | graph_rag | 否 | 否 | multi_agent_graph_rag | 33.33% | 66.67% | 100.00% | 91.97% | 100.00% | 40.00% | 7682.8 |
| graph_inclined_slipway_height | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 60.00% | 5891.27 |
| graph_side_block_height | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2799.12 |
| graph_block_division_factors | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 5021.11 |
| graph_block_joint_principle | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 25.00% | 48.25% | 100.00% | 60.00% | 4506.08 |
| graph_cargo_ship_blocks | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 0.00% | 3899.28 |
| graph_code_levels | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 66.67% | 25.00% | 48.25% | 100.00% | 60.00% | 2555.28 |
| graph_code_information | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 5325.27 |
| graph_lofting_tasks | graph_rag | 否 | 是 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 8949.21 |
| graph_molded_table | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 5080.07 |
| graph_flexible_template | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 100.00% | 4921.27 |
| graph_assembly_modes | graph_rag | 否 | 是 | multi_agent_graph_rag | 50.00% | 75.00% | 50.00% | 66.53% | 100.00% | 100.00% | 2994.91 |
| graph_upright_assembly | graph_rag | 否 | 是 | multi_agent_graph_rag | 16.67% | 100.00% | 16.67% | 35.62% | 100.00% | 100.00% | 4387.09 |
| graph_reverse_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 5312.28 |
| graph_frame_assembly | graph_rag | 否 | 是 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 100.00% | 3336.62 |
| graph_block_drawing_content | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 25.00% | 43.07% | 100.00% | 20.00% | 3408.27 |
| graph_double_bottom_process | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 100.00% | 4916.12 |
| graph_block_after_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 80.00% | 3214.96 |
| graph_slipway_preparation | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 4930.59 |
| graph_baseline_marker | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 25.00% | 48.25% | 100.00% | 100.00% | 3831.39 |
| graph_lifting_plan | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 7883.5 |
| graph_transverse_bulkhead_position | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 91.97% | 100.00% | 60.00% | 4605.48 |
| graph_deck_block_prepare | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 33.33% | 57.06% | 100.00% | 60.00% | 5224.03 |
| graph_superstructure_position | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 60.00% | 4196.53 |
| graph_repair_survey | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 4268.33 |
| graph_plate_thickness_measure | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3515.5 |
| graph_deformation_measure | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 16.67% | 35.62% | 66.67% | 40.00% | 3167.43 |
| negative_mars_population | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4093.61 |
| negative_reactor_repair | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 33.33% | 4183.93 |
| negative_aircraft_wing | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 33.33% | 4117.11 |
| negative_latest_standard | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5798.89 |
| auto_relation_001 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2900.96 |
| auto_relation_002 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3283.38 |
| auto_relation_003 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2757.61 |
| auto_relation_004 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 4400.11 |
| auto_relation_005 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3795.52 |
| auto_relation_006 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3474.14 |
| auto_relation_007 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3912.72 |
| auto_relation_008 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4256.59 |
| auto_relation_009 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 6995.18 |
| auto_relation_010 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3678.5 |
| auto_relation_011 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 100.00% | 4314.15 |
| auto_relation_012 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 6698.04 |
| auto_relation_013 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3114.9 |
| auto_relation_014 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 100.00% | 3683.72 |
| auto_relation_015 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4284.59 |
| auto_relation_016 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4930.24 |
| auto_relation_017 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3887.99 |
| auto_relation_018 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 5227.99 |
| auto_relation_019 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3581.41 |
| auto_relation_020 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3900.14 |
| auto_relation_021 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4595.9 |
| auto_relation_022 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 5015.19 |
| auto_relation_023 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2989.79 |
| auto_relation_024 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3666.71 |
| auto_relation_025 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3169.28 |
| auto_relation_026 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4918.41 |
| auto_relation_027 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3581.64 |
| auto_relation_028 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3586.6 |
| auto_relation_029 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3172.29 |
| auto_relation_030 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3683.74 |
| auto_relation_031 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 33.33% | 4811.5 |
| auto_relation_032 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5323.18 |
| auto_relation_033 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3467.56 |
| auto_relation_034 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3983.88 |
| auto_relation_035 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 4126.71 |
| auto_relation_036 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 10133.07 |
| auto_relation_037 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2655.98 |
| auto_relation_038 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4916.32 |
| auto_relation_039 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4581.56 |
| auto_relation_040 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4119.07 |
| auto_relation_041 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3512.8 |
| auto_relation_042 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5395.55 |
| auto_relation_043 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3278.62 |
| auto_relation_044 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3376.95 |
| auto_relation_045 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3285.99 |
| auto_relation_046 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 5521.29 |
| auto_relation_047 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3181.22 |
| auto_relation_048 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3778.51 |
| auto_relation_049 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4302.96 |
| auto_relation_050 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2965.99 |
| auto_relation_051 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3219.06 |
| auto_relation_052 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3851.25 |
| auto_relation_053 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3393.75 |
| auto_relation_054 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4075.93 |
| auto_relation_055 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3687.9 |
| auto_relation_056 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3578.3 |
| auto_relation_057 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4104.08 |
| auto_relation_058 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3060.72 |
| auto_relation_059 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3689.57 |
| auto_relation_060 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3408.4 |
| auto_relation_061 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4835.48 |
| auto_relation_062 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4242.46 |
| auto_relation_063 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4445.24 |
| auto_relation_064 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 20647.42 |
| auto_relation_065 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5036.11 |
| auto_relation_066 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5200.58 |
| auto_relation_067 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4502.44 |
| auto_relation_068 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3684.73 |
| auto_relation_069 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5324.76 |
| auto_relation_070 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3991.21 |
| auto_relation_071 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3116.85 |
| auto_relation_072 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3065.07 |
| auto_relation_073 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3302.25 |
| auto_relation_074 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3527.13 |
| auto_relation_075 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3785.9 |
| auto_relation_076 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4515.3 |
| auto_relation_077 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3676.51 |
| auto_relation_078 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4221.78 |
| auto_relation_079 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4309.1 |
| auto_relation_080 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3409.25 |
| auto_relation_081 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3012.85 |
| auto_relation_082 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3916.25 |
| auto_relation_083 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3543.71 |
| auto_relation_084 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 6110.02 |
| auto_relation_085 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3430.65 |
| auto_relation_086 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4963.16 |
| auto_relation_087 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3650.1 |
| auto_relation_088 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3147.84 |
| auto_relation_089 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3767.83 |
| auto_relation_090 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 6878.11 |
| auto_relation_091 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3474.51 |
| auto_relation_092 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5450.49 |
| auto_relation_093 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4160.93 |
| auto_relation_094 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3461.03 |
| auto_relation_095 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3214.72 |
| auto_relation_096 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3578.17 |
| auto_relation_097 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3883.21 |
| auto_relation_098 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3494.65 |
| auto_relation_099 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3893.29 |
| auto_relation_100 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3988.89 |
| auto_relation_101 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 4195.2 |
| auto_relation_102 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 9019.16 |
| auto_relation_103 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3473.58 |
| auto_relation_104 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3475.77 |
| auto_relation_105 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3881.29 |
| auto_relation_106 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3693.65 |
| auto_relation_107 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4529.49 |
| auto_relation_108 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3150.89 |
| auto_relation_109 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3583.58 |
| auto_relation_110 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3694.81 |
| auto_relation_111 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3818.3 |
| auto_relation_112 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5703.32 |
| auto_relation_113 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4189.42 |
| auto_relation_114 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3683.54 |
| auto_relation_115 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2663.63 |
| auto_relation_116 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5737.89 |
| auto_relation_117 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3268.81 |
| auto_relation_118 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 6265.41 |
| auto_relation_119 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 10325.41 |
| auto_relation_120 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4508.64 |
| auto_relation_121 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 7081.58 |
| auto_relation_122 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3769.73 |
| auto_relation_123 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4504.78 |
| auto_relation_124 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4003.17 |
| auto_relation_125 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3564.24 |
| auto_relation_126 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3586.1 |
| auto_relation_127 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5820.98 |
| auto_relation_128 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4633.72 |
| auto_relation_129 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5826.63 |
| auto_relation_130 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4992.71 |
| auto_relation_131 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5302.5 |
| auto_relation_132 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4552.39 |
| auto_relation_133 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 66.67% | 66.67% | 3583.85 |
| auto_relation_134 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4192.1 |
| auto_relation_135 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4813.33 |
| auto_relation_136 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3824.04 |
| auto_relation_137 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 6515.1 |
| auto_relation_138 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3868.59 |
| auto_relation_139 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3613.1 |
| auto_relation_140 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3162.88 |
| auto_relation_141 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3382.57 |
| auto_relation_142 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3069.51 |
| auto_relation_143 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4709.7 |
| auto_relation_144 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3790.68 |
| auto_relation_145 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3742.33 |
| auto_relation_146 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3935.34 |
| auto_relation_147 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3069.9 |
| auto_relation_148 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3041.41 |
| auto_relation_149 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 4022.53 |
| auto_relation_150 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3377.54 |
| auto_relation_151 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 5645.29 |
| auto_relation_152 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3771.39 |
| auto_relation_153 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3090.06 |
| auto_relation_154 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 3992.43 |
| auto_relation_155 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 5713.31 |
| auto_relation_156 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 66.67% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 4591.59 |
| auto_relation_157 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2599.02 |

## 说明

本评估根据 `RAG评估体系.docx` 中的指标进行工程化近似实现，不额外调用 LLM-as-Judge。
默认评估集来自 `data/evaluation/rag_eval_dataset.jsonl`，其中 `is_preset=false` 的样本作为严格主评估集；`is_preset=true` 的样本仅用于验证规则智能体与快捷路径。
Context Precision、Context Recall、MRR、NDCG 基于期望页码与返回文档页码计算。
Faithfulness、Answer Relevance、Completeness、Correctness、Fluency 采用证据命中、引用、关键词覆盖、格式与乱码检测等规则近似计算。
Graph RAG 类问题会调用云雾模型，因此耗时显著高于 book_profile 和 domain_qa 快速路径。