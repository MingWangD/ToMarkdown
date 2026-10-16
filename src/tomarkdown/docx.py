"""Overlap independent DOCX image requests while retaining plugin output order."""

import io
import re
from concurrent.futures import ThreadPoolExecutor

from docx import Document
from markitdown import StreamInfo
from markitdown_ocr import DocxConverterWithOCR, LLMVisionOCRService

from .ocr import ordered_window


class _ConcurrentDocxConverter(DocxConverterWithOCR):
    def __init__(self, service, workers):
        super().__init__(ocr_service=service)
        self.workers = workers

    def _extract_and_ocr_images(self, file_stream, ocr_service):
        file_stream.seek(0)
        document = Document(file_stream)
        # Preserve the plugin's relationship order; never share parser objects with workers.
        images = (
            (relation.rId, relation.target_part.blob)
            for relation in document.part.rels.values()
            if 'image' in relation.target_ref.lower() and not relation.is_external
        )

        def recognize(item):
            relationship, data = item
            result = ocr_service.extract_text(io.BytesIO(data))
            if result.error:
                raise RuntimeError(f'DOCX 图片 {relationship} 识别失败：{result.error}')
            return relationship, result.text.strip()

        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            return {
                relationship: text
                for relationship, text in ordered_window(pool, recognize, images, self.workers)
                if text
            }


def convert_docx(path, client, model, prompt, workers):
    service = LLMVisionOCRService(client=client, model=model, default_prompt=prompt)
    converter = _ConcurrentDocxConverter(service, workers)
    # Direct invocation prevents MarkItDown from silently falling back after an OCR error.
    with open(path, 'rb') as stream:
        text = converter.convert(stream, StreamInfo(extension='.docx')).text_content
    text = '\n'.join(line.rstrip() for line in re.split(r'\r?\n', text))
    return re.sub(r'\n{3,}', '\n\n', text)
