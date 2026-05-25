# 基于 openPangu 7B 的船体装配知识图谱构建说明

## 1. 完成情况评估

根据课程报告要求，当前项目已完成数据预处理、知识图谱本体设计、Pangu 大模型实体关系抽取、图谱后处理、Neo4j 存储与管理等核心任务。

| 要求 | 完成情况 | 主要证据 |
|---|---|---|
| 数据预处理：格式转换、清洗 | 已完成 | `data/processed/ship_textbook_pages.cleaned.jsonl`、`ship_textbook.cleaned.md`、`ship_textbook_chunks.jsonl` |
| 定义知识图谱本体 | 已完成 | `docs/kg_design/ontology_design.md` |
| 使用 Pangu 设计实体识别和关系抽取指令与智能体 | 已完成 | `pangu/prompts/kg_extraction_prompt.md`、`pangu/extract_triples.py`、`pangu/build_graph_data.py` |
| 使用 7B 或以下 openPangu 模型抽取整本书三元组 | 已完成 | 远程 openPangu 7B 服务，`pangu/outputs/raw_extractions.jsonl` |
| 形成连接紧密的知识图谱 | 已完成 | 通过实体归一化、关系过滤、三元组去重、章节连接增强实现 |
| Neo4j 存储与管理 | 已完成 | `pangu/import_neo4j.py` 已清空旧图谱并导入新图谱 |
| 展示部分知识图谱可视化结果 | 数据与查询已准备 | 第 9 节给出 Neo4j Browser 可视化查询语句 |

最终结果：

```text
预处理页数：192
文本 chunk：230
参与 Pangu 抽取的有效 chunk：224
Pangu 最终成功抽取 chunk：213
最终失败 chunk：11
最终抽取覆盖率：95.1%
原始实体数：846
原始三元组数：762
规范化实体数：1003
规范化关系数：1747
Neo4j 节点数：1003
Neo4j 关系数：1700
```

## 2. 数据预处理实现

原始语料为：

```text
中级船体装配工工艺学_11934890.pdf
```

该 PDF 是扫描图像型文档，无法直接抽取文本。因此预处理采用 OCR 方案：

1. 使用 PyMuPDF 读取 PDF 页面。
2. 将每页渲染为图像。
3. 使用 RapidOCR 对中文扫描页进行 OCR 识别。
4. 对 OCR 文本进行清洗：
   - 删除页码、空行和明显无意义字符。
   - 规范空白符。
   - 合并断行。
   - 保留页码、行文本和 OCR 置信度，便于追溯。
5. 将清洗后的文本切分为适合大模型输入的 chunk。

预处理输出：

| 文件 | 说明 |
|---|---|
| `data/processed/ship_textbook_pages.cleaned.jsonl` | 逐页 OCR 与清洗结果 |
| `data/processed/ship_textbook.cleaned.md` | 按页组织的 Markdown 全文 |
| `data/processed/ship_textbook_chunks.jsonl` | 用于 Pangu 抽取和后续 RAG 的文本块 |
| `data/processed/preprocess_metadata.json` | 预处理元数据和统计信息 |

预处理统计：

```text
PDF 总页数：192
已处理页数：192
清洗后总字符数：122270
文本 chunk 数：230
平均 OCR 置信度：0.808
```

对应脚本：

```text
scripts/preprocess_ship_pdf.py
```

复现命令：

```powershell
python scripts\preprocess_ship_pdf.py --zoom 1.2 --out-dir data\processed
```

## 3. 知识图谱本体设计

知识图谱本体面向船体装配工艺领域，目标是表达教材中的工艺对象、船体构件、工具设备、测量指标、工艺流程、质量要求和缺陷修理等知识。

实体类型包括：

| 实体类型 | 说明 |
|---|---|
| Chapter | 章节、节、知识单元 |
| ProcessObject | 工艺对象，如船体、分段、底部分段、舷侧分段 |
| Component | 船体构件，如肋骨、甲板、舱壁、外板 |
| Process | 工艺过程，如船体放样、分段装配、船体总装配、船体修理 |
| Operation | 工序或操作，如划线、定位、测量、吊装、合拢 |
| ToolEquipment | 工具设备，如激光经纬仪、胎架、卷尺、线锤 |
| Measurement | 测量对象或指标，如高度、宽度、垂直度、直线度 |
| Parameter | 工艺参数、基准、公式、施工条件 |
| Material | 材料或介质 |
| QualityRequirement | 质量要求或检查项 |
| Defect | 问题或缺陷 |
| StandardSafety | 标准、安全规范 |

关系类型包括：

```text
contains, belongs_to, used_for, uses_tool, operates_on,
precedes, follows, measures, controls, provides_basis_for,
composed_of, assembled_with, located_at, causes, checks, repairs
```

本体设计文件：

```text
docs/kg_design/ontology_design.md
```

## 4. Pangu 大模型指令与智能体设计

本项目使用远程部署的 openPangu 7B 模型完成实体识别和关系抽取。服务测试结果如下：

