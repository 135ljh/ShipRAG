# ShipRAG RAG 评估报告

- 评估样本数：15
- 总体通过率：100.00%
- 路由准确率：100.00%
- 关键词覆盖率均值：96.00%
- 期望页命中率：100.00%
- 引用完整率：100.00%
- 答案结构完整率：100.00%
- 无法确定率：0.00%
- 乱码率：0.00%
- Markdown 粗体符号率：0.00%

## 响应耗时

| 指标 | 平均 | P50 | P90 | P95 | 最大 |
|---|---:|---:|---:|---:|---:|
| 首次 wall time/ms | 1140.84 | 1.28 | 3545.484 | 4778.545 | 7616.03 |
| 系统 reported/ms | 1137.83 | 0.04 | 3538.174 | 4772.096 | 7611.59 |
| 缓存 wall time/ms | 3.14 | 1.15 | 6.982 | - | 8.12 |

## 分类结果

| 类别 | 样本数 | 通过率 | 关键词覆盖均值 | 期望页命中率 | 平均耗时/ms |
|---|---:|---:|---:|---:|---:|
| book_profile | 2 | 100.00% | 100.00% | 100.00% | 3.02 |
| domain_qa | 9 | 100.00% | 100.00% | 100.00% | 1.49 |
| graph_rag | 4 | 100.00% | 85.00% | 100.00% | 4273.32 |

## 明细

| ID | 类别 | 通过 | 模式 | 关键词覆盖 | 期望页命中 | 图谱证据 | 文档证据 | 耗时/ms | 智能体链路 |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| book_chapter_count | book_profile | 是 | multi_agent_book_profile | 100.00% | 是 | 0 | 2 | 4.7 | RouterAgent -> BookProfileAgent -> VerifierAgent |
| book_summary | book_profile | 是 | multi_agent_book_profile | 100.00% | 是 | 0 | 2 | 1.33 | RouterAgent -> BookProfileAgent -> VerifierAgent |
| domain_block_prepare | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 是 | 0 | 3 | 1.1 | RouterAgent -> DomainQAAgent -> VerifierAgent |
| domain_rib_frame | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 是 | 0 | 2 | 1.07 | RouterAgent -> DomainQAAgent -> VerifierAgent |
| domain_slipway_vs_block | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 是 | 0 | 3 | 1.02 | RouterAgent -> DomainQAAgent -> VerifierAgent |
| domain_total_quality | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 是 | 0 | 3 | 1.23 | RouterAgent -> DomainQAAgent -> VerifierAgent |
| domain_measure_tools | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 是 | 0 | 3 | 1.28 | RouterAgent -> DomainQAAgent -> VerifierAgent |
| domain_structure_code | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 是 | 0 | 3 | 1.06 | RouterAgent -> DomainQAAgent -> VerifierAgent |
| domain_welding_deformation_4_1 | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 是 | 0 | 3 | 1.04 | RouterAgent -> DomainQAAgent -> VerifierAgent |
| domain_welding_deformation_6_2 | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 是 | 0 | 3 | 1.01 | RouterAgent -> DomainQAAgent -> VerifierAgent |
| graph_laser_use | graph_rag | 是 | multi_agent_graph_rag | 80.00% | 是 | 29 | 4 | 7616.03 | RouterAgent -> EntityAgent -> GraphAgent -> DocumentAgent -> SynthesisAgent -> AnswerAgent -> VerifierAgent |
| graph_lofting_tasks | graph_rag | 是 | multi_agent_graph_rag | 100.00% | 是 | 40 | 6 | 3562.48 | RouterAgent -> EntityAgent -> GraphAgent -> DocumentAgent -> SynthesisAgent -> AnswerAgent -> VerifierAgent |
| graph_baseline_marking | graph_rag | 是 | multi_agent_graph_rag | 60.00% | 是 | 40 | 6 | 3519.99 | RouterAgent -> EntityAgent -> GraphAgent -> DocumentAgent -> SynthesisAgent -> AnswerAgent -> VerifierAgent |
| graph_block_positioning | domain_qa | 是 | multi_agent_domain_qa | 100.00% | 是 | 0 | 3 | 4.56 | RouterAgent -> DomainQAAgent -> VerifierAgent |
| graph_segment_modes | graph_rag | 是 | multi_agent_graph_rag | 100.00% | 是 | 33 | 6 | 2394.77 | RouterAgent -> EntityAgent -> GraphAgent -> DocumentAgent -> SynthesisAgent -> AnswerAgent -> VerifierAgent |

## 说明

本评估为确定性离线评估，不额外调用裁判模型。答案质量通过路由模式、关键词覆盖、期望页命中、证据数量、答案结构、引用完整性、乱码和 Markdown 符号等指标综合判断。
Graph RAG 类问题会调用云雾模型，因此耗时显著高于 book_profile 和 domain_qa 快速路径。