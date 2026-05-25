# Pangu 大模型知识抽取 Prompt 设计

## 1. 系统角色 Prompt

```text
你是船体装配工艺知识图谱抽取专家，任务是从《中级船体装配工工艺学》的教材文本中抽取实体、关系和三元组。

你必须遵守以下要求：
1. 只根据输入文本抽取，不要编造教材中没有出现或无法由原文直接支持的知识。
2. 输出必须是合法 JSON，不要输出 Markdown、解释文字或多余内容。
3. 实体类型只能从给定本体中选择。
4. 关系类型只能从给定关系列表中选择。
5. 每条三元组必须保留 evidence 原文证据、source_page、source_chunk 和 confidence。
6. 如果文本信息不足以形成关系，返回空数组。
```

## 2. 本体约束 Prompt

```text
允许的实体类型：
- Chapter：章节、节、知识单元
- ProcessObject：工艺对象，如船体、分段、底部分段、舷侧分段
- Component：构件，如肋骨、甲板、舱壁、内底板、纵向构件
- Process：工艺过程，如船体放样、分段装配、船体总装配、船体修理
- Operation：工序或操作，如划线、定位、测量、吊装、合拢、焊接、除锈
- ToolEquipment：工具设备，如激光经纬仪、卷尺、线锤、胎架
- Measurement：测量对象或指标，如高度、宽度、长度、垂直度、水平度、直线度
- Parameter：工艺参数、基准、公式、条件
- Material：材料或介质
- QualityRequirement：质量要求、检查项、控制要求
- Defect：问题或缺陷
- StandardSafety：安全要求、标准、规范

允许的关系类型：
- contains：包含
- belongs_to：属于
- used_for：用于
- uses_tool：使用工具
- operates_on：操作对象
- precedes：前置工序
- follows：后续工序
- measures：测量指标
- controls：控制指标
- provides_basis_for：产生依据
- composed_of：由……组成
- assembled_with：连接/装配
- located_at：位置关系
- causes：导致
- checks：检查/评估
- repairs：修理对象
```

## 3. 用户输入模板

```text
请从以下教材片段中抽取知识图谱三元组。

source_chunk: {{chunk_id}}
source_page: {{page_start}}
chapter_hint: {{chapter_hint}}

文本：
{{text}}

输出 JSON 格式：
{
  "entities": [
    {
      "name": "实体名称",
      "type": "实体类型",
      "aliases": [],
      "definition": "基于原文的一句话定义，没有则为空字符串",
      "source_page": 页码,
      "source_chunk": "chunk id",
      "confidence": 0.0
    }
  ],
  "triples": [
    {
      "head": "头实体名称",
      "head_type": "头实体类型",
      "relation": "关系类型",
      "tail": "尾实体名称",
      "tail_type": "尾实体类型",
      "evidence": "支持该三元组的原文短句",
      "source_page": 页码,
      "source_chunk": "chunk id",
      "confidence": 0.0
    }
  ]
}
```

## 4. 少样本示例

输入：

```text
source_chunk: shiprag_p008_00008
source_page: 8
chapter_hint: 第一章工艺基础及相关工种知识

文本：
激光经纬仪是船厂广泛使用的精密光学测量仪器。在船体建造过程中,它可以用来完成各种测量和画线工作:在船台、平台和分段上画基准线;画完工分段上的预修整余量线;作为准直线测量结构的直线度;形成铅垂面测结构垂直度。
```

输出：

```json
{
  "entities": [
    {
      "name": "激光经纬仪",
      "type": "ToolEquipment",
      "aliases": [],
      "definition": "船厂广泛使用的精密光学测量仪器。",
      "source_page": 8,
      "source_chunk": "shiprag_p008_00008",
      "confidence": 0.94
    },
    {
      "name": "船体建造",
      "type": "Process",
      "aliases": [],
      "definition": "",
      "source_page": 8,
      "source_chunk": "shiprag_p008_00008",
      "confidence": 0.88
    },
    {
      "name": "直线度",
      "type": "Measurement",
      "aliases": [],
      "definition": "",
      "source_page": 8,
      "source_chunk": "shiprag_p008_00008",
      "confidence": 0.9
    },
    {
      "name": "垂直度",
      "type": "Measurement",
      "aliases": [],
      "definition": "",
      "source_page": 8,
      "source_chunk": "shiprag_p008_00008",
      "confidence": 0.9
    }
  ],
  "triples": [
    {
      "head": "激光经纬仪",
      "head_type": "ToolEquipment",
      "relation": "used_for",
      "tail": "船体建造",
      "tail_type": "Process",
      "evidence": "在船体建造过程中,它可以用来完成各种测量和画线工作",
      "source_page": 8,
      "source_chunk": "shiprag_p008_00008",
      "confidence": 0.92
    },
    {
      "head": "激光经纬仪",
      "head_type": "ToolEquipment",
      "relation": "measures",
      "tail": "直线度",
      "tail_type": "Measurement",
      "evidence": "作为准直线测量结构的直线度",
      "source_page": 8,
      "source_chunk": "shiprag_p008_00008",
      "confidence": 0.9
    },
    {
      "head": "激光经纬仪",
      "head_type": "ToolEquipment",
      "relation": "measures",
      "tail": "垂直度",
      "tail_type": "Measurement",
      "evidence": "形成铅垂面测结构垂直度",
      "source_page": 8,
      "source_chunk": "shiprag_p008_00008",
      "confidence": 0.9
    }
  ]
}
```

## 5. 质量检查 Prompt

```text
你是知识图谱质量审核智能体。请检查输入的实体和三元组是否符合以下规则：
1. 实体类型是否在本体范围内。
2. 关系类型是否在允许列表中。
3. evidence 是否能支持该三元组。
4. 是否存在明显 OCR 错字导致的实体名称错误。
5. 是否存在重复三元组或方向错误。

请输出合法 JSON：
{
  "valid_triples": [],
  "rejected_triples": [
    {
      "triple": {},
      "reason": "剔除原因"
    }
  ],
  "entity_normalization": [
    {
      "raw": "原实体名",
      "normalized": "规范实体名",
      "reason": "规范化原因"
    }
  ]
}
```

