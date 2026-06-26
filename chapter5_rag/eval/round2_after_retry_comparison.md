# Round2 DeepSeek 补充重试前后对比

本文件是 after_retry 版本，只用于说明加入失败重试机制后的系统可用性，不替代首次 round2 指标。

| 模型 | 版本 | Entity F1 | Strict Triple F1 | Relaxed Triple F1 | Semantic-like F1 | JSON合法率 | 抽取成功率 |
|---|---|---:|---:|---:|---:|---:|---:|
| pangu | original_round2 | 63.10% | 0.00% | 7.50% | 7.50% | 100.00% | 100.00% |
| deepseek | original_round2 | 70.18% | 5.29% | 17.99% | 20.11% | 80.00% | 80.00% |
| deepseek | after_retry | 70.18% | 5.29% | 17.99% | 20.11% | 80.00% | 80.00% |

`chapter5_012` 首次失败原因：ValueError('<string>:46 Unexpected end of input at column 199')
补充重试成功：否；新增实体 0 个，新增三元组 0 条。

说明：首次运行指标用于衡量模型稳定性；after_retry 指标用于衡量加入失败重试机制后的系统可用性；不能用 after_retry 结果替代首次运行结果。
