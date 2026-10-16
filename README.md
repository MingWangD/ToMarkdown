# Ming ToMarkdown

将 PDF、Word、Excel、PowerPoint、图片和文本文件转换为 Markdown 的 Python 包，支持终端命令和 Python 调用。

安装包名为 `ming-tomarkdown`，终端命令和 Python 导入名仍为 `tomarkdown`。GitHub 仓库名称保持 `ToMarkdown`。

默认开启图片 OCR：正文文字直接提取，图片交给视觉模型识别，再合并为 Markdown。OCR 请求默认最多 4 个并发，保留原有图片尺寸，不缩图、不截短输出。支持单文件和混合格式文件夹，批量转换会保留输入文件夹名称。

## 安装

需要 Python 3.12 或更高版本。在已有虚拟环境中，从 PyPI 安装：

```bash
uv pip install ming-tomarkdown
```

也可以使用 pip：

```bash
python -m pip install ming-tomarkdown
```

尚未创建虚拟环境时，先执行 `uv venv --python 3.12` 并激活环境。macOS / Linux 使用 `source .venv/bin/activate`，Windows PowerShell 使用 `.venv\Scripts\Activate.ps1`。

也可以直接安装 GitHub 发布的 wheel，无需 Git：

```bash
uv pip install "https://github.com/MingWangD/ToMarkdown/releases/download/v0.1.3/ming_tomarkdown-0.1.3-py3-none-any.whl"
```

也可以通过 pip 从 GitHub 源码安装：

```bash
python -m pip install "ming-tomarkdown @ git+https://github.com/MingWangD/ToMarkdown.git@v0.1.3"
```

这种安装方式需要本机已有 Git。也可以从仓库的 [Releases](https://github.com/MingWangD/ToMarkdown/releases) 下载 `.whl`，直接安装，无需 Git：

```bash
python -m pip install ./ming_tomarkdown-0.1.3-py3-none-any.whl
```

仅使用终端命令，也可以用 uv 安装：

```bash
uv tool install ming-tomarkdown
```

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

文件夹只处理当前层，按文件名排序读取，不进入子文件夹，跳过不支持的扩展名。开启 OCR 时最多同时处理 4 个文件，仍按文件名顺序写入，保留上述同名覆盖规则。终端显示文件序号、总耗时、OCR 请求数、复用次数及成功/失败数量，不显示页数或百分比；存在转换失败时命令以非零状态退出。

## 命令参数

| 参数 | 说明 |
| --- | --- |
| `file` | 文件或文件夹路径，必填 |
| `--model` | 指定视觉模型，覆盖环境变量 |
| `--base-url` | 指定 OpenAI 兼容接口基础地址，覆盖环境变量 |
| `--no-ocr` | 关闭 OCR，不调用模型；默认开启 OCR |
| `--workers` | 全部文件与 PDF 图片共享的 OCR 请求并发上限，默认 4，范围 1–32；1 为串行 |
| `--timeout` | 单次请求超时秒数，默认 600；不是整份文档的时间限制 |
| `--max-retries` | SDK 对可重试请求的重试上限，默认 2；0 为不重试 |
| `-h`、`--help` | 查看帮助 |

```bash
tomarkdown "/路径/文档.pdf" --model "你的视觉模型名称"
tomarkdown "/路径/资料" --no-ocr
tomarkdown --help
```

## OCR 提速与完整性

```bash
# 多页 PDF：并发识别图片，保持页序和图文顺序
tomarkdown "/路径/论文.pdf" --workers 4

# 文件夹：文件并发与 PDF 内图片共用同一个请求上限
tomarkdown "/路径/资料" --workers 4

# 服务限流或排查问题时，退回串行
tomarkdown "/路径/资料" --workers 1
```

Python 调用使用相同参数：`convert(path, workers=4, timeout=600, max_retries=2)`。

- PDF 只打开一次，顺序提取图片及版面，仅模型请求并发执行。PDF 渲染在整个进程内串行，避免渲染库的线程安全问题。
- 同一次 `convert()` 中，相同模型、提示词和图片请求共享结果；同时到达的重复请求也只发送一次。最多保留 128 个成功响应，失败不缓存。缓存不写磁盘，下次运行重新识别。
- 独立图片按原字节发送，不缩小、不重新压缩、不跳过小图；PDF 延用插件的图片提取策略，无法提取的区域按既有策略渲染，整页后备识别使用 300 DPI。保持完整提取提示词，不人为限制输出长度，不自动切换模型。
- 文件及 PDF 请求使用有界任务窗口，但单页图片仍一次性提取，因此高分辨率、多图片文件的内存占用取决于页内容；网络并发上限不等于驻留图片上限。
- 单张首次识别仍取决于服务和模型响应；并发不会缩短单个请求的推理时间。优先保证输入信息完整，不以缩图换速度。LLM 识别内容是否完整仍需核对原文。

`ConversionResult` 增加 `ocr_requests`、`ocr_cache_hits` 和 `elapsed_seconds`。请求数按 SDK 调用计数，不含 SDK 内部重试；总耗时包含文件处理。默认 4 是起点，服务只支持单请求或出现明显限流时使用 `--workers 1`。

验证方式：

```bash
uv run python -m unittest discover -s tests -v
uv run python tests/benchmark_ocr.py
```

第二条命令用固定延迟的假模型验证调度与输出一致性，不访问外部服务。实际审查及本次实测见 [OCR 优化审查报告](https://github.com/MingWangD/ToMarkdown/blob/main/docs/ocr-review.md)。

## 支持的内容与处理流程

支持 PDF、Word（`.docx`）、Excel（`.xlsx`、`.xls`）、PowerPoint（`.pptx`）、图片、HTML，以及 TXT、CSV、JSON、XML 等文本格式。旧版 Word `.doc` 不在批量处理范围内。

```text
这一页 PDF
├── 文字层 → 直接提取
└── 图片   → LLM 识别
                ↓
          合并成 Markdown
```

扫描件中的正文通常属于图片，需要 OCR。复杂排版、表格和公式的还原取决于文件内容、MarkItDown 插件及模型。JSON、XML 等文本主要保留原文。模型请求异常、明确拒答或输出截断会计入该文件失败，不写入新的不完整结果；其他文件继续处理。合法无字图片可以返回空文本。插件内部的图片提取/解析错误仍可能影响内容完整性，模型本身也可能漏识。

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

## 维护者：首次发布到 PyPI

仓库提供 `.github/workflows/publish.yml`，通过 GitHub Actions 可信发布，无需配置 PyPI API Token。

首次使用时，登录 PyPI 并打开[账号的 Publishing 页面](https://pypi.org/manage/account/publishing/)，添加 GitHub 待发布项目，填写：

| 字段 | 值 |
| --- | --- |
| PyPI Project Name | `ming-tomarkdown` |
| Owner | `MingWangD` |
| Repository name | `ToMarkdown` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

保存后，在 GitHub Actions 的 **Publish to PyPI** 流程中选择 **Run workflow**，勾选 **Publish to PyPI after building** 即可发布；不勾选时仅检查构建。此后发布新的 GitHub Release 也会自动触发 PyPI 发布。发布新版本前需先更新 `pyproject.toml` 中的版本号及依赖锁定文件。

首次发布成功后，其他人就可以用 `uv pip install ming-tomarkdown` 安装。
