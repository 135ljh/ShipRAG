# 第五章知识抽取质量评测（round2）

| 模型 | Entity P | Entity R | Entity F1 | 类型准确率 | Strict Triple F1 | Relaxed Triple F1 | Semantic-like F1 | JSON合法率 | 抽取成功率 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pangu | 70.67% | 56.99% | 63.10% | 73.58% | 0.00% | 7.50% | 7.50% | 100.00% | 100.00% |
| deepseek | 76.92% | 64.52% | 70.18% | 80.00% | 5.29% | 17.99% | 20.11% | 80.00% | 80.00% |

说明：strict 要求 head/relation/tail 完全一致；relaxed 允许关系归一、实体别名、包含关系和核心数值匹配；semantic-like 在 relaxed 基础上加入少量字符重叠近似判断。
