"""Стратегия S2: нарезка по разделам structure/ (или заголовкам Markdown).

Общий вызов: chunk(doc) -> list[Chunk].
Текст каждого фрагмента — точный срез документа: text == doc.text[char_start:char_end].
"""

from __future__ import annotations

from dataclasses import dataclass

from preprocessing.chunk_document import ChunkDocument
from preprocessing.embed_limit import fit_embed_limit
from preprocessing.fragment_card import FragmentCard, fragment_card
from preprocessing.long_sections import split_long_sections
from preprocessing.small_pieces import drop_small_pieces


@dataclass(frozen=True)
class Chunk:
    """Один фрагмент после нарезки S2, ещё без номера и chunk_id."""

    doc_id: str
    title: str
    breadcrumbs: tuple[str, ...]
    headings: tuple[str, ...]
    text: str
    embed_text: str
    char_start: int
    char_end: int
    has_generated_text: bool

    @classmethod
    def from_card(cls, card: FragmentCard) -> "Chunk":
        return cls(
            doc_id=card.doc_id,
            title=card.title,
            breadcrumbs=card.breadcrumbs,
            headings=card.headings,
            text=card.text,
            embed_text=card.embed_text,
            char_start=card.char_start,
            char_end=card.char_end,
            has_generated_text=card.has_generated_text,
        )

    def to_card(self) -> FragmentCard:
        return FragmentCard(
            doc_id=self.doc_id,
            title=self.title,
            breadcrumbs=self.breadcrumbs,
            headings=self.headings,
            text=self.text,
            embed_text=self.embed_text,
            char_start=self.char_start,
            char_end=self.char_end,
            has_generated_text=self.has_generated_text,
        )


def chunk(
    doc: ChunkDocument,
    *,
    max_tokens: int,
    overlap_tokens: int,
    min_tokens: int,
    tokenizer_name: str,
) -> list[Chunk]:
    """Режет один документ по разделам. Проверяет срез текста у каждого фрагмента."""
    pieces, _notes = split_long_sections(
        doc,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
        tokenizer_name=tokenizer_name,
    )
    kept, _report = drop_small_pieces(
        doc,
        pieces,
        min_tokens=min_tokens,
        tokenizer_name=tokenizer_name,
    )
    kept = fit_embed_limit(
        doc,
        kept,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
        tokenizer_name=tokenizer_name,
    )
    chunks = [Chunk.from_card(fragment_card(doc, piece)) for piece in kept]
    for item in chunks:
        if doc.text[item.char_start : item.char_end] != item.text:
            raise ValueError(
                f"срез не совпал с text у {item.doc_id} [{item.char_start}:{item.char_end}]"
            )
    return chunks