```json
{"status":"ok","cuda":true,"device":"NVIDIA GeForce RTX 3090"}
```

Pangu 抽取提示词位于：

```text
pangu/prompts/kg_extraction_prompt.md
```

提示词约束包括：

1. 只根据输入文本抽取，不编造。
2. 只输出合法 JSON。
3. 实体类型必须来自本体。
4. 关系类型必须来自预定义关系集合。
5. 每条三元组保留证据、来源页码、来源 chunk 和置信度。
6. 优先抽取能形成图谱连接的知识，如工艺流程、工具用途、构件关系、测量指标、质量控制等。
7. 过滤目录、出版社、ISBN 等非领域知识。
8. 控制每个 chunk 的输出数量，避免生成过长 JSON。

智能体/模块设计：

| 模块 | 作用 |
|---|---|
| ExtractionAgent | 调用 Pangu 从 chunk 中抽取实体和三元组 |
| RetryAgent | 对第一次失败 chunk 使用极简 Prompt 进行二次补抽 |
| NormalizeAgent | 对实体名称进行规范化，修正部分 OCR 错字 |
| ReviewAgent | 过滤低置信度或关系类型不合法的三元组 |
| GraphBuilder | 补充章节连接关系，增强图谱连通性 |
| Neo4jImporter | 清空旧图谱并导入新图谱 |

相关实现：

```text
pangu/extract_triples.py
pangu/retry_failed_minimal.py
pangu/compact_raw_extractions.py
pangu/build_graph_data.py
pangu/import_neo4j.py
```

## 5. 第一次 Pangu 全书抽取

抽取输入为：

```text
data/processed/ship_textbook_chunks.jsonl
```

由于封面、出版信息和目录页不属于船体装配领域知识，抽取脚本会跳过明显的前置信息页。最终参与抽取的有效 chunk 数为 224。

第一次抽取命令：

```powershell
python pangu\extract_triples.py --all --max-input-chars 500
```

第一次抽取结果：

```text
有效 chunk 总数：224
成功抽取 chunk：186
失败 chunk：38
第一次覆盖率：83.0%
原始三元组数：717
```

第一次失败的主要原因不是 Pangu 服务不可用，而是模型在部分文本块上输出的 JSON 不完整，例如缺少结尾括号、逗号或字段引号，导致本地程序无法解析。失败记录仍保存在 `raw_extractions.jsonl` 中，便于定位和二次补抽。

## 6. 第二次失败 chunk 补抽

为了提高整本书覆盖率，项目对第一次失败的 38 个 chunk 进行了第二次补抽。第二次补抽没有重新抽取全部文本，而是只针对失败 chunk 进行处理。

第二次补抽采用了更严格、更短的极简 Prompt：

1. 每个失败 chunk 只截取前 220 个字符。
2. 每个 chunk 最多输出 2 条最重要三元组。
3. 不要求模型输出 definition，减少 JSON 长度。
4. 明确要求只返回一行合法 JSON。
5. 使用 `json5` 对轻微格式问题进行兼容解析。

对应脚本：

```text
pangu/retry_failed_minimal.py
pangu/compact_raw_extractions.py
```

第二次补抽命令：

```powershell
python pangu\retry_failed_minimal.py --max-input-chars 220 --max-new-tokens 260
python pangu\compact_raw_extractions.py
```

第二次补抽效果：

```text
补抽前成功 chunk：186
补抽前失败 chunk：38
补抽后成功 chunk：213
补抽后失败 chunk：11
覆盖率从 83.0% 提升到 95.1%
原始三元组数从 717 提升到 762
```

最终原始抽取结果：

```text
pangu/outputs/raw_extractions.jsonl
```

说明：仍有 11 个 chunk 失败，主要原因仍是模型输出格式不稳定或 OCR 文本质量较差。由于失败比例已经较低，且成功 chunk 已覆盖整本书主要章节，因此当前结果可以支撑后续图谱构建和报告展示。

## 7. 高质量图谱构建

为了避免图谱只是松散三元组堆叠，项目在 Pangu 原始抽取结果基础上进行了后处理：

1. 实体规范化：
   - 删除空实体、过长实体、出版信息实体。
   - 对 OCR 错字进行归一，例如将“航侧分段、触侧分段、眩侧分段”等统一为“舷侧分段”。
2. 关系规范化：
   - 只保留本体中定义的关系类型。
   - 将中文关系名映射为英文关系类型。
3. 三元组去重：
   - 对相同头实体、关系、尾实体进行合并。
4. 章节连接增强：
   - 增加“教材-章节”和“章节-实体”的 `contains` 关系。
   - 使实体挂接到章节知识单元上，提高图谱连通性。
5. 低质量过滤：
   - 过滤低置信度实体和关系。
   - 过滤无效出版信息、页码、ISBN 等。

构建命令：

```powershell
python pangu\build_graph_data.py
```

规范化后图谱统计：

```text
实体数：1003
关系数：1747
孤立实体数：33
```

实体类型分布：

