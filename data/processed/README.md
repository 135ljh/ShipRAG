# 数据预处理产物说明

源文件：`中级船体装配工工艺学_11934890.pdf`

该 PDF 为扫描图像型文档，无法直接抽取文本。本次预处理使用 PyMuPDF 将页面渲染为图像，再使用 RapidOCR 进行中文 OCR 识别，并对识别文本进行了基础清洗、页码过滤、空白规范化和 RAG 分块。

## 输出文件

- `ship_textbook_pages.cleaned.jsonl`：逐页清洗结果，每行对应 1 页，包含页码、清洗文本、行文本、字符数、OCR 置信度等字段。
- `ship_textbook_chunks.jsonl`：面向知识抽取和 RAG 的分块数据，每行对应 1 个文本块，包含来源、页码范围、章节提示、文本和字符数。
- `ship_textbook.cleaned.md`：按页组织的 Markdown 文本，便于人工阅读和检查。
- `preprocess_metadata.json`：预处理元数据，包含页数、处理工具、字符数、分块数和平均 OCR 置信度。

## 处理结果

- 总页数：192 页
- 已处理页数：192 页
- 清洗后总字符数：122270
- RAG/知识抽取分块数：230
- 平均 OCR 置信度：0.808

## 复现命令

```powershell
python scripts\preprocess_ship_pdf.py --zoom 1.2 --out-dir data\processed
```

脚本支持断点续跑：如果 `ship_textbook_pages.cleaned.jsonl` 中已经存在某些页，再次运行时会自动跳过已处理页面。
