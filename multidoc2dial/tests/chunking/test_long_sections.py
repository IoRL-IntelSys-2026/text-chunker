"""Долго: грузит токенизатор bge-m3, один тест проходит весь снимок.

Раздел длиннее 512 токенов режется внутри своих границ, соседние куски перекрываются.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from preprocessing.chunk_document import ChunkDocument, load_chunk_documents
from preprocessing.chunking_config import load_chunking_config
from preprocessing.long_sections import split_long_sections
from preprocessing.token_count import count_tokens

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_chunking_config(ROOT / "configs" / "chunking" / "mdd_sections_512.yaml")
SNAPSHOT = ROOT / "data" / "snapshots" / "mdd_v1"
TOKENIZER = CONFIG["tokenizer"]
MAX_TOKENS = CONFIG["max_tokens"]
OVERLAP = CONFIG["overlap_tokens"]


def test_long_section_stays_inside_its_bounds_and_overlaps() -> None:
    """Длинный раздел делится на куски не длиннее 512 токенов, и соседние куски повторяют 64 токена на стыке."""
    paragraph = "Aid is calculated from the family income and the school cost. "
    text = "\n\n".join([paragraph] * 40)
    document = _document(text)
    pieces, notes = split_long_sections(
        document, max_tokens=MAX_TOKENS, overlap_tokens=OVERLAP, tokenizer_name=TOKENIZER
    )
    assert notes == []
    assert len(pieces) > 1
    for piece in pieces:
        assert count_tokens(piece.text, TOKENIZER) <= MAX_TOKENS
        assert piece.text == text[piece.char_start : piece.char_end]
        assert 0 <= piece.char_start <= piece.char_end <= len(text)
    for previous, following in zip(pieces, pieces[1:], strict=False):
        assert previous.char_start < following.char_start < previous.char_end
        shared = text[following.char_start : previous.char_end]
        assert count_tokens(shared, TOKENIZER) >= OVERLAP


def test_sentence_longer_than_limit_is_reported() -> None:
    """Предложение длиннее лимита всё равно режется по токенам, и такой разрез попадает в отчёт."""
    text = "word " * 800
    document = _document(text.strip())
    pieces, notes = split_long_sections(
        document, max_tokens=MAX_TOKENS, overlap_tokens=OVERLAP, tokenizer_name=TOKENIZER
    )
    assert len(notes) == 1
    assert notes[0].char_start == 0
    assert notes[0].char_end == len(document.text)
    assert len(pieces) > 1
    for piece in pieces:
        assert count_tokens(piece.text, TOKENIZER) <= MAX_TOKENS
        assert piece.text == document.text[piece.char_start : piece.char_end]
    shared = document.text[pieces[1].char_start : pieces[0].char_end]
    assert count_tokens(shared, TOKENIZER) >= OVERLAP


def test_wide_table_repeats_its_header() -> None:
    """Широкая таблица режется по строкам, и в каждом куске повторяется шапка, иначе строки без названий колонок не читаются."""
    header = "| Program | Cost |"
    separator = "| --- | --- |"
    row = "| Student aid | 1000 |"
    text = "\n".join([header, separator, *([row] * 80)])
    document = _document(text)
    pieces, notes = split_long_sections(
        document, max_tokens=80, overlap_tokens=8, tokenizer_name=TOKENIZER
    )
    assert notes == []
    assert len(pieces) > 1
    for piece in pieces:
        assert piece.text.startswith(header)
        assert count_tokens(piece.text, TOKENIZER) <= 80
        assert piece.char_start >= 0
        assert piece.char_end <= len(text)


def test_snapshot_pieces_stay_inside_sections() -> None:
    """На всём снимке ни один кусок не выходит из своего раздела и не длиннее 512 токенов."""
    for document in load_chunk_documents(SNAPSHOT):
        pieces, _notes = split_long_sections(
            document, max_tokens=MAX_TOKENS, overlap_tokens=OVERLAP, tokenizer_name=TOKENIZER
        )
        for piece in pieces:
            assert count_tokens(piece.text, TOKENIZER) <= MAX_TOKENS
            assert any(
                section["char_start"] <= piece.char_start and piece.char_end <= section["char_end"]
                for section in document.sections
            )
            if not piece.header_repeated:
                assert piece.text == document.text[piece.char_start : piece.char_end]


def _document(text: str) -> ChunkDocument:
    return ChunkDocument(
        doc_id="doc",
        title="Title",
        text=text,
        sections=({"title_path": ["Part"], "char_start": 0, "char_end": len(text)},),
    )
