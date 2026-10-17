"""Legacy XLS fidelity and OCR routing through the public API."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook
from PIL import Image

from tomarkdown import convert


class LegacySpreadsheetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def legacy(self):
        path = self.root/'ledger.xls'
        shutil.copyfile(Path(__file__).parent/'fixtures'/'legacy-ledger.xls', path)
        return path

    def test_xls_has_cell_evidence_merges_types_formats_and_hidden_content(self):
        path = self.legacy()
        result = convert(path, ocr=False, evidence=True, results_dir=self.root/'out')
        self.assertFalse(result.errors)
        data = json.loads(result.evidence_files[path].read_text())
        self.assertEqual(data['location_granularity'], 'cell')
        sheets = data['document']['sheets']
        sheet = sheets[0]
        cells = {c['coordinate']: c for c in sheet['cells']}
        self.assertEqual(sheet['merged_ranges'], ['A2:A3'])
        self.assertEqual(sheet['hidden_rows'], [3])
        self.assertEqual(sheet['hidden_columns'], ['E'])
        self.assertEqual(sheets[1]['state'], 'hidden')
        self.assertEqual(cells['B2']['value'], '温升 | 上限\n第二行')
        self.assertEqual(cells['E2']['value'], 'NaN')
        self.assertEqual(cells['C3']['value'], 64.8)
        self.assertEqual(cells['C4']['number_format'], '000000')
        self.assertEqual(cells['C5']['value'], '2026-10-17T00:00:00')
        self.assertIs(cells['C7']['value'], True)
        self.assertIn('000123', result.files[0].read_text())
        self.assertIn('温升 \\| 上限<br>第二行', result.files[0].read_text())
        self.assertIn('↳ A2', result.files[0].read_text())
        self.assertTrue(any('公式' in w and '缓存' in w for w in data['warnings']))
        self.assertTrue(any('.xls' in w and '图片' in w for w in data['warnings']))

    def test_text_only_excel_default_ocr_makes_no_model_calls_or_key_demand(self):
        xls = self.legacy()
        book = Workbook()
        book.active['A1'] = '纯文本 ≤65 K'
        xlsx = self.root/'text.xlsx'
        book.save(xlsx)
        for path in (xls, xlsx):
            with self.subTest(extension=path.suffix), patch.dict(os.environ, {}, clear=True), \
                    patch('tomarkdown.core.load_dotenv'), patch('tomarkdown.core.OpenAI') as sdk:
                result = convert(path, evidence=True, results_dir=self.root/'out')
                self.assertFalse(result.errors)
                self.assertEqual(result.ocr_requests, 0)
                sdk.assert_not_called()

    def test_missing_key_for_real_image_is_error_and_never_silent_success(self):
        path = self.root/'scan.png'
        Image.new('RGB', (100, 100), 'white').save(path)
        with patch.dict(os.environ, {}, clear=True), patch('tomarkdown.core.load_dotenv'), \
                patch('tomarkdown.core.OpenAI') as sdk:
            result = convert(path, evidence=True, results_dir=self.root/'out')
        self.assertFalse(result.files)
        self.assertFalse(result.evidence_files)
        self.assertIn('API Key', result.errors[path])
        sdk.assert_not_called()


if __name__ == '__main__':
    unittest.main()
