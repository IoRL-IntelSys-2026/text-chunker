"""Загрузка фрагментов в коллекцию Qdrant.

Номер точки равен chunk_id. Повторная загрузка обновляет точку, а не создаёт вторую.
Карточка строки chunks.jsonl уходит целиком, плюс время indexed_at.
Векторы берутся из vectors.jsonl и в карточку не копируются.
"""

from __future__ import annotations

import json
from pathlib import Path

from qdrant_client import models

from rag_common.embeddings import DENSE_SIZE

COLLECTION = "mdd_chunks_v1"
BATCH_SIZE = 32


def upload_chunks(
    chunks_path: Path,
    vectors_path: Path,
    client,
    *,
    collection: str = COLLECTION,
    batch_size: int = BATCH_SIZE,
    indexed_at: str,
) -> int:
    """Кладёт фрагменты в коллекцию. Возвращает число отправленных точек."""
    if batch_size < 1:
        raise ValueError("пачка должна содержать хотя бы одну точку")
    chunks_path = Path(chunks_path)
    vectors_path = Path(vectors_path)
    expected = _count(chunks_path)
    if expected == 0:
        raise ValueError("файл фрагментов пуст")
    vectors = _rows(vectors_path)
    batch: list[models.PointStruct] = []
    sent = 0
    for chunk in _rows(chunks_path):
        try:
            vector = next(vectors)
        except StopIteration as error:
            raise ValueError("векторов меньше, чем фрагментов") from error
        batch.append(_point(chunk, vector, indexed_at))
        if len(batch) == batch_size:
            sent += _send(client, collection, batch)
            batch = []
            print(f"{sent}/{expected}", flush=True)
    if batch:
        sent += _send(client, collection, batch)
        print(f"{sent}/{expected}", flush=True)
    try:
        next(vectors)
    except StopIteration:
        pass
    else:
        raise ValueError("векторов больше, чем фрагментов")
    if sent != expected:
        raise ValueError("отправлено не столько точек, сколько фрагментов")
    return sent


def _point(chunk: dict, vector: dict, indexed_at: str) -> models.PointStruct:
    if vector.get("chunk_id") != chunk["chunk_id"]:
        raise ValueError("вектор не от того фрагмента")
    dense = vector.get("dense")
    indices = vector.get("sparse_indices")
    values = vector.get("sparse_values")
    if not isinstance(dense, list) or len(dense) != DENSE_SIZE:
        raise ValueError(f"у {chunk['chunk_id']} плотный вектор не длины {DENSE_SIZE}")
    if (
        not isinstance(indices, list)
        or not isinstance(values, list)
        or not indices
        or len(indices) != len(values)
    ):
        raise ValueError(f"у {chunk['chunk_id']} пустой разреженный вектор")
    payload = dict(chunk)
    payload["indexed_at"] = indexed_at
    return models.PointStruct(
        id=chunk["chunk_id"],
        vector={
            "dense": dense,
            "sparse": models.SparseVector(indices=indices, values=values),
        },
        payload=payload,
    )


def _send(client, collection: str, batch: list[models.PointStruct]) -> int:
    client.upsert(collection_name=collection, points=batch, wait=True)
    return len(batch)


def _rows(path: Path):
    with path.open("rb") as source:
        for raw in source:
            if raw.strip():
                yield json.loads(raw)


def _count(path: Path) -> int:
    return sum(1 for raw in path.read_bytes().splitlines() if raw.strip())
