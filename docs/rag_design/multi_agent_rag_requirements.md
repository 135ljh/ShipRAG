# ShipRAG 多智能体 RAG 系统需求与设计

## 1. 建设目标

在现有 ShipRAG 图谱问答系统基础上，引入多智能体协作机制，使系统不再由单一问答模块直接完成全部工作，而是由多个具备明确职责的智能体共同完成问题理解、证据检索、答案生成和结果校验。

该设计用于满足课程报告中“考虑设计多智能体系统（多个大模型相互分工）”的扩展要求，同时提升系统可解释性和演示效果。

## 2. 设计原则

1. 保持现有系统稳定：复用 Neo4j、Qdrant、Pangu 知识图谱和云雾 OpenAI 兼容模型。
2. 职责清晰：每个智能体只负责一个相对独立的任务。
3. 可追踪：每次问答返回 `agent_trace`，展示智能体执行链路。
4. 可扩展：后续可以将规则型智能体替换为 Pangu 或其他大模型智能体。
5. 可演示：前端页面展示智能体流程，让系统具备“多智能体协作”的可见证据。

## 3. 智能体划分

| 智能体 | 职责 | 当前实现方式 |
|---|---|---|
| RouterAgent | 判断问题类型和处理路径 | 规则路由 |
| BookProfileAgent | 回答书籍元信息问题 | 教材简介和目录档案 |
| DomainQAAgent | 回答高频船体装配核心工艺题 | 教材证据整理 |
| EntityAgent | 实体识别与实体链接 | Neo4j 实体匹配 |
| GraphAgent | 图谱证据检索 | Neo4j 邻域关系检索 |
| DocumentAgent | 文档证据检索 | Qdrant 向量检索 |
| SynthesisAgent | 证据融合与裁剪 | 图谱事实和文档片段组装 |
| AnswerAgent | 生成最终答案 | 云雾 `gpt-5.4-mini` |
| VerifierAgent | 答案证据检查 | 规则校验 |

## 4. 问答流程

### 4.1 书籍元信息问题

```text
用户问题
-> RouterAgent
-> BookProfileAgent
-> VerifierAgent
-> 最终回答
```

适用问题：

```text
这本书讲什么？
这本书有多少章？
作者是谁？
```

### 4.2 教材核心工艺问题

```text
用户问题
-> RouterAgent
-> DomainQAAgent
-> VerifierAgent
-> 最终回答
```

适用问题：

```text
船体分段装配前需要做哪些准备工作？
船体结构编码的作用是什么？
船体装配中常用的测量工具有哪些？
```

### 4.3 普通 Graph RAG 问题

```text
用户问题
-> RouterAgent
-> EntityAgent
-> GraphAgent
-> DocumentAgent
-> SynthesisAgent
-> AnswerAgent
-> VerifierAgent
-> 最终回答
```

## 5. 数据与模型分工

Pangu 主要用于知识图谱构建阶段：

1. 实体识别。
2. 关系抽取。
3. 三元组规范化。
4. 图谱构建数据生成。

云雾 OpenAI 兼容模型主要用于问答阶段：

1. 根据图谱事实和教材证据生成自然语言答案。
2. 对复杂问题进行解释性组织。

Neo4j 和 Qdrant 分别作为图谱智能体和文档智能体的外部工具。

## 6. 接口返回

`/ask` 接口在原有返回结构中增加：

```json
{
  "metadata": {
    "retrieval_mode": "multi_agent_graph_rag",
    "agent_trace": [
      {
        "agent": "RouterAgent",
        "status": "success",
        "detail": "route=graph_rag",
        "elapsed_ms": 0.01
      }
    ]
  }
}
```

前端展示该执行链路，用于说明系统的多智能体协作过程。

## 7. 后续扩展

1. 将 RouterAgent 升级为大模型意图识别智能体。
2. 将 VerifierAgent 升级为事实一致性校验智能体。
3. 将 SynthesisAgent 升级为证据排序和冲突检测智能体。
4. 支持多个大模型并行生成答案，再由 VerifierAgent 选择最佳答案。
