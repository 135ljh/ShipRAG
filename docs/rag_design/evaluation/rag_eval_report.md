# ShipRAG RAG 评估报告

本报告按照 `RAG评估体系.docx` 中的三层指标体系重新计算：检索层、生成层、系统层。

- 评估样本数：200
- 样本构成：43 条人工/控制样本 + 157 条教材 chunk 自动抽样样本；自动样本均标记为非预设。
- 任务完成率：9.50%
- 路由准确率：100.00%
- 噪声鲁棒性：20.00%
- 负样本拒绝率：100.00%
- 严格非预设样本数：190
- 严格非预设通过率：4.74%

## 核心指标

| 层级 | 指标 | 分数 |
|---|---|---:|
| 检索层 | Context Precision | 11.42% |
| 检索层 | Context Recall | 30.08% |
| 检索层 | Hit@K | 32.50% |
| 检索层 | MRR | 20.48% |
| 检索层 | NDCG | 23.27% |
| 生成层 | Faithfulness/Groundedness | 86.17% |
| 生成层 | Answer Relevance | 26.57% |
| 生成层 | Answer Completeness | 26.57% |
| 生成层 | Answer Correctness | 61.75% |
| 生成层 | Fluency | 100.00% |
| 系统层 | Context Utilization | 14.67% |
| 系统层 | Task Completion | 9.50% |
| 系统层 | Negative Rejection | 100.00% |
| 系统层 | Noise Robustness | 20.00% |

## 质量辅助指标

- 关键词覆盖率均值：26.57%
- 期望页命中率：32.50%
- 引用完整率：100.00%
- 答案结构完整率：100.00%
- 无法确定率：43.50%
- 乱码率：0.00%
- Markdown 粗体符号率：0.00%

## 响应耗时

| 指标 | 平均 | P50 | P90 | P95 | 最大 |
|---|---:|---:|---:|---:|---:|
| 首次 wall time/ms | 3614.66 | 3087.07 | 4485.184 | 7125.3375 | 23963.59 |
| 系统 reported/ms | 3608.35 | 3080.415 | 4479.448 | 7121.303 | 23956.33 |
| 缓存 wall time/ms | 0.0 | 0.0 | 0.0 | - | 0.0 |

## 分类结果

| 类别 | 样本数 | 通过率 | Context Precision | Context Recall | Faithfulness | Answer Relevance | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| book_profile | 2 | 100.00% | 75.00% | 75.00% | 100.00% | 100.00% | 5.59 |
| domain_qa | 8 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.43 |
| graph_rag | 29 | 13.79% | 10.35% | 33.33% | 79.31% | 35.17% | 4987.38 |
| graph_rag_auto | 157 | 0.64% | 4.03% | 23.57% | 86.20% | 18.65% | 3605.37 |
| negative | 4 | 100.00% | 100.00% | 100.00% | 100.00% | 91.67% | 3058.45 |

## 预设样本隔离

为避免把 `domain_qa.py` 中的规则问答当作真实 RAG 能力，本次评估把样本拆成两组：

| 子集 | 样本数 | 通过率 | Context Precision | Context Recall | Hit@K | Faithfulness | Answer Relevance | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| strict_non_preset | 190 | 4.74% | 7.02% | 26.67% | 28.95% | 85.44% | 22.71% | 3804.79 |
| preset_or_rule_based | 10 | 100.00% | 95.00% | 95.00% | 100.00% | 100.00% | 100.00% | 2.26 |

## 评估结论

- 严格非预设样本通过率为 4.74%，明显低于规则路径，说明此前只用少量 `domain_qa.py` 预设题无法代表真实 RAG 能力。
- 非预设样本 Hit@K 为 28.95%，Context Precision 为 7.02%，主要瓶颈在教材证据召回和页码命中，而不是答案格式。
- 生成层 Faithfulness 为 85.44%，说明在检索证据不足时系统倾向于保守拒答，降低了幻觉风险，但也导致大量教材内问题回答为“无法确定”。
- 157 条自动样本采用教材 chunk 页码和关键词作为弱标注，评价口径比人工样本更严格，适合暴露召回覆盖率问题，不应和人工精选题的通过率直接等同。
- 后续优化重点应放在：重建 Qdrant 切片与元数据、增强章节/页码/术语索引、把 Neo4j 实体别名回填到向量检索查询、并减少“证据不足”判断过严的问题。

