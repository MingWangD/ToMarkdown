"""Shared request budget and per-conversion cache for both OCR call paths."""

import hashlib
import json
from collections import OrderedDict
from concurrent.futures import FIRST_COMPLETED, Future, wait
from threading import BoundedSemaphore, Lock, local
from types import SimpleNamespace


def ordered_window(executor, function, items, limit):
    """Refill on any completion, emit in order, and bound the reorder buffer."""
    iterator = enumerate(items)
    pending, ready = {}, {}
    next_index = 0
    exhausted = False
    while pending or ready or not exhausted:
        # Completed results need no worker slot, but still count toward memory.
        while not exhausted and len(pending) < limit and len(pending) + len(ready) < 2 * limit:
            try:
                index, item = next(iterator)
            except StopIteration:
                exhausted = True
                break
            pending[executor.submit(function, item)] = index
        if next_index in ready:
            yield ready.pop(next_index)
            next_index += 1
            continue
        if pending:
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                ready[pending.pop(future)] = future.result()


class OCRClient:
    """Small OpenAI-compatible adapter; one instance lives for one convert()."""

    def __init__(self, client, workers, cache_size=128):
        self._client = client
        self._slots = BoundedSemaphore(workers)
        self._lock = Lock()
        self._local = local()
        self._cache = OrderedDict()
        self._inflight = {}
        self._cache_size = cache_size
        self.requests = 0
        self.cache_hits = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def reset_errors(self):
        self._local.errors = []

    def raise_if_failed(self):
        errors = getattr(self._local, 'errors', [])
        if errors:
            raise RuntimeError(f'OCR 识别失败：{errors[0]}')

    def create(self, **kwargs):
        try:
            return self._create(**kwargs)
        except Exception as exc:
            if not hasattr(self._local, 'errors'):
                self._local.errors = []
            self._local.errors.append(str(exc))
            raise

    def _create(self, **kwargs):
        key = hashlib.sha256(json.dumps(kwargs, sort_keys=True, ensure_ascii=False).encode()).digest()
        with self._lock:
            if key in self._cache:
                self.cache_hits += 1
                self._cache.move_to_end(key)
                return self._cache[key]
            future = self._inflight.get(key)
            owner = future is None
            if owner:
                future = Future()
                self._inflight[key] = future
            else:
                self.cache_hits += 1
        if not owner:
            return future.result()
        try:
            with self._slots:
                with self._lock:
                    self.requests += 1
                response = self._client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                if getattr(choice, 'finish_reason', None) in ('length', 'content_filter'):
                    raise RuntimeError(f'OCR 返回不完整：{choice.finish_reason}')
                if getattr(choice.message, 'refusal', None):
                    raise RuntimeError('OCR 服务拒绝识别该图片')
                if choice.message.content is None:
                    raise RuntimeError('OCR 未返回文本内容')
            with self._lock:
                self._cache[key] = response
                self._cache.move_to_end(key)
                while len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)
            future.set_result(response)
            return response
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._inflight.pop(key, None)
