"""
将文档转换为 Markdown，可通过 LLM OCR 提取图片中的文字。
这一页 PDF
├── 正文文字 → 直接提取
└── 图片     → llm 识别
                 ↓
          合并成 Markdown
"""


import argparse
import os
import sys
from contextlib import ExitStack
from pathlib import Path

from dotenv import load_dotenv
from markitdown import MarkItDown
from openai import OpenAI

from ui import progress


SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".xls", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp",
    ".html", ".htm", ".txt", ".csv", ".json", ".xml",
}


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    load_dotenv(project_dir / ".env")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="输入文件或文件夹路径（文件夹只处理当前层）")
    parser.add_argument("--no-ocr", action="store_true", help="仅提取正文，不调用模型")
    parser.add_argument(
        "--model",
        default=os.getenv("MODEL", "gemini-3.8-flash-high"),
        help="支持图片输入的模型名称，也可设置 GEMINI_MODEL 或 OPENAI_MODEL",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8045/v1"),
        help="OpenAI 兼容接口地址",
    )
    args = parser.parse_args()
    input_path = args.file.expanduser().resolve()
    output_dir = project_dir / "results"
    if input_path.is_dir():
        output_dir = output_dir / input_path.name
        sources = sorted(
            path for path in input_path.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
    else:
        sources = [input_path]
    if not sources:
        print("文件夹中没有可转换的文件。")
        return

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not args.no_ocr and (not api_key or not args.model):
        parser.error("OCR 需要 API Key 和模型名称；请配置环境变量及 --model，或使用 --no-ocr。")

    failed = 0
    with ExitStack() as stack:
        if args.no_ocr:
            converter = MarkItDown()
        else:
            client = stack.enter_context(OpenAI(base_url=args.base_url, api_key=api_key))
            converter = MarkItDown(
                enable_plugins=True,
                llm_client=client,
                llm_model=args.model,
                llm_prompt=(
                    "提取图片中所有文字，保留原文语言、阅读顺序、标题、表格和公式。"
                    "以 Markdown 输出，公式使用 LaTeX。"
                    "只返回提取的内容，不添加解释，不用代码块包裹全文。"
                ),
            )

        for index, source in enumerate(sources, start=1):
            output = output_dir / f"{source.stem}.md"
            try:
                if source == output:
                    raise ValueError("输入文件不能是 results 中的同名 Markdown 文件。")
                with progress(f"[{index}/{len(sources)}] 正在转换 {source.name}"):
                    result = converter.convert(str(source))
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(result.text_content + "\n", encoding="utf-8")
                print(f"已保存：{output}")
            except Exception as exc:
                failed += 1
                print(f"转换失败：{source.name}：{exc}", file=sys.stderr)

    print(f"处理结束：成功 {len(sources) - failed} 个，失败 {failed} 个。")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