## 明细

| ID | 类别 | 预设 | 通过 | 模式 | C.Precision | C.Recall | MRR | NDCG | Faithfulness | Relevance | 耗时/ms |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| book_chapter_count | book_profile | 是 | 是 | multi_agent_book_profile | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 8.42 |
| book_summary | book_profile | 是 | 是 | multi_agent_book_profile | 50.00% | 50.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2.77 |
| domain_block_prepare | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2.01 |
| domain_rib_frame | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.63 |
| domain_slipway_vs_block | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.36 |
| domain_total_quality | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.5 |
| domain_measure_tools | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.29 |
| domain_structure_code | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.19 |
| domain_welding_deformation_4_1 | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.23 |
| domain_welding_deformation_6_2 | domain_qa | 是 | 是 | multi_agent_domain_qa | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 1.21 |
| graph_laser_use | graph_rag | 否 | 是 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 7096.14 |
| graph_laser_features | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 33.33% | 100.00% | 100.00% | 100.00% | 40.00% | 3463.19 |
| graph_theodolite_parts | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 33.33% | 100.00% | 100.00% | 66.67% | 0.00% | 3782.09 |
| graph_inclined_slipway_height | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 60.00% | 3487.6 |
| graph_side_block_height | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3064.38 |
| graph_block_division_factors | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 91.97% | 100.00% | 80.00% | 3379.54 |
| graph_block_joint_principle | graph_rag | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 33.33% | 57.06% | 66.67% | 80.00% | 2978.0 |
| graph_cargo_ship_blocks | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 40.00% | 2783.01 |
| graph_code_levels | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2938.27 |
| graph_code_information | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 2866.1 |
| graph_lofting_tasks | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 87.72% | 100.00% | 100.00% | 2499.02 |
| graph_molded_table | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 11024.34 |
| graph_flexible_template | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 824.93 |
| graph_assembly_modes | graph_rag | 否 | 是 | multi_agent_graph_rag | 33.33% | 50.00% | 50.00% | 60.53% | 100.00% | 80.00% | 3284.91 |
| graph_upright_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 3666.55 |
| graph_reverse_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 50.00% | 20.00% | 38.69% | 66.67% | 20.00% | 5791.69 |
| graph_frame_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2703.12 |
| graph_block_drawing_content | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 66.67% | 0.00% | 9388.0 |
| graph_double_bottom_process | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 50.00% | 16.67% | 35.62% | 66.67% | 60.00% | 19996.42 |
| graph_block_after_assembly | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 2713.52 |
| graph_slipway_preparation | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 40.00% | 19409.32 |
| graph_baseline_marker | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 50.00% | 50.00% | 63.09% | 100.00% | 40.00% | 2972.52 |
| graph_lifting_plan | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2799.22 |
| graph_transverse_bulkhead_position | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 50.00% | 100.00% | 100.00% | 66.67% | 20.00% | 3428.83 |
| graph_deck_block_prepare | graph_rag | 否 | 否 | multi_agent_graph_rag | 16.67% | 50.00% | 25.00% | 43.07% | 66.67% | 60.00% | 2879.32 |
| graph_superstructure_position | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 40.00% | 2764.21 |
| graph_repair_survey | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 5811.87 |
| graph_plate_thickness_measure | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 3502.18 |
| graph_deformation_measure | graph_rag | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 40.00% | 3335.65 |
| negative_mars_population | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 66.67% | 2807.65 |
| negative_reactor_repair | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2923.1 |
| negative_aircraft_wing | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 3872.14 |
| negative_latest_standard | negative | 否 | 是 | multi_agent_graph_rag | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 2630.9 |
| auto_chunk_shiprag_p008_00008 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 4498.0 |
| auto_chunk_shiprag_p009_00010 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2479.05 |
| auto_chunk_shiprag_p010_00011 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2690.46 |
| auto_chunk_shiprag_p011_00012 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3430.09 |
| auto_chunk_shiprag_p012_00013 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 4204.52 |
| auto_chunk_shiprag_p013_00014 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2563.68 |
| auto_chunk_shiprag_p014_00015 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2751.46 |
| auto_chunk_shiprag_p018_00020 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 3067.71 |
| auto_chunk_shiprag_p019_00021 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2866.98 |
| auto_chunk_shiprag_p021_00024 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2730.03 |
| auto_chunk_shiprag_p022_00025 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3238.33 |
| auto_chunk_shiprag_p023_00026 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 4798.32 |
| auto_chunk_shiprag_p025_00029 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 3059.03 |
| auto_chunk_shiprag_p026_00030 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3070.93 |
| auto_chunk_shiprag_p027_00031 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3377.59 |
| auto_chunk_shiprag_p028_00033 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2898.28 |
| auto_chunk_shiprag_p029_00034 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2119.19 |
| auto_chunk_shiprag_p030_00037 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2469.68 |
| auto_chunk_shiprag_p031_00038 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2618.36 |
| auto_chunk_shiprag_p033_00040 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 16.67% | 35.62% | 100.00% | 20.00% | 3209.83 |
| auto_chunk_shiprag_p034_00042 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3013.85 |
| auto_chunk_shiprag_p035_00043 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3041.44 |
| auto_chunk_shiprag_p036_00045 | graph_rag_auto | 否 | 是 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 80.00% | 3256.03 |
| auto_chunk_shiprag_p037_00046 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 50.00% | 3086.32 |
| auto_chunk_shiprag_p038_00047 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 40.00% | 4255.23 |
| auto_chunk_shiprag_p039_00049 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 25.00% | 43.07% | 100.00% | 20.00% | 2706.48 |
| auto_chunk_shiprag_p040_00050 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 25.00% | 43.07% | 100.00% | 0.00% | 3078.33 |
| auto_chunk_shiprag_p041_00051 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 5.54 |
| auto_chunk_shiprag_p044_00054 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2725.46 |
| auto_chunk_shiprag_p045_00055 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 20.00% | 4483.76 |
| auto_chunk_shiprag_p046_00056 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 3716.02 |
| auto_chunk_shiprag_p047_00057 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 20.00% | 3807.58 |
| auto_chunk_shiprag_p048_00058 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 4971.56 |
| auto_chunk_shiprag_p048_00059 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 25.00% | 3504.44 |
| auto_chunk_shiprag_p051_00062 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3893.75 |
| auto_chunk_shiprag_p051_00063 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 16.67% | 35.62% | 100.00% | 0.00% | 4262.98 |
| auto_chunk_shiprag_p052_00064 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 20.00% | 3738.41 |
| auto_chunk_shiprag_p053_00065 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3705.27 |
| auto_chunk_shiprag_p054_00066 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 20.00% | 3239.33 |
| auto_chunk_shiprag_p054_00067 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 20.00% | 2292.96 |
| auto_chunk_shiprag_p056_00069 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 25.00% | 43.07% | 100.00% | 20.00% | 4048.3 |
| auto_chunk_shiprag_p057_00070 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 3077.3 |
| auto_chunk_shiprag_p058_00071 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 4514.82 |
| auto_chunk_shiprag_p059_00072 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 4083.25 |
| auto_chunk_shiprag_p060_00073 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3173.71 |
| auto_chunk_shiprag_p060_00074 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 23963.59 |
| auto_chunk_shiprag_p062_00076 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 3068.35 |
| auto_chunk_shiprag_p063_00077 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2986.76 |
| auto_chunk_shiprag_p064_00078 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3382.12 |
| auto_chunk_shiprag_p070_00085 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 16.67% | 35.62% | 100.00% | 20.00% | 2946.86 |
| auto_chunk_shiprag_p071_00086 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 5252.85 |
| auto_chunk_shiprag_p074_00090 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 20.00% | 38.69% | 100.00% | 25.00% | 3577.68 |
| auto_chunk_shiprag_p080_00096 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 25.00% | 3322.25 |
| auto_chunk_shiprag_p084_00100 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 25.00% | 43.07% | 100.00% | 40.00% | 4819.47 |
| auto_chunk_shiprag_p085_00101 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2888.17 |
| auto_chunk_shiprag_p086_00102 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 33.33% | 50.00% | 100.00% | 20.00% | 3120.78 |
| auto_chunk_shiprag_p088_00104 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 25.00% | 43.07% | 100.00% | 40.00% | 2814.94 |
| auto_chunk_shiprag_p089_00105 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 20.00% | 38.69% | 66.67% | 25.00% | 4354.8 |
| auto_chunk_shiprag_p091_00107 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3948.73 |
| auto_chunk_shiprag_p092_00108 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 20.00% | 38.69% | 100.00% | 20.00% | 3271.18 |
| auto_chunk_shiprag_p093_00109 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 16427.28 |
| auto_chunk_shiprag_p094_00110 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 4048.75 |
| auto_chunk_shiprag_p096_00112 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 4404.93 |
| auto_chunk_shiprag_p097_00113 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3230.19 |
| auto_chunk_shiprag_p099_00115 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 4140.05 |
| auto_chunk_shiprag_p100_00116 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2974.04 |
| auto_chunk_shiprag_p101_00117 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3177.71 |
| auto_chunk_shiprag_p102_00118 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 0.00% | 3413.06 |
| auto_chunk_shiprag_p103_00119 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 33.33% | 50.00% | 66.67% | 20.00% | 3334.74 |
| auto_chunk_shiprag_p104_00120 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2966.56 |
| auto_chunk_shiprag_p106_00122 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 5428.47 |
| auto_chunk_shiprag_p107_00124 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 40.00% | 3583.1 |
| auto_chunk_shiprag_p108_00125 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3107.8 |
| auto_chunk_shiprag_p109_00126 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 40.00% | 2726.54 |
| auto_chunk_shiprag_p110_00127 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 33.33% | 50.00% | 100.00% | 20.00% | 3278.1 |
| auto_chunk_shiprag_p111_00128 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 11160.6 |
| auto_chunk_shiprag_p113_00130 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 20.00% | 38.69% | 66.67% | 20.00% | 2864.2 |
| auto_chunk_shiprag_p114_00131 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 4299.05 |
| auto_chunk_shiprag_p115_00132 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 17946.4 |
| auto_chunk_shiprag_p116_00133 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 20.00% | 2735.78 |
| auto_chunk_shiprag_p116_00134 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 20.00% | 7680.09 |
| auto_chunk_shiprag_p117_00135 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3632.82 |
| auto_chunk_shiprag_p120_00138 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3127.92 |
| auto_chunk_shiprag_p122_00140 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3476.96 |
| auto_chunk_shiprag_p123_00141 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3788.26 |
| auto_chunk_shiprag_p124_00142 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2982.12 |
| auto_chunk_shiprag_p125_00143 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2918.97 |
| auto_chunk_shiprag_p126_00144 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2839.53 |
| auto_chunk_shiprag_p128_00146 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2220.17 |
| auto_chunk_shiprag_p129_00147 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3579.42 |
| auto_chunk_shiprag_p130_00148 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2846.24 |
| auto_chunk_shiprag_p131_00149 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3132.18 |
| auto_chunk_shiprag_p132_00150 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 20.00% | 3437.95 |
| auto_chunk_shiprag_p133_00151 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 33.33% | 50.00% | 100.00% | 20.00% | 3126.06 |
| auto_chunk_shiprag_p134_00153 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3635.16 |
| auto_chunk_shiprag_p135_00154 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3476.2 |
| auto_chunk_shiprag_p136_00155 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3202.91 |
| auto_chunk_shiprag_p136_00156 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 33.33% | 2996.57 |
| auto_chunk_shiprag_p137_00157 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2723.13 |
| auto_chunk_shiprag_p138_00158 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 16.67% | 35.62% | 100.00% | 0.00% | 3079.0 |
| auto_chunk_shiprag_p140_00160 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2350.06 |
| auto_chunk_shiprag_p141_00161 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2815.18 |
| auto_chunk_shiprag_p141_00162 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2781.34 |
| auto_chunk_shiprag_p143_00164 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2982.75 |
| auto_chunk_shiprag_p144_00165 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3790.64 |
| auto_chunk_shiprag_p145_00166 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3194.03 |
| auto_chunk_shiprag_p146_00168 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2799.89 |
| auto_chunk_shiprag_p147_00169 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2826.65 |
| auto_chunk_shiprag_p148_00170 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3108.17 |
| auto_chunk_shiprag_p149_00171 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 3007.4 |
| auto_chunk_shiprag_p150_00172 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2977.74 |
| auto_chunk_shiprag_p151_00173 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2797.06 |
| auto_chunk_shiprag_p153_00175 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2786.16 |
| auto_chunk_shiprag_p155_00178 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3119.65 |
| auto_chunk_shiprag_p157_00180 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3288.48 |
| auto_chunk_shiprag_p157_00181 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3713.16 |
| auto_chunk_shiprag_p158_00182 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2622.33 |
| auto_chunk_shiprag_p159_00183 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2758.47 |
| auto_chunk_shiprag_p160_00185 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2540.44 |
| auto_chunk_shiprag_p161_00186 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2349.4 |
| auto_chunk_shiprag_p161_00187 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 25.00% | 3035.28 |
| auto_chunk_shiprag_p163_00189 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 25.00% | 43.07% | 100.00% | 40.00% | 2925.47 |
| auto_chunk_shiprag_p164_00190 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 0.00% | 3344.2 |
| auto_chunk_shiprag_p165_00191 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2252.43 |
| auto_chunk_shiprag_p166_00193 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 20.00% | 38.69% | 100.00% | 0.00% | 3109.09 |
| auto_chunk_shiprag_p167_00194 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 1953.63 |
| auto_chunk_shiprag_p168_00195 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3384.57 |
| auto_chunk_shiprag_p169_00196 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 2153.5 |
| auto_chunk_shiprag_p170_00197 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 40.00% | 2597.87 |
| auto_chunk_shiprag_p170_00198 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 4023.18 |
| auto_chunk_shiprag_p172_00200 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3967.07 |
| auto_chunk_shiprag_p173_00201 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3113.67 |
| auto_chunk_shiprag_p174_00202 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3084.37 |
| auto_chunk_shiprag_p174_00203 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 7971.8 |
| auto_chunk_shiprag_p175_00204 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3271.11 |
| auto_chunk_shiprag_p176_00205 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 50.00% | 63.09% | 100.00% | 20.00% | 2969.38 |
| auto_chunk_shiprag_p177_00207 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 33.33% | 100.00% | 100.00% | 91.97% | 100.00% | 0.00% | 3279.0 |
| auto_chunk_shiprag_p177_00208 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2970.89 |
| auto_chunk_shiprag_p178_00209 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 7.1 |
| auto_chunk_shiprag_p179_00210 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 100.00% | 100.00% | 100.00% | 40.00% | 3308.3 |
| auto_chunk_shiprag_p180_00211 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3190.4 |
| auto_chunk_shiprag_p180_00212 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 0.00% | 3863.94 |
| auto_chunk_shiprag_p181_00214 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3144.63 |
| auto_chunk_shiprag_p182_00215 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3580.44 |
| auto_chunk_shiprag_p183_00216 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2454.83 |
| auto_chunk_shiprag_p183_00217 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 25.00% | 43.07% | 66.67% | 20.00% | 3176.67 |
| auto_chunk_shiprag_p184_00218 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2558.01 |
| auto_chunk_shiprag_p185_00219 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 16.67% | 100.00% | 25.00% | 43.07% | 100.00% | 20.00% | 2984.88 |
| auto_chunk_shiprag_p186_00222 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2616.43 |
| auto_chunk_shiprag_p187_00223 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 1996.11 |
| auto_chunk_shiprag_p187_00224 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2862.36 |
| auto_chunk_shiprag_p188_00225 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 2746.29 |
| auto_chunk_shiprag_p189_00226 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3087.82 |
| auto_chunk_shiprag_p190_00228 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2861.28 |
| auto_chunk_shiprag_p191_00229 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 3018.19 |
| auto_chunk_shiprag_p008_00008 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% | 20.00% | 3110.01 |
| auto_chunk_shiprag_p009_00010 | graph_rag_auto | 否 | 否 | multi_agent_graph_rag | 0.00% | 0.00% | 0.00% | 0.00% | 66.67% | 20.00% | 2768.15 |

## 说明

本评估根据 `RAG评估体系.docx` 中的指标进行工程化近似实现，不额外调用 LLM-as-Judge。
默认评估集来自 `data/evaluation/rag_eval_dataset.jsonl`，其中 `is_preset=false` 的样本作为严格主评估集；`is_preset=true` 的样本仅用于验证规则智能体与快捷路径。
Context Precision、Context Recall、MRR、NDCG 基于期望页码与返回文档页码计算。
Faithfulness、Answer Relevance、Completeness、Correctness、Fluency 采用证据命中、引用、关键词覆盖、格式与乱码检测等规则近似计算。
Graph RAG 类问题会调用云雾模型，因此耗时显著高于 book_profile 和 domain_qa 快速路径。