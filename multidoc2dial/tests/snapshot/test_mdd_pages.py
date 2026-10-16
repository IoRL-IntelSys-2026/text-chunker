"""Текст страницы записывается байт в байт.

Границы разделов считают символы в этом тексте. Если его поправить, номера укажут не туда.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from rag_common.datasets.mdd.documents import iter_documents
from rag_common.datasets.mdd.ids import k1_doc_id
from rag_common.datasets.mdd.pages import write_pages

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "cache" / "multidoc2dial.zip"


def test_t_pre_02_pages_match_doc_text_bytes(tmp_path: Path) -> None:
    """Появляется 488 файлов, и каждый равен исходному тексту документа."""
    pages = tmp_path / "pages"
    assert write_pages(ARCHIVE, pages) == 488
    files = list(pages.glob("*.txt"))
    assert len(files) == 488

    expected: dict[str, bytes] = {}
    for document in iter_documents(ARCHIVE):
        doc_id = k1_doc_id(document.domain, document.source_doc_id)
        expected[doc_id] = document.doc_text.encode("utf-8")

    assert len(expected) == 488
    for doc_id, payload in expected.items():
        raw = (pages / f"{doc_id}.txt").read_bytes()
        assert len(raw) == len(payload)
        assert hashlib.sha256(raw).digest() == hashlib.sha256(payload).digest()

    first = {path.name: hashlib.sha256(path.read_bytes()).digest() for path in files}
    assert write_pages(ARCHIVE, pages) == 488
    second = {path.name: hashlib.sha256(path.read_bytes()).digest() for path in pages.glob("*.txt")}
    assert first == second
