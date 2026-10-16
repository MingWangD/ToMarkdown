# Ming ToMarkdown

将 PDF、Word、Excel、PowerPoint、图片和文本文件转换为 Markdown 的 Python 包，支持终端命令和 Python 调用。

安装包名为 `ming-tomarkdown`，终端命令和 Python 导入名仍为 `tomarkdown`。GitHub 仓库名称保持 `ToMarkdown`。

默认开启图片 OCR：正文文字直接提取，图片交给视觉模型识别，再合并为 Markdown。支持单文件和混合格式文件夹，批量转换会保留输入文件夹名称。

## 安装

需要 Python 3.12 或更高版本。在已有虚拟环境中，可用 uv 直接安装 GitHub 发布版本，无需 Git：

```bash
uv pip install "https://github.com/MingWangD/ToMarkdown/releases/download/v0.1.1/ming_tomarkdown-0.1.1-py3-none-any.whl"
```

尚未创建虚拟环境时，先执行 `uv venv --python 3.12` 并激活环境。macOS / Linux 使用 `source .venv/bin/activate`，Windows PowerShell 使用 `.venv\Scripts\Activate.ps1`。

也可以通过 pip 从 GitHub 源码安装：

```bash
python -m pip install "ming-tomarkdown @ git+https://github.com/MingWangD/ToMarkdown.git@v0.1.1"
```