```text
Component: 290
ProcessObject: 156
Process: 150
Operation: 94
Parameter: 71
ToolEquipment: 70
Measurement: 63
QualityRequirement: 48
Defect: 26
Chapter: 22
Material: 7
StandardSafety: 6
```

关系类型分布：

```text
contains: 1160
uses_tool: 106
assembled_with: 74
precedes: 72
used_for: 68
measures: 44
composed_of: 39
operates_on: 39
located_at: 38
controls: 27
causes: 26
follows: 16
belongs_to: 13
provides_basis_for: 11
repairs: 8
checks: 6
```

输出文件：

```text
pangu/outputs/graph/entities.jsonl
pangu/outputs/graph/relations.jsonl
pangu/outputs/graph/entities.csv
pangu/outputs/graph/relations.csv
pangu/outputs/graph/summary.json
```

## 8. Neo4j 存储与管理

图谱使用 Neo4j 存储。每个实体统一保存为 `Entity` 节点，并根据实体类型增加对应标签，例如：

```text
:Entity:Component
:Entity:Process
:Entity:ToolEquipment
:Entity:Measurement
```

关系使用大写英文关系类型，例如：

```text
CONTAINS
USES_TOOL
USED_FOR
MEASURES
ASSEMBLED_WITH
PRECEDES
```

导入前执行清空操作：

```cypher
MATCH (n) DETACH DELETE n
```

导入命令：

```powershell
python pangu\import_neo4j.py --clear
```

Neo4j 当前导入结果：

```text
节点数：1003
关系数：1700
```

关系文件中有 1747 条关系，而 Neo4j 中实际导入 1700 条关系，是因为导入时使用 `MERGE` 对重复的“头实体-关系-尾实体”进行了合并，这是去重后的正常结果。

## 9. Neo4j 可视化展示建议

报告中需要展示部分知识图谱可视化结果。当前图谱已经导入 Neo4j，可以在 Neo4j Browser 中运行以下查询并截图。

### 9.1 工具设备与测量指标

```cypher
MATCH p=(a:ToolEquipment)-[r:MEASURES|USED_FOR|USES_TOOL]-(b)
RETURN p
LIMIT 50;
```

### 9.2 船体分段装配相关知识

```cypher
MATCH p=(a)-[r]-(b)
WHERE a.name CONTAINS "分段" OR b.name CONTAINS "分段"
RETURN p
LIMIT 80;
```

### 9.3 章节与领域实体连接

```cypher
MATCH p=(c:Chapter)-[:CONTAINS]->(e:Entity)
RETURN p
LIMIT 100;
```

### 9.4 高连接实体统计

```cypher
MATCH (n:Entity)-[r]-()
RETURN n.name AS name, n.type AS type, count(r) AS degree
ORDER BY degree DESC
LIMIT 20;
```

### 9.5 核心实体邻域

```cypher
MATCH p=(n:Entity {name:"激光经纬仪"})-[r]-(m)
RETURN p;
```

也可以替换为：

```cypher
MATCH p=(n:Entity {name:"胎架"})-[r]-(m)
RETURN p;
```

## 10. 实现内容总结

本阶段实现了从扫描版教材到 Neo4j 知识图谱的完整流程：

1. 将扫描 PDF 转换为 OCR 文本。
2. 对文本进行清洗、分页保存和 chunk 切分。
3. 设计船体装配领域知识图谱本体。
4. 设计 Pangu 大模型抽取 Prompt 和智能体流水线。
5. 调用远程部署的 openPangu 7B 模型进行第一次整本书抽取。
6. 针对第一次失败 chunk 进行第二次极简 Prompt 补抽。
7. 对抽取结果进行实体归一化、关系过滤、三元组去重和章节连接增强。
8. 将最终图谱导入 Neo4j，并清空了旧图谱。
9. 生成了可用于报告、可视化和后续 RAG 的实体表、关系表和 JSONL 数据。

## 11. 当前不足与后续优化

当前系统已经完成核心要求，但仍有优化空间：

1. 仍有 11 个 chunk 出现 JSON 格式错误，后续可继续人工修正或再次补抽。
2. OCR 文本中仍有少量识别错误，会影响实体名称质量。
3. 部分实体仍存在粒度不一致问题，例如同一概念可能被抽为 `ProcessObject` 或 `ToolEquipment`。
4. 后续可以加入人工复核环节，对高频实体和核心关系进行人工校正。
5. 可以进一步基于 Neo4j 图谱构建 RAG 问答系统，实现课程要求中的高分扩展目标。

## 12. 复现命令汇总

数据预处理：

```powershell
python scripts\preprocess_ship_pdf.py --zoom 1.2 --out-dir data\processed
```

第一次 Pangu 全书抽取：

```powershell
python pangu\extract_triples.py --all --max-input-chars 500
```

第二次失败 chunk 补抽：

```powershell
python pangu\retry_failed_minimal.py --max-input-chars 220 --max-new-tokens 260
python pangu\compact_raw_extractions.py
```

构建图谱数据：

```powershell
python pangu\build_graph_data.py
```

清空 Neo4j 并导入图谱：

```powershell
python pangu\import_neo4j.py --clear
```

