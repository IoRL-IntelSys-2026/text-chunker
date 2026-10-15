"""Проверка векторов фрагментов.

У каждой строки chunks.jsonl есть строка в vectors.jsonl.
Плотный вектор содержит 1024 числа. Пустых векторов нет.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from rag_common.embeddings import DENSE_SIZE


def check_vectors(chunks_path: Path, vectors_path: Path) -> int:
    """Проверяет vectors.jsonl. При ошибке останавливается. Возвращает число строк."""
    chunk_ids = _chunk_ids(Path(chunks_path))
    if not chunk_ids:
        raise ValueError("файл фрагментов пуст")
    problems = []
    count = 0
    for index, row in enumerate(_rows(Path(vectors_path)), start=1):
        count += 1
        if index > len(chunk_ids):
            problems.append(f"строка {index}: лишний вектор")
            break
        problems.extend(_problems(row, index, chunk_ids[index - 1]))
        if len(problems) >= 20:
            break
    if count < len(chunk_ids):
        problems.append(f"векторов {count}, фрагментов {len(chunk_ids)}")
    if problems:
        raise ValueError("\n".join(problems))
    return count


def _problems(row: dict, index: int, chunk_id: str) -> list[str]:
    if row.get("chunk_id") != chunk_id:
        return [f"строка {index}: вектор не от того фрагмента"]
    dense = row.get("dense")
    indices = row.get("sparse_indices")
    values = row.get("sparse_values")
    if not isinstance(dense, list) or not dense:
        return [f"строка {index}: пустой плотный вектор"]
    if len(dense) != DENSE_SIZE or any(not _number(item) for item in dense):
        return [f"строка {index}: плотный вектор не длины {DENSE_SIZE}"]
    if not isinstance(indices, list) or not isinstance(values, list) or not indices or not values:
        return [f"строка {index}: пустой разреженный вектор"]
    if len(indices) != len(values):
        return [f"строка {index}: у разреженного вектора разное число номеров и весов"]
    return []


def _number(item) -> bool:
    return isinstance(item, (int, float)) and not isinstance(item, bool) and not math.isnan(item)


def _chunk_ids(chunks_path: Path) -> list[str]:
    ids = []
    for row in _rows(chunks_path):
        ids.append(row["chunk_id"])
    return ids


def _rows(path: Path):
    for line in path.read_bytes().decode("utf-8").splitlines():
        if line:
            yield json.loads(line)
