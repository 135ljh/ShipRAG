# DeepSeek Round2 失败 Chunk 补充重试分析

本次实验只对 DeepSeek round2 中首次失败的 `chapter5_012` 做一次补充重试，不重跑全量 DeepSeek，也不覆盖 round2 原始结果。

## 重试结果

| 项目 | 结果 |
|---|---|
| 失败 chunk_id | chapter5_012 |
| 首次失败原因 | ValueError('<string>:46 Unexpected end of input at column 199') |
| 重试是否成功 | 否 |
| 是否能解析 JSON | 否 |
| 重试后新增实体数 | 0 |
| 重试后新增三元组数 | 0 |
| evidence 可追溯率 | 0.00% |
| 首次 DeepSeek 抽取成功率 | 80.00% |
| 合并重试后的抽取成功率 | 80.00% |

## 指标解释

- 首次运行指标用于衡量模型稳定性，反映一次性批处理时 DeepSeek 输出 JSON 的可靠程度。
- after_retry 指标用于衡量加入失败重试机制后的系统可用性，反映工程系统在失败补偿后的可恢复能力。
- 不能用 after_retry 结果替代首次运行结果；两者应同时报告：前者看系统可用性，后者看模型首轮稳定性。

## 文件保留说明

原始 round2 文件未被修改：

- `outputs/round2/deepseek/raw_extractions.jsonl`
- `eval/round2_extraction_eval_metrics.json`
- `eval/extraction_round_comparison.md`

本次补充输出保存在：

- `outputs/round2_retry/deepseek/raw_extractions_retry.jsonl`
- `outputs/round2_retry/deepseek/kg_entities_retry.jsonl`
- `outputs/round2_retry/deepseek/kg_triples_retry.jsonl`
- `eval/deepseek_retry_metrics.json`
- `eval/deepseek_retry_analysis.md`
- `eval/round2_after_retry_extraction_eval_metrics.json`
- `eval/round2_after_retry_comparison.md`
