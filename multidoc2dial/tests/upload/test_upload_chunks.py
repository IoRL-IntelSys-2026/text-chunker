"""Загрузка фрагментов в базу.

Номер точки равен chunk_id, поэтому повторная загрузка обновляет точку, а не создаёт вторую.
Тест подставляет фальшивый клиент и в живой Qdrant не ходит.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from preprocessing.upload_chunks import upload_chunks
from rag_common.embeddings import DENSE_SIZE

INDEXED_AT = "2026-10-02T15:50:00Z"


def test_points_use_chunk_id_and_upsert_in_batches(tmp_path: Path) -> None:
    """Каждая точка получает номер своего chunk_id. Отправка идёт пачками, а не по одной."""
    chunks, vectors = _files(tmp_path, 5)
    client = _FakeClient()
    count = upload_chunks(
        chunks,
        vectors,
        client,
        collection="mdd_chunks_v1",
        batch_size=2,
        indexed_at=INDEXED_AT,
    )
    assert count == 5
    assert [len(batch) for _name, batch in client.calls] == [2, 2, 1]
    assert all(name == "mdd_chunks_v1" for name, _batch in client.calls)
    points = [point for _name, batch in client.calls for point in batch]
    assert [point.id for point in points] == [f"id-{index}" for index in range(5)]
    assert points[0].vector["dense"] == [0.1] * DENSE_SIZE
    assert list(points[0].vector["sparse"].indices) == [4, 7]
    assert points[0].payload["text"] == "fragment 0"
    assert points[0].payload["indexed_at"] == INDEXED_AT
    assert "dense" not in points[0].payload


def test_second_upload_sends_the_same_ids(tmp_path: Path) -> None:
    """Повторная загрузка снова шлёт те же номера, поэтому в базе не появляется дубль."""
    chunks, vectors = _files(tmp_path, 1)
    client = _FakeClient()
    upload_chunks(chunks, vectors, client, batch_size=8, indexed_at=INDEXED_AT)
    upload_chunks(chunks, vectors, client, batch_size=8, indexed_at=INDEXED_AT)
    first = [point.id for point in client.calls[0][1]]
    second = [point.id for point in client.calls[1][1]]
    assert first == second == ["id-0"]


def test_mismatched_vector_is_rejected(tmp_path: Path) -> None:
    """Если вектор относится к другому фрагменту, загрузка останавливается и не кладёт чужой вектор на этот chunk_id."""
    chunks, vectors = _files(tmp_path, 1)
    wrong = [{"chunk_id": "other", "dense": [0.1] * DENSE_SIZE, "sparse_indices": [1], "sparse_values": [0.2]}]
    vectors.write_bytes(_dump(wrong))
    with pytest.raises(ValueError, match="не от того фрагмента"):
        upload_chunks(chunks, vectors, _FakeClient(), batch_size=8, indexed_at=INDEXED_AT)


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list]] = []

    def upsert(self, collection_name, points, wait=True):
        assert wait is True
        self.calls.append((collection_name, list(points)))


def _files(directory: Path, count: int) -> tuple[Path, Path]:
    chunks = [
        {"chunk_id": f"id-{index}", "text": f"fragment {index}", "embed_text": f"embed {index}"}
        for index in range(count)
    ]
    vectors = [
        {
            "chunk_id": row["chunk_id"],
            "dense": [0.1] * DENSE_SIZE,
            "sparse_indices": [4, 7],
            "sparse_values": [0.2, 0.3],
        }
        for row in chunks
    ]
    chunk_path = directory / "chunks.jsonl"
    vector_path = directory / "vectors.jsonl"
    chunk_path.write_bytes(_dump(chunks))
    vector_path.write_bytes(_dump(vectors))
    return chunk_path, vector_path


def _dump(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row) + "\n" for row in rows).encode("utf-8")
