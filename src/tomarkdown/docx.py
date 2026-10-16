"""Overlap independent DOCX image requests while retaining plugin output order."""

import io
import hashlib
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
        self._collecting = False
        self._images = {}
        self._prepared = {}
        self._missing_image = False

    @staticmethod
    def _image_key(data, stream_info):
        return hashlib.sha256(data).digest(), stream_info.mimetype

    def convert(self, file_stream, stream_info, **kwargs):
        # Plugin 0.1.0 extracts relationships before rendering; 0.1.1 uses
        # MarkItDown's native image hook. Retain each version's own layout logic.
        if not hasattr(DocxConverterWithOCR, '_image_to_html'):
            return super().convert(file_stream, stream_info, **kwargs)
        self._images = {}
        self._prepared = {}
        self._missing_image = False
        self._collecting = True
        try:
            super().convert(file_stream, stream_info, **kwargs)
        finally:
            self._collecting = False

        def recognize(item):
            key, (data, metadata) = item
            result = self.ocr_service.extract_text(io.BytesIO(data), stream_info=metadata)
            if result.error:
                raise RuntimeError(f'DOCX 图片识别失败：{result.error}')
            return key, result

        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                self._prepared = dict(ordered_window(pool, recognize, self._images.items(), self.workers))
            self._images.clear()
            file_stream.seek(0)
            result = super().convert(file_stream, stream_info, **kwargs)
            if self._missing_image:
                raise RuntimeError('DOCX 图片在两次解析中不一致，无法确认识别内容完整。')
            return result
        finally:
            self._images.clear()
            self._prepared.clear()

    def _image_to_html(self, image_stream, stream_info, **kwargs):
        data = image_stream.read()
        image_stream.seek(0)
        key = self._image_key(data, stream_info)
        if self._collecting:
            self._images.setdefault(key, (data, stream_info))
            return '<span>OCR pending</span>'
        if key not in self._prepared:
            self._missing_image = True
            raise RuntimeError('DOCX image was not present in the extraction pass')
        # Delegate formatting and repeated-image placement to the native plugin.
        prepared = self._prepared[key]
        class PreparedService:
            def extract_text(self, image_stream, stream_info=None):
                return prepared
        kwargs['ocr_service'] = PreparedService()
        return super()._image_to_html(image_stream, stream_info, **kwargs)

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
