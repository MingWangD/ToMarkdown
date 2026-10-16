"""Reproducible offline scheduling benchmark; no credentials or network used.

Run: python tests/benchmark_ocr.py
"""
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from markitdown import MarkItDown
from tomarkdown import convert
from tomarkdown.core import OCR_PROMPT
from test_ocr_performance import VisionEndpoint


def benchmark():
    rows = []
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        images = [Image.new('RGB', (160, 120), (n*25, 20, 80)) for n in range(8)]
        folder = root/'images'
        folder.mkdir()
        for n, image in enumerate(images):
            image.save(folder/f'{n}.png')
        pdf = root/'unique.pdf'
        images[0].save(pdf, save_all=True, append_images=images[1:])
        repeated = root/'repeated.pdf'
        images[0].save(repeated, save_all=True, append_images=[images[0]]*7)
        for source in [folder, pdf, repeated]:
            before = VisionEndpoint(delay=0.1)
            converter = MarkItDown(enable_plugins=True, llm_client=before,
                                   llm_model='test-vision', llm_prompt=OCR_PROMPT)
            paths = sorted(source.iterdir()) if source.is_dir() else [source]
            start = time.perf_counter()
            baseline = [converter.convert(str(p)).text_content.strip() for p in paths]
            old_seconds = time.perf_counter() - start
            after = VisionEndpoint(delay=0.1)
            start = time.perf_counter()
            with patch('tomarkdown.core.OpenAI', return_value=after):
                result = convert(source, api_key='test-only', model='test-vision',
                                 base_url='http://unused.invalid/v1', results_dir=root/'out')
            new_seconds = time.perf_counter() - start
            assert not result.errors, result.errors
            assert [p.read_text().strip() for p in result.files] == baseline
            rows.append(dict(case=source.name, baseline_seconds=round(old_seconds,3),
                             optimized_seconds=round(new_seconds,3),
                             speedup=round(old_seconds/new_seconds,2),
                             baseline_requests=before.calls, optimized_requests=after.calls,
                             baseline_peak=before.peak, optimized_peak=after.peak,
                             output_identical=True))
    return {'note':'Synthetic endpoint: fixed 100ms/request, 8 images/pages. Not real LLM throughput.', 'results':rows}


if __name__ == '__main__':
    print(json.dumps(benchmark(), ensure_ascii=False, indent=2))
