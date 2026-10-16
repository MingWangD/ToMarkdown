"""tomarkdown 命令入口。"""

import argparse
from pathlib import Path

from .core import convert


def main(*, results_dir: Path | None = None) -> int:
    parser = argparse.ArgumentParser(description="将文件或文件夹转换为 Markdown，默认开启图片 OCR。")
    parser.add_argument("file", type=Path, help="文件或文件夹路径（文件夹只处理当前层）")
    parser.add_argument("--no-ocr", action="store_true", help="仅进行常规提取，不调用模型")
    parser.add_argument("--model", help="视觉模型名称；默认读取 MODEL、OPENAI_MODEL 或 GEMINI_MODEL")
    parser.add_argument("--base-url", help="OpenAI 兼容接口地址，也可设置 OPENAI_BASE_URL")
    args = parser.parse_args()
    try:
        result = convert(
            args.file,
            ocr=not args.no_ocr,
            model=args.model,
            base_url=args.base_url,
            results_dir=results_dir,
            show_progress=True,
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    if not result.files and not result.errors:
        print("文件夹中没有可转换的文件。")
    else:
        print(f"处理结束：成功 {len(result.files)} 个，失败 {len(result.errors)} 个。")
    return 1 if result.errors else 0
