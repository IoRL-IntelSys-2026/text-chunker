"""Прогон до записи в базу: снимок, нарезка, векторы, затем pytest.

Архив читается из data/cache/multidoc2dial.zip и на диск не распаковывается.
В Qdrant этот скрипт не пишет. Поиск retrieve.py не запускается.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from preprocessing.embed_chunks import write_vectors
from preprocessing.write_chunks import write_chunks
from rag_common.mdd.build import build_snapshot

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data" / "cache" / "multidoc2dial.zip"
SNAPSHOT = ROOT / "data" / "snapshots" / "mdd_v1"
CONFIG = ROOT / "configs" / "chunking" / "mdd_sections_512.yaml"
CHUNKS = ROOT / "data" / "index" / "mdd_chunks_v1" / "chunks.jsonl"
VECTORS = ROOT / "data" / "index" / "mdd_chunks_v1" / "vectors.jsonl"


def main() -> int:
    print("Собираю снимок из архива", flush=True)
    build_snapshot(ARCHIVE, SNAPSHOT)
    print("Режу фрагменты", flush=True)
    chunk_count = write_chunks(SNAPSHOT, CONFIG, CHUNKS)
    print(f"Фрагментов: {chunk_count}", flush=True)
    print("Считаю векторы bge-m3. При первом запуске модель скачивается", flush=True)
    vector_count = write_vectors(CHUNKS, VECTORS)
    print(f"Векторов: {vector_count}", flush=True)
    print("Запускаю проверки", flush=True)
    return pytest.main(
        [
            "tests/snapshot",
            "tests/chunking",
            "tests/vectors",
            "tests/upload",
            "tests/answer",
            "-q",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
