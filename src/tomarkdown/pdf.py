"""PDF extraction: parse/render sequentially, overlap only independent OCR calls."""

import io
import re
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from threading import Lock

import pdfplumber
from markitdown_ocr import LLMVisionOCRService
# Isolate the plugin-specific image extraction seam here; covered by real PDF tests.
from markitdown_ocr._pdf_converter_with_ocr import _extract_images_from_page


# PDFium rendering is not thread-safe, including across separate documents.
_RENDER_LOCK = Lock()

def _text_lines(page):
    lines = []
    current, y = [], None
    for char in sorted(page.chars, key=lambda c: (c['top'], c['x0'])):
        if y is not None and abs(char['top'] - y) > 2:
            text = ''.join(current).strip()
            if text:
                lines.append((y, text))
            current, y = [], None
        if y is None:
            y = char['top']
        current.append(char['text'])
    if current:
        text = ''.join(current).strip()
        if text:
            lines.append((y, text))
    return lines


def convert_pdf(path, client, model, prompt, workers):
    service = LLMVisionOCRService(client=client, model=model, default_prompt=prompt)

    def recognize(data):
        result = service.extract_text(io.BytesIO(data))
        if result.error:
            raise RuntimeError(f'OCR 识别失败：{result.error}')
        return result.text

    # The queue includes text markers as well as futures; flushing in order preserves layout.
    output, pending = [], deque()
    active = set()

    def flush_one():
        item = pending.popleft()
        if isinstance(item, str):
            output.append(item)
        else:
            page_num, future = item
            try:
                text = future.result()
            except Exception as exc:
                raise RuntimeError(f'第 {page_num} 页：{exc}') from exc
            if text.strip():
                output.append(f'\n\n*[Image OCR]\n{text}\n[End OCR]*\n')

    # PDF objects never cross threads. Only immutable image bytes enter the executor.
    with pdfplumber.open(path) as pdf, ThreadPoolExecutor(max_workers=workers) as executor:
        for number, page in enumerate(pdf.pages, 1):
            try:
                pending.append(f'\n## Page {number}\n')
                with _RENDER_LOCK:
                    images = _extract_images_from_page(page)
                text = page.extract_text() or ''
                full_page = len(images) < len(page.images) or (
                    not text.strip() and not images and bool(page.curves or page.rects or page.lines)
                )
                if full_page:
                    # Extraction failed or text is drawn as vectors: render the actual page.
                    stream = io.BytesIO()
                    with _RENDER_LOCK:
                        page.to_image(resolution=300).original.save(stream, format='PNG')
                    images = [{'stream': stream, 'y_pos': 0}]
                    items = []
                elif images:
                    items = [(y, 'text', value) for y, value in _text_lines(page)]
                else:
                    items = [(0, 'text', text.strip())] if text.strip() else []
                items.extend((image['y_pos'], 'image', image['stream']) for image in images)
                items.sort(key=lambda item: item[0])
                for _, kind, value in items:
                    if kind == 'text':
                        pending.append(value)
                    else:
                        active.difference_update(future for future in tuple(active) if future.done())
                        if len(active) >= workers:
                            completed, _ = wait(active, return_when=FIRST_COMPLETED)
                            active.difference_update(completed)
                        value.seek(0)
                        future = executor.submit(recognize, value.read())
                        active.add(future)
                        pending.append((number, future))
                        value.close()
                # Do not keep text-only pages behind completed OCR indefinitely.
                while pending and (isinstance(pending[0], str) or pending[0][1].done()):
                    flush_one()
            finally:
                page.close()
        while pending:
            flush_one()
    text = '\n\n'.join(output).strip()
    # Match MarkItDown's public conversion whitespace normalization.
    text = '\n'.join(line.rstrip() for line in re.split(r'\r?\n', text))
    return re.sub(r'\n{3,}', '\n\n', text)