这种安装方式需要本机已有 Git。也可以从仓库的 [Releases](https://github.com/MingWangD/ToMarkdown/releases) 下载 `.whl`，直接安装，无需 Git：

```bash
python -m pip install ./ming_tomarkdown-0.1.1-py3-none-any.whl
```

仅使用终端命令，也可以用 uv 安装：

```bash
uv tool install "https://github.com/MingWangD/ToMarkdown/releases/download/v0.1.1/ming_tomarkdown-0.1.1-py3-none-any.whl"
```

当前通过 GitHub 分发，尚未发布到 PyPI，请使用以上安装地址。

旧版 GitHub 包的安装名为 `tomarkdown`，升级前请在对应环境运行 `uv pip uninstall tomarkdown`（或 `python -m pip uninstall tomarkdown`），再安装新包。两者提供相同的导入模块和命令，不应同时安装。

## 快速开始

无需模型配置即可先验证普通转换：

```bash
tomarkdown "/路径/文档.pdf" --no-ocr
```

配置好下一节的 OCR 服务后，直接运行：

```bash
# 单个文件
tomarkdown "/路径/论文.pdf"

# 混合格式文件夹：PDF、Word、Excel 等
tomarkdown "/路径/资料"
```

终端命令不需要先 `import`。如果终端找不到 `tomarkdown`，可以用安装该包的 Python 运行：

```bash
python -m tomarkdown "/路径/资料"
```

## 通用 OCR 配置

使用支持图片输入、兼容 OpenAI Chat Completions 接口的模型服务。在运行命令的目录创建 `.env`：

```dotenv
OPENAI_API_KEY=服务提供的_API_Key
OPENAI_MODEL=服务支持的视觉模型名称
OPENAI_BASE_URL=服务提供的_OpenAI_兼容接口基础地址
```

`OPENAI_` 是变量名称，不限定模型提供商。密钥、模型和接口地址需要对应同一个服务；接口地址不要追加 `/chat/completions`。也可以直接设置系统环境变量，同名系统环境变量优先于 `.env`。

配置优先级：

- 模型：显式参数 → `MODEL` → `OPENAI_MODEL` → `GEMINI_MODEL` → `gemini-3.8-flash-high`。
- 密钥：Python 调用的 `api_key` 参数 → `GEMINI_API_KEY` → `OPENAI_API_KEY`。
- 接口：显式参数 → `OPENAI_BASE_URL` → `http://127.0.0.1:8045/v1`。

最后的模型名和接口地址沿用原项目默认值，不代表你的服务一定提供该模型。使用通用配置时，应填写实际服务信息，并清除不再使用的 `MODEL`、`GEMINI_API_KEY` 等旧值。

### 一个具体例子

假设本地服务已在 `http://127.0.0.1:8045/v1` 启动，提供名为 `vision-model` 的视觉模型。在当前目录的 `.env` 中填写：

```dotenv
OPENAI_API_KEY=你的本地服务密钥
OPENAI_MODEL=vision-model
OPENAI_BASE_URL=http://127.0.0.1:8045/v1
```

`vision-model` 和密钥需要替换为实际值。然后运行：

```bash
tomarkdown "/路径/论文.pdf"
```

结果保存在当前目录下的 `results/论文.md`。

## 在 Python 中调用

```python
from tomarkdown import convert

# 默认开启 OCR，读取当前工作目录的 .env
result = convert("/路径/资料")

for path in result.files:
    print("已保存：", path)

for source, error in result.errors.items():
    print("转换失败：", source, error)
```

也可以直接传入配置：

```python
import os
from tomarkdown import convert

result = convert(
    "/路径/论文.pdf",
    api_key=os.environ["OPENAI_API_KEY"],
    model="你的视觉模型名称",
    base_url="http://127.0.0.1:8045/v1",
    show_progress=True,
)
```

关闭 OCR：

```python
result = convert("/路径/报告.docx", ocr=False)
```

`convert()` 返回 `ConversionResult`：`files` 是成功输出的 `Path` 列表，`errors` 是输入路径到错误信息的字典。单个文件转换失败后会继续处理其他文件；无效输入路径、缺少密钥等配置错误会直接抛出异常。

Python 调用默认不显示终端进度，可用 `show_progress=True` 开启；也可通过 `results_dir="/路径/results"` 指定结果根目录。

## 输出规则

安装包后，命令及 Python 调用默认将结果写入**当前工作目录**的 `results/`，不会写进包的安装目录。所需目录会自动创建。

```text
单文件输入：/路径/论文.pdf
输出：      results/论文.md

文件夹输入：/路径/资料/
            ├── 论文.pdf
            ├── 报告.docx
            └── 数据.xlsx
输出：      results/资料/
            ├── 论文.md
            ├── 报告.md
            └── 数据.md
```

保留源文件名，只把扩展名改为 `.md`，例如 `报告.v2.pdf` → `报告.v2.md`。同一输出目录下的同名结果会覆盖，`报告.pdf` 与 `报告.docx` 也会写入同一个 `报告.md`。

文件夹只处理当前层，按文件名排序逐个转换，不进入子文件夹，跳过不支持的扩展名。终端显示文件序号、耗时及成功/失败数量，不显示页数或百分比；存在转换失败时命令以非零状态退出。

## 命令参数

| 参数 | 说明 |
| --- | --- |
| `file` | 文件或文件夹路径，必填 |
| `--model` | 指定视觉模型，覆盖环境变量 |
| `--base-url` | 指定 OpenAI 兼容接口基础地址，覆盖环境变量 |
| `--no-ocr` | 关闭 OCR，不调用模型；默认开启 OCR |
| `-h`、`--help` | 查看帮助 |

```bash
tomarkdown "/路径/文档.pdf" --model "你的视觉模型名称"
tomarkdown "/路径/资料" --no-ocr
tomarkdown --help
```

## 支持的内容与处理流程

支持 PDF、Word（`.docx`）、Excel（`.xlsx`、`.xls`）、PowerPoint（`.pptx`）、图片、HTML，以及 TXT、CSV、JSON、XML 等文本格式。旧版 Word `.doc` 不在批量处理范围内。

```text
这一页 PDF
├── 文字层 → 直接提取
└── 图片   → LLM 识别
                ↓
          合并成 Markdown
```

扫描件中的正文通常属于图片，需要 OCR。复杂排版、表格和公式的还原取决于文件内容、MarkItDown 插件及模型。JSON、XML 等文本主要保留原文。OCR 插件内部未抛出的识别错误不会计入失败数量。

## 从源码运行与构建

```bash
git clone https://github.com/MingWangD/ToMarkdown.git
cd ToMarkdown
uv sync

# 安装包后的命令入口
uv run tomarkdown "/路径/资料"

# 保留原有脚本入口：读取项目 .env，结果固定保存到项目 results/
uv run python to_md.py "/路径/资料"

# 生成 wheel 和源码包，输出到 dist/
uv build --no-sources
```

核心代码位于 `src/tomarkdown/`。根目录的 `to_md.py` 和 `ui.py` 保留为原有用法的兼容入口。发布包不包含 `.env`、转换结果或本地样例文件。
