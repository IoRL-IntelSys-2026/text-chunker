"""Векторы фрагментов: плотный и разреженный для каждой строки chunks.jsonl.

Счёт идёт пачками. Карточка чанка в chunks.jsonl не меняется.
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_common.embeddings import DENSE_SIZE, Embedder, get_embedder

BATCH_SIZE = 8
MAX_LENGTH = 512


def write_vectors(
    chunks_path: Path,
    vectors_path: Path,
    embedder: Embedder | None = None,
    *,
    batch_size: int = BATCH_SIZE,
    max_length: int = MAX_LENGTH,
) -> int:
    """Пишет vectors.jsonl заново: одна строка на строку chunks.jsonl."""
    chunks_path = Path(chunks_path)
    vectors_path = Path(vectors_path)
    rows = _rows(chunks_path)
    if embedder is None:
        embedder = get_embedder()
    vectors_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with vectors_path.open("wb") as target:
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            encoded = embedder.encode_documents(
                [row["embed_text"] for row in batch],
                batch_size=batch_size,
                max_length=max_length,
            )
            if len(encoded) != len(batch):
                raise ValueError("модель вернула не столько векторов, сколько фрагментов")
            for row, result in zip(batch, encoded, strict=True):
                if len(result.dense) != DENSE_SIZE:
                    raise ValueError(f"у {row['chunk_id']} плотный вектор не длины {DENSE_SIZE}")
                payload = {
                    "chunk_id": row["chunk_id"],
                    "dense": list(result.dense),
                    "sparse_indices": list(result.sparse.indices),
                    "sparse_values": list(result.sparse.values),
                }
                target.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
                written += 1
            target.flush()
            print(f"{written}/{len(rows)}", flush=True)
    if written != len(rows):
        raise ValueError("число векторов не равно числу фрагментов")
    return written


def _rows(chunks_path: Path) -> list[dict]:
    rows = []
    for line in chunks_path.read_bytes().decode("utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows
