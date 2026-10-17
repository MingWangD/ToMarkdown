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
    parser.add_argument("--workers", type=int, default=4, help="OCR 全局并发上限，默认 4；设为 1 使用串行")
    parser.add_argument("--timeout", type=float, default=600.0, help="单次请求超时秒数，默认 600")
    parser.add_argument("--max-retries", type=int, default=2, help="失败请求的最大重试次数，默认 2")
    parser.add_argument("--evidence", action="store_true", help="输出来源 JSON，保留输入扩展名以区分同名材料")
    args = parser.parse_args()
    try:
        result = convert(
            args.file,
            ocr=not args.no_ocr,
            model=args.model,
            base_url=args.base_url,
            results_dir=results_dir,
            show_progress=True,
            workers=args.workers,
            timeout=args.timeout,
            max_retries=args.max_retries,
            evidence=args.evidence,
        )
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    if not result.files and not result.errors:
        print("文件夹中没有可转换的文件。")
    else:
        print(f"处理结束：成功 {len(result.files)} 个，失败 {len(result.errors)} 个。")
    if not args.no_ocr and (result.files or result.errors):
        print(f"OCR 请求 {result.ocr_requests} 次，复用 {result.ocr_cache_hits} 次，总耗时 {result.elapsed_seconds:.1f}s。")
    return 1 if result.errors else 0
