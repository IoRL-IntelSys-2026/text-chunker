"""Кусок ужимается, пока строка для поиска не влезет в лимит.

В строку для поиска входят заголовок документа, путь заголовков и сам кусок.
Лимит считается по этой строке целиком, а не только по тексту куска.
"""

from __future__ import annotations

from preprocessing.chunk_document import ChunkDocument
from preprocessing.fragment_card import fragment_card
from preprocessing.long_sections import SectionPiece, split_inside
from preprocessing.token_count import count_tokens


def fit_embed_limit(
    document: ChunkDocument,
    pieces: list[SectionPiece],
    *,
    max_tokens: int,
    overlap_tokens: int,
    tokenizer_name: str,
) -> list[SectionPiece]:
    """Делит куски, у которых строка для поиска длиннее лимита."""
    fitted: list[SectionPiece] = []
    for piece in pieces:
        fitted.extend(
            _fit_piece(document, piece, max_tokens, overlap_tokens, tokenizer_name, depth=0)
        )
    return fitted


def _fit_piece(
    document: ChunkDocument,
    piece: SectionPiece,
    max_tokens: int,
    overlap_tokens: int,
    tokenizer_name: str,
    depth: int,
) -> list[SectionPiece]:
    embed_tokens = _embed_tokens(document, piece, tokenizer_name)
    if embed_tokens <= max_tokens:
        return [piece]
    if depth > 8:
        raise ValueError(f"кусок {piece.doc_id} не умещается в {max_tokens} токенов")
    body_tokens = count_tokens(piece.text, tokenizer_name)
    if body_tokens <= 1:
        raise ValueError(f"кусок {piece.doc_id} не умещается в {max_tokens} токенов")
    limit = body_tokens - (embed_tokens - max_tokens) - 1
    if limit < 1:
        limit = 1
    if limit >= body_tokens:
        limit = body_tokens - 1
    overlap = overlap_tokens if overlap_tokens < limit else 0
    parts = split_inside(
        document,
        piece,
        max_tokens=limit,
        overlap_tokens=overlap,
        tokenizer_name=tokenizer_name,
    )
    if len(parts) == 1 and parts[0].char_start == piece.char_start and parts[0].char_end == piece.char_end:
        raise ValueError(f"кусок {piece.doc_id} не умещается в {max_tokens} токенов")
    fitted: list[SectionPiece] = []
    for part in parts:
        fitted.extend(
            _fit_piece(document, part, max_tokens, overlap_tokens, tokenizer_name, depth + 1)
        )
    return fitted


def _embed_tokens(document: ChunkDocument, piece: SectionPiece, tokenizer_name: str) -> int:
    return count_tokens(fragment_card(document, piece).embed_text, tokenizer_name)
