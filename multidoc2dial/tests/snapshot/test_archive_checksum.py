"""Сумма архива и чтение документов из zip.

Снимок можно собирать только из той копии архива, сумма которой записана в коде.
Zip не распаковывается: документы читаются в памяти.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_common.mdd.documents import iter_documents
from rag_common.mdd.mdd import (
    ARCHIVE_SHA256,
    ArchiveHashMismatch,
    file_sha256,
    prepare_archive,
)

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "cache" / "multidoc2dial.zip"


def test_t_pre_01_official_archive_matches_recorded_hash() -> None:
    """Локальный zip совпадает с официальной суммой, иначе это другая или битая копия."""
    assert file_sha256(ARCHIVE) == ARCHIVE_SHA256


def test_t_pre_01_prepare_copies_matching_archive(tmp_path: Path) -> None:
    """Верный архив копируется в кэш целиком и рядом не появляется распакованная папка."""
    target = prepare_archive(ARCHIVE, tmp_path)
    assert target.name == "multidoc2dial.zip"
    assert target.is_file()
    assert file_sha256(target) == ARCHIVE_SHA256
    assert not (tmp_path / "multidoc2dial").exists()


def test_t_pre_01_wrong_hash_stops_and_does_not_replace_cache(tmp_path: Path) -> None:
    """Чужая сумма останавливает работу и не затирает уже лежащую в кэше копию."""
    good = prepare_archive(ARCHIVE, tmp_path)
    before = good.read_bytes()[:16]
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not the official archive")
    with pytest.raises(ArchiveHashMismatch):
        prepare_archive(bad, tmp_path)
    assert good.read_bytes()[:16] == before


def test_t_pre_01_reads_488_documents_from_zip() -> None:
    """Из zip читаются 488 документов и четыре темы: dmv, ssa, va, studentaid."""
    before = {path.name for path in ARCHIVE.parent.iterdir()}
    counts: dict[str, int] = {}
    total = 0
    for document in iter_documents(ARCHIVE):
        total += 1
        counts[document.domain] = counts.get(document.domain, 0) + 1
        assert isinstance(document.doc_text, str)
        assert isinstance(document.title, str)
        assert document.source_doc_id
    assert total == 488
    assert counts == {"dmv": 149, "ssa": 109, "va": 138, "studentaid": 92}
    assert {path.name for path in ARCHIVE.parent.iterdir()} == before
    assert not (ARCHIVE.parent / "multidoc2dial").exists()


def test_t_pre_01_bad_archive_is_not_read(tmp_path: Path) -> None:
    """При чужой сумме документы даже не начинают читаться."""
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not the official archive")
    with pytest.raises(ArchiveHashMismatch):
        list(iter_documents(bad))
