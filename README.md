# ToMarkdown

将 PDF、Word、Excel、PowerPoint、图片和文本文件转换为 Markdown 的命令行工具。

默认开启图片 OCR：正文文字直接提取，图片交给视觉模型识别，再合并为 Markdown。单文件结果直接保存到项目的 `results/`，文件夹批量转换则保存到 `results/输入文件夹名/`。保留源文件名，扩展名改为 `.md`。

## 处理流程

```text
这一页 PDF
├── 文字层 → 直接提取
└── 图片   → LLM 识别
                ↓
          合并成 Markdown
                ↓
       保存到 results 下
```

扫描件中的正文通常属于图片，需要 OCR。复杂排版、表格和公式的转换效果取决于文件内容与模型能力。

## 安装

需要 Python 3.12 或更高版本，以及 uv。在项目目录执行：

```bash
uv sync
```

## 通用配置方法

使用支持图片输入、兼容 OpenAI Chat Completions 接口的模型服务。在项目根目录创建或编辑 `.env`，填写以下三项：

```dotenv
OPENAI_API_KEY=服务提供的_API_Key
OPENAI_MODEL=服务支持的视觉模型名称
OPENAI_BASE_URL=服务提供的_OpenAI_兼容接口基础地址
```

| 配置项 | 含义 |
| --- | --- |
| `OPENAI_API_KEY` | 调用所选服务使用的密钥 |
| `OPENAI_MODEL` | 该服务支持的视觉模型标识，必须支持图片输入 |
| `OPENAI_BASE_URL` | 接口基础地址，填写服务文档提供的地址，不追加 `/chat/completions` |

这里的 `OPENAI_` 是脚本读取的变量名称，不限定模型提供商。密钥、模型和接口地址需要对应同一个可用服务。

脚本也兼容旧配置 `GEMINI_API_KEY` 和 `GEMINI_MODEL`，且旧配置优先。改用上面的通用配置时，请删除或清空旧配置，避免覆盖新设置。脚本自动读取项目目录下的 `.env`；同名系统环境变量优先于 `.env`。

配置完成后，在项目目录运行：

```bash
uv run python to_md.py "/路径/源文件.pdf"
```

默认启用 OCR，无需额外添加开启参数。

## 具体例子

假设本地已经启动一个 OpenAI 兼容服务，地址是 `http://127.0.0.1:8045/v1`，服务中提供的视觉模型标识为 `vision-model`，要转换的文件是 `/Users/myw/Desktop/论文.pdf`。

在 `.env` 中填写：

```dotenv
OPENAI_API_KEY=你的本地服务密钥
OPENAI_MODEL=vision-model
OPENAI_BASE_URL=http://127.0.0.1:8045/v1
```

`vision-model` 是示例标识，需要替换成你的服务实际提供的视觉模型名称；密钥也需要替换。

在项目目录执行：

```bash
uv run python to_md.py "/Users/myw/Desktop/论文.pdf"
```

输出文件为：

```text
/Users/myw/Desktop/ToMarkdown/results/论文.md
```

终端会显示处理状态、耗时和保存位置。

## 常用命令

以下命令均在项目目录执行，文件路径按实际情况替换：

```bash
# 默认开启 OCR，转换 PDF
uv run python to_md.py "/路径/文档.pdf"

# 批量转换文件夹中的混合格式文件，默认开启 OCR
uv run python to_md.py "/路径/资料文件夹"

# 转换 Word、Excel、PowerPoint 或图片
uv run python to_md.py "/路径/报告.docx"
uv run python to_md.py "/路径/数据.xlsx"
uv run python to_md.py "/路径/演示.pptx"
uv run python to_md.py "/路径/截图.png"

# 临时指定模型，覆盖环境变量中的模型配置
uv run python to_md.py "/路径/文档.pdf" --model "服务支持的视觉模型名称"

# 关闭 OCR，仅进行常规提取，不需要 API Key 或模型配置
uv run python to_md.py "/路径/文档.pdf" --no-ocr

# 查看帮助
uv run python to_md.py --help
```

## 文件夹批量转换

文件夹可以同时包含 PDF、Word、Excel、图片等文件，直接传入文件夹路径即可：

```bash
uv run python to_md.py "/Users/myw/Desktop/资料"
```

例如：

```text
资料/                         项目的 results/资料/
├── 论文.pdf       →          ├── 论文.md
├── 报告.docx      →          ├── 报告.md
└── 数据.xlsx      →          └── 数据.md
```

脚本按文件名排序，逐个转换当前文件夹内支持的文件，不进入子文件夹，跳过不支持的扩展名。Word 请使用 `.docx`，旧版 `.doc` 不在批量处理范围内。

终端显示 `[当前文件序号/总数]`、每个文件的耗时和最终成功、失败数量。某个文件抛出转换错误时会显示错误并继续处理其他文件；存在失败时，命令以非零状态退出。OCR 插件内部未抛出的识别错误不在此统计范围内。

批量转换同样支持 `--no-ocr`、`--model` 和 `--base-url`。

## 命令参数

| 参数 | 说明 |
| --- | --- |
| `file` | 输入文件或文件夹路径，必填；文件夹只处理当前层 |
| `--model` | 指定视觉模型，覆盖环境变量中的模型配置 |
| `--base-url` | 指定接口基础地址，覆盖 `OPENAI_BASE_URL`；两者均未设置时使用 `http://127.0.0.1:8045/v1` |
| `--no-ocr` | 关闭 OCR，不调用模型；默认开启 OCR |
| `-h`、`--help` | 查看帮助 |

## 输出说明

- 输出固定放在 `to_md.py` 所在项目的 `results/` 下，与启动命令时所在的目录无关，所需文件夹自动创建。
- 单文件转换直接保存到 `results/`，例如 `报告.v2.pdf` → `results/报告.v2.md`。
- 文件夹批量转换保留输入文件夹名称，例如 `资料/报告.pdf` → `results/资料/报告.md`。
- 同一输出目录下的同名结果会覆盖。例如批量转换中的 `报告.pdf` 和 `报告.docx` 会写入同一个 `报告.md`；不同位置的同名输入文件夹也会共用同一个结果文件夹。
- 支持单文件和文件夹批量转换，文件逐个处理；终端显示文件序号、等待动画和耗时，不显示页数或百分比进度。

## 支持的文件

PDF、Word（`.docx`）、Excel（`.xlsx`、`.xls`）、PowerPoint（`.pptx`）、图片、HTML，以及 TXT、CSV、JSON、XML 等文本格式。

具体提取能力取决于 MarkItDown 及其 OCR 插件。JSON、XML 等文本文件主要保留原文，不会自动重新组织为 Markdown 表格。

## 项目结构

```text
ToMarkdown/
├── to_md.py         # 参数读取、文件转换和结果保存
├── ui.py            # 终端等待动画和耗时显示
├── results/         # 转换后的 Markdown 文件
├── .env             # API Key、模型和接口配置
├── pyproject.toml   # Python 版本和依赖声明
├── uv.lock          # 依赖版本锁定
└── README.md
```
