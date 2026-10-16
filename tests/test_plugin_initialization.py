"""Cold concurrent conversion must not skip MarkItDown's lazy plugins."""
import importlib
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from markitdown import DocumentConverter, DocumentConverterResult, MarkItDown
from tomarkdown import convert


class PluginInitializationTests(unittest.TestCase):
    def test_concurrent_cold_start_registers_plugin_for_every_file(self):
        registry = importlib.import_module('markitdown._markitdown')
        a_conversion_finished = threading.Event()
        original_convert = MarkItDown.convert
        marker = 'PLUGIN WAS REGISTERED: '

        class MarkerConverter(DocumentConverter):
            def accepts(self, file_stream, stream_info, **kwargs):
                return stream_info.extension == '.txt'

            def convert(self, file_stream, stream_info, **kwargs):
                return DocumentConverterResult(
                    markdown=marker + file_stream.read().decode('utf-8'))

        def register(markitdown, **kwargs):
            markitdown.register_converter(MarkerConverter(), priority=-100)

        plugin = SimpleNamespace(register_converters=register)

        def slow_load():
            # Without initialization serialization, a second converter observes
            # the empty registry and finishes conversion before this returns.
            # With serialization no conversion can finish yet; the timeout
            # allows initialization to complete without requiring a second load.
            a_conversion_finished.wait(0.4)
            return plugin

        def tracked_convert(instance, *args, **kwargs):
            result = original_convert(instance, *args, **kwargs)
            a_conversion_finished.set()
            return result

        entry_point = SimpleNamespace(name='cold-start-test', load=slow_load)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input'
            source.mkdir()
            for index in range(4):
                (source / f'{index}.txt').write_text(f'content-{index}', encoding='utf-8')
            with (
                patch.object(registry, '_plugins', None),
                patch.object(registry, 'entry_points', return_value=[entry_point]),
                patch.object(MarkItDown, 'convert', tracked_convert),
                patch('tomarkdown.core.OpenAI', return_value=MagicMock()),
            ):
                result = convert(source, api_key='test-only', model='fake',
                                 base_url='http://unused.invalid/v1',
                                 results_dir=root / 'output', workers=4)
            self.assertFalse(result.errors)
            self.assertEqual(len(result.files), 4)
            self.assertEqual(result.ocr_requests, 0)
            for index, path in enumerate(result.files):
                self.assertEqual(path.read_text(encoding='utf-8'),
                                 f'{marker}content-{index}\n',
                                 f'worker silently omitted its plugin for {path.name}')


if __name__ == '__main__':
    unittest.main()
