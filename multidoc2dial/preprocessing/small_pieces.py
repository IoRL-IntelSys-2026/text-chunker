"""Мелкие куски убираются после нарезки.

Кусок из одного заголовка склеивается со следующим из того же раздела.
Кусок короче минимума склеивается с соседом того же раздела или отбрасывается.
"""

from __future__ import annotations

from dataclasses import dataclass

from preprocessing.chunk_document import ChunkDocument
from preprocessing.long_sections import SectionPiece
from preprocessing.token_count import count_tokens


@dataclass(frozen=True)
class SmallPieceReport:
    """Сколько кусков короче минимума не удалось склеить и пришлось отбросить."""

    dropped_short: int


def drop_small_pieces(
    document: ChunkDocument,
    pieces: list[SectionPiece],
    *,
    min_tokens: int,
    tokenizer_name: str,
) -> tuple[list[SectionPiece], SmallPieceReport]:
    """Возвращает куски без пустых и без кусков из одного заголовка."""
    merged = _merge_headings(document, pieces)
    kept, dropped_short = _merge_or_drop_short(document, merged, min_tokens, tokenizer_name)
    kept, dropped_short = _drop_leftover_headings(kept, dropped_short, min_tokens, tokenizer_name)
    return kept, SmallPieceReport(dropped_short)


def _merge_headings(document: ChunkDocument, pieces: list[SectionPiece]) -> list[SectionPiece]:
    merged: list[SectionPiece] = []
    index = 0
    while index < len(pieces):
        piece = pieces[index]
        nxt = index + 1
        if (
            _is_heading_only(piece)
            and nxt < len(pieces)
            and pieces[nxt].title_path == piece.title_path
        ):
            merged.append(_merge(document, piece, pieces[nxt]))
            index += 2
            continue
        merged.append(piece)
        index += 1
    return merged


def _merge_or_drop_short(
    document: ChunkDocument,
    pieces: list[SectionPiece],
    min_tokens: int,
    tokenizer_name: str,
) -> tuple[list[SectionPiece], int]:
    dropped = 0
    current = list(pieces)
    while True:
        kept: list[SectionPiece] = []
        changed = False
        index = 0
        while index < len(current):
            piece = current[index]
            if not _is_short(piece, min_tokens, tokenizer_name):
                kept.append(piece)
                index += 1
                continue
            if kept and kept[-1].title_path == piece.title_path:
                kept[-1] = _merge(document, kept[-1], piece)
                changed = True
            elif index + 1 < len(current) and current[index + 1].title_path == piece.title_path:
                current[index + 1] = _merge(document, piece, current[index + 1])
                changed = True
            else:
                dropped += 1
            index += 1
        current = kept
        if not changed:
            return current, dropped


def _merge(document: ChunkDocument, left: SectionPiece, right: SectionPiece) -> SectionPiece:
    start = min(left.char_start, right.char_start)
    end = max(left.char_end, right.char_end)
    if left.header_repeated or right.header_repeated:
        earlier, later = (left, right) if left.char_start <= right.char_start else (right, left)
        extra = document.text[later.char_start : later.char_end]
        text = earlier.text if extra and extra in earlier.text else f"{earlier.text}\n{extra}".strip()
        return SectionPiece(left.doc_id, left.title_path, start, end, text, True)
    return SectionPiece(left.doc_id, left.title_path, start, end, document.text[start:end], False)


def _drop_leftover_headings(
    pieces: list[SectionPiece],
    dropped_short: int,
    min_tokens: int,
    tokenizer_name: str,
) -> tuple[list[SectionPiece], int]:
    """Заголовок без текста рядом не остаётся. Короткий такой кусок считается отброшенным."""
    kept = []
    for piece in pieces:
        if not piece.text.strip():
            continue
        if _is_heading_only(piece):
            if count_tokens(piece.text, tokenizer_name) < min_tokens:
                dropped_short += 1
            continue
        kept.append(piece)
    return kept, dropped_short


def _is_heading_only(piece: SectionPiece) -> bool:
    body = piece.text.strip()
    titles = [title.strip() for title in piece.title_path if title.strip()]
    return bool(body) and bool(titles) and body == titles[-1]


def _is_short(piece: SectionPiece, min_tokens: int, tokenizer_name: str) -> bool:
    if not piece.text.strip():
        return True
    if _is_heading_only(piece):
        return False
    return count_tokens(piece.text, tokenizer_name) < min_tokens
