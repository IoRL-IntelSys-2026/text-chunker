"""Паспорт коллекции Qdrant.

Число точек в базе сверяется с числом строк chunks.jsonl.
При расхождении файл не пишется.
"""

from __future__ import annotations

import json
from pathlib import Path


def write_index_info(
    chunks_path: Path,
    info_path: Path,
    client,
    config: dict,
    *,
    collection: str,
    snapshot_id: str,
    embedding_model_revision: str,
    created_at: str,
) -> dict:
    """Пишет index_info.json. Возвращает записанный паспорт."""
    chunks_path = Path(chunks_path)
    info_path = Path(info_path)
    chunk_count, document_count = _counts(chunks_path, config)
    point_count = client.count(collection, exact=True).count
    if point_count != chunk_count:
        raise ValueError(f"в базе {point_count} точек, в файле {chunk_count} фрагментов")
    payload = {
        "collection": collection,
        "snapshot_id": snapshot_id,
        "chunker": config["chunker"],
        "strategy": config["strategy"],
        "max_tokens": config["max_tokens"],
        "overlap_tokens": config["overlap_tokens"],
        "min_tokens": config["min_tokens"],
        "embedding_model": config["embedding_model"],
        "embedding_model_revision": embedding_model_revision,
        "document_count": document_count,
        "chunk_count": chunk_count,
        "created_at": created_at,
    }
    info_path.parent.mkdir(parents=True, exist_ok=True)
    info_path.write_bytes((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return payload


def _counts(chunks_path: Path, config: dict) -> tuple[int, int]:
    chunker = config["chunker"]
    model = config["embedding_model"]
    documents: set[str] = set()
    count = 0
    for raw in chunks_path.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("chunker") != chunker or row.get("embedding_model") != model:
            raise ValueError("фрагмент собран другим чанкером или моделью")
        documents.add(row["doc_id"])
        count += 1
    if count == 0:
        raise ValueError("файл фрагментов пуст")
    return count, len(documents)
