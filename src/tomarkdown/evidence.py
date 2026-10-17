"""Provenance records describe extraction coverage, never audit conclusions."""
import hashlib
import os
import tempfile
from pathlib import Path
from importlib.metadata import version


def publish_evidence(output, output_bytes, evidence_path, evidence_text):
    """Stage both outputs; the hash-checked manifest is the final commit marker.

    Two paths cannot be replaced atomically together. Remove the old marker first,
    and remove the new Markdown if the final marker cannot be published.
    """
    staged = []
    replaced = False
    try:
        for data in (output_bytes, evidence_text.encode('utf-8')):
            with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.tomarkdown-', delete=False) as temp:
                staged.append(Path(temp.name))
                temp.write(data)
        evidence_path.unlink(missing_ok=True)
        os.replace(staged[0], output)
        replaced = True
        os.replace(staged[1], evidence_path)
    except BaseException:
        if replaced:
            output.unlink(missing_ok=True)
            evidence_path.unlink(missing_ok=True)
        raise
    finally:
        for path in staged:
            path.unlink(missing_ok=True)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def make_evidence(source, digest, output, output_bytes, document, *, ocr, model, prompt):
    is_spreadsheet = source.suffix.lower() in ('.xlsx', '.xls')
    warnings = list(document.get('warnings', [])) if document else []
    if not is_spreadsheet:
        warnings.append('仅记录文件级来源；未提供字段坐标、表格结构或图像实体数量的可靠证据。')
    warnings.append('未进行真实性、合规性或业务规则审查；OCR 输出不保证逐字准确。')
    return dict(
        schema_version=1,
        source=dict(name=source.name, path=str(source), sha256=digest),
        output=dict(name=output.name, sha256=hashlib.sha256(output_bytes).hexdigest()),
        converter=dict(name='ming-tomarkdown', version=version('ming-tomarkdown'),
                       dependencies={name: version(name) for name in
                                     ('openpyxl', 'xlrd', 'markitdown', 'markitdown-ocr', 'pdfplumber')}),
        configuration=dict(ocr=ocr, model=model if ocr else None,
                           prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest() if ocr else None),
        status='converted_requires_review',
        location_granularity='cell' if is_spreadsheet else 'file',
        warnings=warnings, document=document,
    )
