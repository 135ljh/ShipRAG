# 第五章 RAG 多智能体设计说明

## 目标

第五章 RAG 系统在原有“知识图谱 + 向量数据库 + Pangu 生成”的基础上，进一步设计为多智能体协同架构。多个智能体围绕同一用户问题分工处理，分别完成问题规划、向量召回、图谱召回、证据融合、答案生成和答案校验。

## 智能体分工

| 智能体 | 类型 | 职责 | 是否调用大模型 |
|---|---|---|---|
| PlannerAgent | 问题规划智能体 | 分析问题意图，生成检索关键词，判断是否需要图谱和向量检索 | 是，调用 Pangu 7B |
| VectorAgent | 文档检索智能体 | 调用 Qdrant 向量库，并融合关键词召回，返回第五章教材证据 | 否 |
| GraphAgent | 图谱检索智能体 | 进行实体链接和图谱邻域检索，返回第五章知识三元组 | 否 |
| FusionAgent | 证据融合智能体 | 合并 Qdrant 文档证据与图谱证据，对图谱支持的 chunk 加权重排 | 否 |
| AnswerAgent | 答案生成智能体 | 基于融合证据调用 Pangu 7B 生成最终答案 | 是，调用 Pangu 7B |
| VerifierAgent | 校验智能体 | 检查答案是否有证据支撑、是否包含“结论/依据/引用”结构 | 否 |

## 执行链路

```text
用户问题
  -> PlannerAgent：分析意图和关键词
  -> VectorAgent：Qdrant 向量召回 + 关键词召回
  -> GraphAgent：实体链接 + 图谱关系召回
  -> FusionAgent：证据融合和重排
  -> AnswerAgent：Pangu 7B 生成答案
  -> VerifierAgent：证据与格式校验
  -> 返回答案、证据和 Agent Trace
```

## 系统特点

- 保留 Pangu 7B 作为生成式 LLM，用于问题规划和最终答案生成。
- Qdrant 负责第五章教材 chunk 的向量检索，collection 为 `chapter5_rag_chunks`。
- 图谱检索直接读取 `outputs/graph/entities.jsonl` 和 `relations.jsonl`。
- 前端新增 `AGENT TRACE` 区域，可以展示每个智能体的执行动作、耗时和关键输出。
- `metadata.agent_trace` 会随 `/ask` 接口返回，便于调试和课程报告展示。
