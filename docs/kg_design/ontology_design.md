# 船体装配工艺知识图谱本体设计

## 1. 设计目标

本知识图谱面向《中级船体装配工工艺学》的知识组织、知识抽取和 RAG 问答。图谱需要表达船体装配领域中的对象、工艺、工具、测量方法、质量要求和工序关系，使后续系统能够支持“概念查询、工艺流程查询、工具用途查询、质量控制查询”等任务。

本体设计遵循三个原则：

- 面向教材语料：实体和关系优先来自教材章节、术语和工艺描述。
- 面向知识抽取：实体类别和关系类别保持清晰、可判定，方便大模型输出结构化三元组。
- 面向 RAG 和图谱融合：每个实体、关系和三元组都保留来源页码、文本片段和置信度，便于追溯。

## 2. 核心实体类型

| 实体类型 | 英文字段 | 说明 | 示例 |
|---|---|---|---|
| 章节 | Chapter | 教材的章、节、知识单元 | 第一章工艺基础及相关工种知识、第一节船体装配中的较复杂测量 |
| 工艺对象 | ProcessObject | 被加工、装配、测量或修理的船体对象 | 船体、船体分段、底部分段、舷侧分段、甲板分段 |
| 构件 | Component | 船体结构中的具体构件 | 肋骨、甲板、舱壁、内底板、纵向构件 |
| 工艺过程 | Process | 具有明确操作目标的工艺活动 | 船体放样、分段装配、船体总装配、船体修理 |
| 工序/操作 | Operation | 工艺过程中的具体步骤或动作 | 划线、定位、测量、吊装、合拢、焊接、除锈 |
| 工具设备 | ToolEquipment | 完成工艺活动所需工具、仪器、设备 | 激光经纬仪、卷尺、线锤、胎架、起重设备 |
| 测量对象/指标 | Measurement | 尺寸、精度、位置等可测量指标 | 高度、宽度、长度、垂直度、水平度、直线度 |
| 工艺参数 | Parameter | 工艺中的数值、公式、条件或技术参数 | 基准线、理论高度、预修整余量、结构代码 |
| 材料/介质 | Material | 船体制造或处理中的材料、介质 | 板材、型材、涂料、保护气体 |
| 质量要求 | QualityRequirement | 对工艺结果的规范、检查项、质量控制要求 | 制造质量、定位精度、装配质量 |
| 问题/缺陷 | Defect | 修理或质量检查中识别的问题 | 变形、偏高、偏低、锈蚀、裂纹 |
| 安全/规范 | StandardSafety | 安全要求、标准、规范、操作注意事项 | 船舶建造安全技术、职业技能鉴定规范 |

## 3. 核心关系类型

| 关系类型 | 英文字段 | 主语类型 | 宾语类型 | 说明 |
|---|---|---|---|---|
| 包含 | contains | Chapter/Process | 任意实体 | 章节、过程包含子知识点 |
| 属于 | belongs_to | 任意实体 | Chapter/Process | 知识点归属到章节或工艺过程 |
| 用于 | used_for | ToolEquipment/Operation | Process/Operation/Measurement | 工具或操作的用途 |
| 使用工具 | uses_tool | Process/Operation | ToolEquipment | 某工艺或工序使用的工具设备 |
| 操作对象 | operates_on | Process/Operation | ProcessObject/Component | 工艺或工序作用的对象 |
| 前置工序 | precedes | Operation/Process | Operation/Process | 工艺流程先后关系 |
| 后续工序 | follows | Operation/Process | Operation/Process | 工艺流程后续关系 |
| 测量指标 | measures | ToolEquipment/Operation | Measurement | 工具或操作测量的指标 |
| 控制指标 | controls | Process/Operation | Measurement/QualityRequirement | 工艺过程控制的质量或测量指标 |
| 产生依据 | provides_basis_for | Process/Operation/Parameter | Operation/Process | 放样、图纸、基准线等为后续工序提供依据 |
| 由……组成 | composed_of | ProcessObject/Component | Component | 结构组成关系 |
| 连接/装配 | assembled_with | Component/ProcessObject | Component/ProcessObject | 构件或分段之间的装配关系 |
| 位置关系 | located_at | Component/ProcessObject | Component/ProcessObject/Parameter | 构件位置或基准关系 |
| 导致 | causes | Defect/Operation/Condition | Defect/QualityRequirement | 问题或条件导致结果 |
| 检查/评估 | checks | Operation/ToolEquipment | QualityRequirement/Measurement | 检查某项质量或指标 |
| 修理对象 | repairs | Process/Operation | Defect/Component | 修理工艺针对的缺陷或构件 |

## 4. 属性设计

### 实体属性

| 属性 | 说明 |
|---|---|
| `id` | 实体唯一编号 |
| `name` | 实体标准名称 |
| `type` | 实体类型 |
| `aliases` | 别名或 OCR 可能变体 |
| `definition` | 简短定义，可由大模型基于上下文生成 |
| `source_pages` | 来源页码列表 |
| `source_chunks` | 来源 chunk 编号 |
| `confidence` | 抽取置信度 |

### 关系属性

| 属性 | 说明 |
|---|---|
| `head` | 头实体 |
| `relation` | 关系类型 |
| `tail` | 尾实体 |
| `evidence` | 原文证据 |
| `source_page` | 来源页码 |
| `source_chunk` | 来源 chunk 编号 |
| `confidence` | 关系置信度 |

## 5. 三元组示例

```json
[
  {
    "head": "激光经纬仪",
    "head_type": "ToolEquipment",
    "relation": "used_for",
    "tail": "船体建造测量",
    "tail_type": "Operation",
    "evidence": "激光经纬仪是船厂广泛使用的精密光学测量仪器。在船体建造过程中,它可以用来完成各种测量和画线工作。",
    "source_page": 8,
    "confidence": 0.92
  },
  {
    "head": "激光经纬仪",
    "head_type": "ToolEquipment",
    "relation": "measures",
    "tail": "垂直度",
    "tail_type": "Measurement",
    "evidence": "形成铅垂面测结构垂直度、画铅垂线和进行垂直方向的投影。",
    "source_page": 8,
    "confidence": 0.9
  },
  {
    "head": "船体放样",
    "head_type": "Process",
    "relation": "provides_basis_for",
    "tail": "船体装配",
    "tail_type": "Process",
    "evidence": "船体放样的方法虽已由实尺放样改变到数学放样。但其主要任务都是为后续工序提供各种施工依据。",
    "source_page": 5,
    "confidence": 0.88
  }
]
```

## 6. Neo4j 存储建议

建议将所有实体统一存储为 `Entity` 节点，并附加具体类型标签，例如 `:Entity:ToolEquipment`、`:Entity:Process`。关系使用本体中的英文关系名，便于程序处理。

示例：

```cypher
MERGE (a:Entity:ToolEquipment {name: "激光经纬仪"})
MERGE (b:Entity:Measurement {name: "垂直度"})
MERGE (a)-[:MEASURES {
  evidence: "形成铅垂面测结构垂直度、画铅垂线和进行垂直方向的投影。",
  source_page: 8,
  confidence: 0.9
}]->(b);
```

