"""Паспорт коллекции пишется только когда число точек в базе равно числу строк фрагментов.

Иначе файл паспорта соврал бы, сколько кусков реально загружено.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from preprocessing.index_info import write_index_info

CONFIG = {
    "chunker": "mdd-sections+recursive/v1/512/64",
    "strategy": "md_header",
    "max_tokens": 512,
    "overlap_tokens": 64,
    "min_tokens": 24,
    "embedding_model": "BAAI/bge-m3",
}


def test_passport_records_matching_counts(tmp_path: Path) -> None:
    """При совпадении счётчика паспорт записывает число фрагментов и документов из файла нарезки."""
    chunks = tmp_path / "chunks.jsonl"
    _write(chunks, ["doc-a", "doc-a", "doc-b"])
    info = tmp_path / "index_info.json"
    payload = write_index_info(
        chunks,
        info,
        _FakeClient(3),
        CONFIG,
        collection="mdd_chunks_v1",
        snapshot_id="mdd_v1",
        embedding_model_revision="rev",
        created_at="2026-10-02T15:52:35Z",
    )
    saved = json.loads(info.read_bytes().decode("utf-8"))
    assert saved == payload
    assert saved["chunk_count"] == 3
    assert saved["document_count"] == 2
    assert saved["snapshot_id"] == "mdd_v1"
    assert saved["embedding_model"] == "BAAI/bge-m3"
    assert saved["embedding_model_revision"] == "rev"


def test_mismatch_does_not_write_passport(tmp_path: Path) -> None:
    """Если в базе точек меньше, чем строк в файле, паспорт не создаётся."""
    chunks = tmp_path / "chunks.jsonl"
    _write(chunks, ["doc-a"])
    info = tmp_path / "index_info.json"
    with pytest.raises(ValueError, match="0 точек"):
        write_index_info(
            chunks,
            info,
            _FakeClient(0),
            CONFIG,
            collection="mdd_chunks_v1",
            snapshot_id="mdd_v1",
            embedding_model_revision="rev",
            created_at="2026-10-02T15:52:35Z",
        )
    assert not info.exists()


class _FakeClient:
    def __init__(self, count: int) -> None:
        self._count = count

    def count(self, collection_name, exact=True):
        assert collection_name == "mdd_chunks_v1"
        assert exact is True
        return type("Count", (), {"count": self._count})()


def _write(path: Path, doc_ids: list[str]) -> None:
    rows = []
    for index, doc_id in enumerate(doc_ids):
        rows.append({
            "chunk_id": f"id-{index}",
            "doc_id": doc_id,
            "chunker": CONFIG["chunker"],
            "embedding_model": CONFIG["embedding_model"],
        })
    path.write_bytes("".join(json.dumps(row) + "\n" for row in rows).encode("utf-8"))
