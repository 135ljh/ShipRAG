# 第五章知识抽取质量评测

本目录用于对第五章 Pangu 与 DeepSeek 知识抽取结果进行人工标注与自动评测。

## 样本范围

当前选取 5 个代表性 chunk：

- `chapter5_001`：分段装配概述与装配方式总览。
- `chapter5_005`：分段工作图及相关图纸资料。
- `chapter5_012`：舷侧分段装配与双斜切胎架。
- `chapter5_018`：艏、艉分段装配。
- `chapter5_025`：提高分段制造质量的措施。

样本文本：

```powershell
chapter5_rag\eval\gold_sample_chunks.md
```

人工标注模板：

```powershell
chapter5_rag\eval\gold_annotations_template.json
```

## 人工标注

请复制模板并人工填写：

```powershell
Copy-Item chapter5_rag\eval\gold_annotations_template.json chapter5_rag\eval\gold_annotations.json
```

实体类型限定为：

- 分段类型
- 装配方式
- 船体构件
- 工装设备
- 工艺工序
- 图纸资料
- 质量问题
- 控制措施
- 数据指标
- 其他

关系类型建议包括：

- 包括
- 属于
- 可采用
- 适用于
- 用于
- 指导
- 依据
- 组成
- 装配于
- 连接
- 定位
- 控制
- 导致
- 校正

## 自动评测

填写并确认 `gold_annotations.json` 后运行：

```powershell
python chapter5_rag\eval\evaluate_extraction_quality.py
```

输出文件：

- `extraction_eval_report.md`
- `extraction_eval_metrics.json`
- `unmatched_entities.json`
- `unmatched_triples.json`

如果 `gold_annotations.json` 不存在，脚本会退出并提示先人工标注，不会自动生成 gold。

## 第二轮抽取优化与对比

保留第一轮结果后，只对 gold 标注中的 5 个 chunk 进行第二轮抽取：

```powershell
python chapter5_rag\extract_round2_gold_chunks.py --model pangu

$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
python chapter5_rag\extract_round2_gold_chunks.py --model deepseek
```

第二轮评测：

```powershell
python chapter5_rag\eval_extraction_quality.py `
  --gold chapter5_rag\eval\gold_annotations.json `
  --pangu chapter5_rag\outputs\round2\pangu\raw_extractions.jsonl `
  --deepseek chapter5_rag\outputs\round2\deepseek\raw_extractions.jsonl `
  --out-prefix round2
```

生成 round1 / round2 对比报告：

```powershell
python chapter5_rag\compare_extraction_rounds.py
```

第二轮输出文件：

- `round2_extraction_eval_report.md`
- `round2_extraction_eval_metrics.json`
- `round2_unmatched_entities.json`
- `round2_unmatched_triples.json`
- `round2_manual_review_candidates.json`
- `extraction_round_comparison.md`
- `extraction_round_comparison.json`
