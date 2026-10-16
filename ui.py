"""终端进度显示：转换期间显示动画和耗时，不估算完成百分比。"""

import sys
import time
from contextlib import contextmanager
from itertools import cycle
from threading import Event, Thread
from typing import Iterator


@contextmanager
def progress(message: str) -> Iterator[None]:
    """在终端显示等待动画；重定向输出时只打印开始和结束状态。"""
    started = time.monotonic()
    stopped = Event()
    terminal = sys.stderr.isatty()

    def animate() -> None:
        for frame in cycle("|/-\\"):
            elapsed = time.monotonic() - started
            print(f"\r{frame} {message}（{elapsed:.1f}s）", end="", file=sys.stderr, flush=True)
            if stopped.wait(0.1):
                break

    worker = Thread(target=animate, daemon=True) if terminal else None
    if worker:
        worker.start()
    else:
        print(message, file=sys.stderr)

    completed = False
    try:
        yield
        completed = True
    finally:
        stopped.set()
        if worker:
            worker.join()
        status = "处理完成" if completed else "处理未完成"
        prefix = "\r\033[2K" if terminal else ""
        elapsed = time.monotonic() - started
        print(f"{prefix}{status}，耗时 {elapsed:.1f}s", file=sys.stderr, flush=True)
