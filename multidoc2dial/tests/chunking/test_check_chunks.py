"""Долго: читает весь снимок и нарезку, считает токены bge-m3.

Проверка, что записанный фрагмент правда взят из страницы и строка для поиска не длиннее лимита.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from preprocessing.chunk_document import ChunkDocument
from preprocessing.check_chunks import check_chunks
from preprocessing.embed_limit import fit_embed_limit
from preprocessing.fragment_card import fragment_card
from preprocessing.long_sections import SectionPiece
from preprocessing.token_count import count_tokens
from preprocessing.write_chunks import write_chunks

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "data" / "snapshots" / "mdd_v1"
CONFIG = ROOT / "configs" / "chunking" / "mdd_sections_512.yaml"
TOKENIZER = "BAAI/bge-m3"


def test_snapshot_chunks_match_the_text_and_repeat() -> None:
    """Срез страницы (символы страницы между char_start и char_end) совпадает с text, пустых фрагментов нет, embed_text не длиннее 512, повтор даёт тот же файл."""
    target = ROOT / "data" / "index" / "mdd_chunks_v1" / "chunks.jsonl"
    count = write_chunks(SNAPSHOT, CONFIG, target)
    assert check_chunks(SNAPSHOT, CONFIG, target) == count


def test_long_search_line_is_split_down_to_the_limit() -> None:
    """Если заголовок вместе с куском длиннее 512 токенов, кусок делится, пока строка для поиска не влезет в лимит."""
    sentence = "The school calculates aid from family income and the attendance cost. "
    text = sentence * 40
    document = ChunkDocument("doc", "How Aid Is Calculated", text, ())
    piece = SectionPiece("doc", ("What to look for",), 0, len(text), text, False)
    fitted = fit_embed_limit(
        document, [piece], max_tokens=64, overlap_tokens=8, tokenizer_name=TOKENIZER
    )
    assert len(fitted) > 1
    for part in fitted:
        assert part.text == text[part.char_start : part.char_end]
        assert count_tokens(fragment_card(document, part).embed_text, TOKENIZER) <= 64


def test_empty_fragment_is_rejected(tmp_path: Path) -> None:
    """Пустой фрагмент проверка не пропускает: по нему нечего искать и не из чего отвечать."""
    target = tmp_path / "chunks.jsonl"
    write_chunks(SNAPSHOT, CONFIG, target)
    lines = target.read_bytes().decode("utf-8").splitlines()
    row = json.loads(lines[0])
    row["text"] = " "
    lines[0] = json.dumps(row, ensure_ascii=False)
    target.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    with pytest.raises(ValueError, match="пустой"):
        check_chunks(SNAPSHOT, CONFIG, target)
