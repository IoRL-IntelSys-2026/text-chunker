"""Опись снимка: по номеру можно найти заголовок и адрес, не открывая текст.

Хеш считается по копии текста. Сам файл страницы при этом не меняется.
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_common.datasets.mdd.documents import iter_documents
from rag_common.datasets.mdd.ids import k1_doc_id, k1_url
from rag_common.datasets.mdd.manifest import FETCHED_AT, write_manifest
from rag_common.text import normalized_hash

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "cache" / "multidoc2dial.zip"
PAGES = ROOT / "data" / "snapshots" / "mdd_v1" / "pages"


def test_normalized_hash_changes_only_the_copy() -> None:
    """Буква ё, неразрывный пробел, мягкий перенос и повторные пробелы меняют только хеш, не файл страницы."""
    plain = "е е"
    assert normalized_hash("ё  е") == normalized_hash(plain)
    assert normalized_hash("е\u00a0е") == normalized_hash("ее")
    assert normalized_hash("е\u00adе") == normalized_hash("ее")
    assert normalized_hash("ё  е") != normalized_hash("е е е")


def test_manifest_has_address_id_and_title(tmp_path: Path) -> None:
    """В описи 488 строк. В каждой есть адрес, номер и заголовок, а файлы страниц остаются прежними."""
    sample = next(iter_documents(ARCHIVE))
    sample_id = k1_doc_id(sample.domain, sample.source_doc_id)
    page = PAGES / f"{sample_id}.txt"
    before = page.read_bytes()

    manifest = tmp_path / "manifest.jsonl"
    assert write_manifest(ARCHIVE, manifest) == 488
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 488
    assert [row["doc_id"] for row in rows] == sorted(row["doc_id"] for row in rows)

    by_id = {row["doc_id"]: row for row in rows}
    assert len(by_id) == 488
    for document in iter_documents(ARCHIVE):
        doc_id = k1_doc_id(document.domain, document.source_doc_id)
        row = by_id[doc_id]
        assert row["schema_version"] == "k1.v1"
        assert row["source"] == "multidoc2dial"
        assert row["url"] == k1_url(document.domain, document.source_doc_id)
        assert row["doc_id"] == doc_id
        assert row["title"] == document.title
        assert row["source_doc_id"] == document.source_doc_id
        assert row["section"] == document.domain
        assert row["lang"] == "en"
        assert row["content_type"] == "text/plain"
        assert row["path"] == f"pages/{doc_id}.txt"
        assert row["aliases"] == []
        assert row["last_modified"] is None
        assert row["fetched_at"] == FETCHED_AT
        assert row["content_hash"] == normalized_hash(document.doc_text)

    assert page.read_bytes() == before
    assert before == sample.doc_text.encode("utf-8")

    first = manifest.read_bytes()
    write_manifest(ARCHIVE, manifest)
    assert manifest.read_bytes() == first
