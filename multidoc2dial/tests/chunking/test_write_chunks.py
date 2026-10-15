"""Долго: читает весь снимок и считает токены bge-m3 по всем фрагментам.

Запись chunks.jsonl: одна строка на фрагмент, со ссылкой на документ и границами.
Векторов в этом файле быть не должно, они пишутся отдельно.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from preprocessing.write_chunks import write_chunks
from rag_common.ids import make_chunk_id

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "data" / "snapshots" / "mdd_v1"
CONFIG = ROOT / "configs" / "chunking" / "mdd_sections_512.yaml"
KNOWN_ID = "0a6f1ad6-6a7d-5462-abe5-516ceca3c4bb"
CHUNKER = "mdd-sections+recursive/v1/512/64"
KNOWN_URL = "mdd://studentaid/How%20Aid%20Is%20Calculated%20%7C%20Federal%20Student%20Aid%231_0"


def test_chunks_file_has_one_line_per_fragment_and_no_vectors(tmp_path: Path) -> None:
    """Число строк равно числу фрагментов, векторов в строке нет, повторная запись даёт тот же файл."""
    target = tmp_path / "mdd_chunks_v1" / "chunks.jsonl"
    first_count = write_chunks(SNAPSHOT, CONFIG, target)
    first_bytes = target.read_bytes()
    second_count = write_chunks(SNAPSHOT, CONFIG, target)
    assert second_count == first_count
    assert target.read_bytes() == first_bytes

    lines = first_bytes.decode("utf-8").splitlines()
    assert len(lines) == first_count
    assert lines
    rows = [json.loads(line) for line in lines]
    assert all("vector" not in row and "dense" not in row and "indexed_at" not in row for row in rows)

    known = [row for row in rows if row["doc_id"] == KNOWN_ID]
    assert known
    assert {row["n_chunks"] for row in known} == {len(known)}
    assert [row["chunk_index"] for row in known] == list(range(len(known)))
    page = (SNAPSHOT / "pages" / f"{KNOWN_ID}.txt").read_bytes().decode("utf-8")
    first = known[0]
    assert first["url"] == KNOWN_URL
    assert first["char_start"] == 0
    assert page[first["char_start"] : first["char_end"]] == first["text"]
    assert first["chunk_id"] == make_chunk_id(KNOWN_ID, CHUNKER, 0)
    assert first["chunk_id"] == "c966c095-0b78-5501-ac2a-f3054750b38c"
