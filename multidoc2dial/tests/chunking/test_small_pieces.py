"""Долго: грузит токенизатор bge-m3, один тест проходит весь снимок.

Кусок короче 24 токенов почти ничего не ищет. Его склеивают с соседом того же раздела или отбрасывают.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from preprocessing.chunk_document import ChunkDocument, load_chunk_documents
from preprocessing.chunking_config import load_chunking_config
from preprocessing.long_sections import SectionPiece, split_long_sections
from preprocessing.small_pieces import drop_small_pieces
from preprocessing.token_count import count_tokens

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_chunking_config(ROOT / "configs" / "chunking" / "mdd_sections_512.yaml")
SNAPSHOT = ROOT / "data" / "snapshots" / "mdd_v1"
TOKENIZER = CONFIG["tokenizer"]
MIN_TOKENS = CONFIG["min_tokens"]


def test_heading_only_piece_merges_with_the_next() -> None:
    """Кусок из одного заголовка склеивается со следующим текстом того же раздела, чтобы в поиске не осталось пустого названия."""
    body = _long("The aid amount depends on family income and school cost.")
    text = f"Part\n\n{body}"
    document = _document(text, "Part")
    pieces = [
        _piece(document, 0, 4, ("Part",)),
        _piece(document, 6, len(text), ("Part",)),
    ]
    kept, report = drop_small_pieces(
        document, pieces, min_tokens=MIN_TOKENS, tokenizer_name=TOKENIZER
    )
    assert report.dropped_short == 0
    assert len(kept) == 1
    assert kept[0].text == text
    assert kept[0].text.strip() != "Part"


def test_short_piece_without_same_section_neighbor_is_dropped() -> None:
    """Кусок короче 24 токенов без соседа из того же раздела отбрасывается, и это число пишется в отчёт."""
    text = f"{_long('Alpha section stays here.')}\nHi\n{_long('Beta section stays here too.')}"
    hi_at = text.index("Hi")
    document = ChunkDocument(
        doc_id="doc",
        title="Title",
        text=text,
        sections=(
            {"title_path": ["Alpha"], "char_start": 0, "char_end": hi_at},
            {"title_path": ["Alone"], "char_start": hi_at, "char_end": hi_at + 2},
            {"title_path": ["Beta"], "char_start": hi_at + 3, "char_end": len(text)},
        ),
    )
    pieces = [
        _piece(document, 0, hi_at, ("Alpha",)),
        _piece(document, hi_at, hi_at + 2, ("Alone",)),
        _piece(document, hi_at + 3, len(text), ("Beta",)),
    ]
    kept, report = drop_small_pieces(
        document, pieces, min_tokens=MIN_TOKENS, tokenizer_name=TOKENIZER
    )
    assert report.dropped_short == 1
    assert [piece.title_path for piece in kept] == [("Alpha",), ("Beta",)]
    assert all(piece.text.strip() for piece in kept)


def test_short_piece_merges_with_same_section_neighbor() -> None:
    """Короткий кусок с соседом того же раздела склеивается с ним и в отброшенные не попадает."""
    text = f"{_long('The aid amount depends on family income and the school cost.')}\nOk"
    document = _document(text, "Part")
    pieces = [
        _piece(document, 0, text.index("\n"), ("Part",)),
        _piece(document, text.index("Ok"), len(text), ("Part",)),
    ]
    kept, report = drop_small_pieces(
        document, pieces, min_tokens=MIN_TOKENS, tokenizer_name=TOKENIZER
    )
    assert report.dropped_short == 0
    assert len(kept) == 1
    assert kept[0].text == text


def test_snapshot_has_no_empty_or_heading_only_pieces() -> None:
    """На всём снимке после склейки не остаётся пустых кусков и кусков из одного заголовка."""
    for document in load_chunk_documents(SNAPSHOT):
        pieces, _notes = split_long_sections(
            document,
            max_tokens=CONFIG["max_tokens"],
            overlap_tokens=CONFIG["overlap_tokens"],
            tokenizer_name=TOKENIZER,
        )
        kept, report = drop_small_pieces(
            document, pieces, min_tokens=MIN_TOKENS, tokenizer_name=TOKENIZER
        )
        assert report.dropped_short >= 0
        for piece in kept:
            assert piece.text.strip()
            titles = [title.strip() for title in piece.title_path if title.strip()]
            assert not titles or piece.text.strip() != titles[-1]
            if not piece.header_repeated:
                assert piece.text == document.text[piece.char_start : piece.char_end]


def _long(sentence: str) -> str:
    text = sentence
    while count_tokens(text, TOKENIZER) < MIN_TOKENS:
        text = f"{text} {sentence}"
    return text


def _document(text: str, title: str) -> ChunkDocument:
    return ChunkDocument(
        doc_id="doc",
        title=title,
        text=text,
        sections=({"title_path": [title], "char_start": 0, "char_end": len(text)},),
    )


def _piece(document: ChunkDocument, start: int, end: int, title_path: tuple[str, ...]) -> SectionPiece:
    return SectionPiece(document.doc_id, title_path, start, end, document.text[start:end], False)
