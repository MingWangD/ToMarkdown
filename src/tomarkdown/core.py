"""文件转换与批量转换，可独立于命令行使用。"""

import os
import sys
import math
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, local
from contextlib import ExitStack, nullcontext
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from markitdown import MarkItDown
from openai import OpenAI

from .ui import progress
from .ocr import OCRClient, ordered_window
from .pdf import convert_pdf

# MarkItDown lazily populates a global plugin registry without its own lock.
_CONVERTER_INIT_LOCK = Lock()

OCR_PROMPT = (
    "提取图片中所有文字，保留原文语言、阅读顺序、标题、表格和公式。"
    "以 Markdown 输出，公式使用 LaTeX。"
    "只返回提取的内容，不添加解释，不用代码块包裹全文。"
)

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".xls", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp",
    ".html", ".htm", ".txt", ".csv", ".json", ".xml",
}


@dataclass
class ConversionResult:
    """files 为成功保存的路径，errors 为输入路径与错误信息的对应关系。"""

    files: list[Path] = field(default_factory=list)
    errors: dict[Path, str] = field(default_factory=dict)
    ocr_requests: int = 0
    ocr_cache_hits: int = 0
    elapsed_seconds: float = 0.0


def convert(
    source: str | Path,
    *,
    ocr: bool = True,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    results_dir: str | Path | None = None,
    show_progress: bool = False,
    workers: int = 4,
    timeout: float = 600.0,
    max_retries: int = 2,
) -> ConversionResult:
    """转换文件或文件夹，默认写入当前目录的 results；批量时保留文件夹名。

    默认读取当前目录的 .env。显式参数优先于环境变量。
    配置和输入路径错误会抛出异常；单文件转换错误记录在返回值的 errors 中，
    批量处理会继续。默认不显示终端进度。
    workers 控制整个调用的 OCR 请求并发；1 为串行。保留图片原始输入。
    timeout/max_retries 传给模型客户端；不代表整份文档的总时间限制。
    """
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 32:
        raise ValueError("workers 必须是 1–32 的整数。")
    try:
        valid_timeout = not isinstance(timeout, bool) and isinstance(timeout, (int, float)) and math.isfinite(timeout) and timeout > 0
    except OverflowError:
        valid_timeout = False
    if not valid_timeout:
        raise ValueError("timeout 必须是有限正数。")
    if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError("max_retries 必须是非负整数。")
    started = time.monotonic()
    load_dotenv(Path.cwd() / ".env")
    input_path = Path(source).expanduser().resolve()
    output_dir = Path(results_dir).expanduser().resolve() if results_dir is not None else Path.cwd() / "results"
    if input_path.is_dir():
        output_dir /= input_path.name
        sources = sorted(
            path for path in input_path.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
    elif input_path.is_file():
        sources = [input_path]
    else:
        raise FileNotFoundError(f"输入路径不存在或不是文件/文件夹：{input_path}")

    result = ConversionResult()
    if not sources:
        return result

    model = model or os.getenv("MODEL") or os.getenv("OPENAI_MODEL") or os.getenv("GEMINI_MODEL") or "gemini-3.8-flash-high"
    api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = base_url or os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8045/v1")
    if ocr and not api_key:
        raise ValueError("OCR 需要 API Key，请配置 OPENAI_API_KEY 或传入 api_key。")

    with ExitStack() as stack:
        client = None
        if ocr:
            raw_client = stack.enter_context(OpenAI(
                base_url=base_url, api_key=api_key, timeout=timeout, max_retries=max_retries,
            ))
            client = OCRClient(raw_client, workers)
        state = local()

        def convert_one(path):
            try:
                if client:
                    client.reset_errors()
                if ocr and path.suffix.lower() == ".pdf":
                    text = convert_pdf(path, client, model, OCR_PROMPT, workers)
                else:
                    # Each file worker owns its converter and parser state.
                    if not hasattr(state, "converter"):
                        with _CONVERTER_INIT_LOCK:
                            state.converter = MarkItDown(
                                enable_plugins=True, llm_client=client, llm_model=model,
                                llm_prompt=OCR_PROMPT,
                            ) if ocr else MarkItDown()
                    text = state.converter.convert(str(path)).text_content
                if client:
                    client.raise_if_failed()
                return text, None
            except Exception as exc:
                return None, str(exc)

        pool = stack.enter_context(ThreadPoolExecutor(max_workers=workers if ocr else 1))
        converted_files = ordered_window(pool, convert_one, sources, workers if ocr else 1)
        # Write on the calling thread in source order, preserving same-stem overwrite behavior.
        for index, path in enumerate(sources, start=1):
            output = output_dir / f"{path.stem}.md"
            try:
                status = progress(f"[{index}/{len(sources)}] 正在转换 {path.name}") if show_progress else nullcontext()
                with status:
                    text, error = next(converted_files)
                    if error:
                        raise RuntimeError(error)
                    if path == output:
                        raise ValueError("输入文件不能与输出文件相同。")
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(text + "\n", encoding="utf-8")
                result.files.append(output)
                if show_progress:
                    print(f"已保存：{output}")
            except Exception as exc:
                result.errors[path] = str(exc)
                if show_progress:
                    print(f"转换失败：{path.name}：{exc}", file=sys.stderr)
        if client:
            result.ocr_requests = client.requests
            result.ocr_cache_hits = client.cache_hits
    result.elapsed_seconds = time.monotonic() - started
    return result
