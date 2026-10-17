# Agent 材料接入约定

Markdown 和 JSON 都可以由具备文件读取工具的 Agent 消费；只把路径发给无文件访问权限的模型，不会自动读取文件。业务后端应读取文件内容或提供受控读取工具。

## 两种输出的职责

- Markdown：理解材料、检索段落、查看表格。XLS/XLSX 保留原始行列，不猜业务表头。
- evidence JSON：程序解析原值、类型、合并范围及来源坐标；查看原件/结果哈希、工具版本及覆盖限制。
- `source.sha256 + sheet.name + cell.coordinate`：Excel 字段的来源引用组合。原件路径仍应由业务系统关联；哈希本身不能代替原件存储。
- 原表的“合格”“不做判断”只是原始字段内容，不是本程序的审查结论。`converted_requires_review` 也不能作为业务通过状态。

## 后端调用

```python
import hashlib
import json
from tomarkdown import convert

result = convert(material_path, evidence=True)
if result.errors:
    # 将错误交给任务系统；不要把失败材料作为已完成输入。
    raise RuntimeError(result.errors)

for source, metadata_path in result.evidence_files.items():
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    markdown_path = metadata_path.parent / metadata["output"]["name"]
    markdown_bytes = markdown_path.read_bytes()
    assert hashlib.sha256(markdown_bytes).hexdigest() == metadata["output"]["sha256"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == metadata["source"]["sha256"]
    markdown = markdown_bytes.decode("utf-8")
    # 由项目一的编排服务将 markdown、metadata 和当前业务规则交给 Agent。
```

大文件的哈希可流式计算；上面仅展示接入逻辑。读取期间若任务结果正在更新，校验不一致应重试/报告，而非继续使用。不要只扫描目录中的旧结果推断本次任务成功。

## Excel 字段读取

```python
document = metadata.get("document") or {}
for sheet in document.get("sheets", []):
    cells = {cell["coordinate"]: cell for cell in sheet["cells"]}
    # 示例：读取工作表中的 G2；不假定所有台账都用同一列。
    cell = cells.get("G2")
    if cell and cell.get("visibility") != "covered_by_merge":
        evidence = {
            "source_sha256": metadata["source"]["sha256"],
            "sheet": sheet["name"],
            "coordinate": cell["coordinate"],
            "value": cell["value"],
        }
```

合并延续位置没有新增值时，应根据 `merged_ranges` 回到左上角锚点；不能对所有空白向下填充。`covered_by_merge` 是原件底层存储的遮盖值，必须区别于显示事实，有差异交人工复核。

## OCR 路径

- `ocr=True`：允许在需要时调用图片识别，不强制将原生文字发送给模型。
- XLSX 单元格通过 openpyxl 读取；支持的嵌入光栅图片才做 OCR。XLS 单元格通过 xlrd 读取；旧格式的媒体暂未提取。
- 纯文字 XLS/XLSX 不初始化模型、不要求 API Key、`ocr_requests == 0`。
- `configuration.ocr=true` 是配置许可，不是实际调用记录。`result.ocr_requests` 是整个调用的请求统计；来源记录中的模型名也不是“每个字段均由此模型识别”的证明。

## 项目一边界

转换器可提供字段提取和比对的输入。项目一还需要材料分类、台账字段映射、规范版本和条款、确定性比较、未知项处理及专家复核。检测报告 PDF 的表格框、图像实体及样品关联还未完成验证，不能将文本齐全等同于关系准确。

XLS 的日期、布尔值、前导零格式和隐藏状态会保留，但公式仅有缓存值；XLS 内嵌图片尚未覆盖。Agent 必须读取 `warnings`，以及 `location_granularity`、`document.formula_support`、`document.media_support` 和各媒体项状态描述的覆盖范围，不得将未覆盖内容解释为“不存在”。
