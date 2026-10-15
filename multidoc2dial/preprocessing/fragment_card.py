"""Карточка фрагмента: текст куска и отдельная строка для поиска.

В text лежит только кусок документа. Заголовок документа и путь заголовков
пишутся в embed_text. У учебного снимка хлебных крошек нет.
Текст моделью не писался, поэтому has_generated_text всегда false.
"""

from __future__ import annotations

from dataclasses import dataclass

from preprocessing.chunk_document import ChunkDocument
from preprocessing.long_sections import SectionPiece


@dataclass(frozen=True)
class FragmentCard:
    """Один фрагмент после нарезки, ещё без номера."""

    doc_id: str
    title: str
    breadcrumbs: tuple[str, ...]
    headings: tuple[str, ...]
    text: str
    embed_text: str
    char_start: int
    char_end: int
    has_generated_text: bool


def fragment_card(document: ChunkDocument, piece: SectionPiece) -> FragmentCard:
    """Собирает карточку. Заголовок документа в text не вклеивается."""
    headings = _headings(piece.title_path, document.title)
    return FragmentCard(
        doc_id=piece.doc_id,
        title=document.title,
        breadcrumbs=(),
        headings=headings,
        text=piece.text,
        embed_text=_embed_text(document.title, headings, piece.text),
        char_start=piece.char_start,
        char_end=piece.char_end,
        has_generated_text=False,
    )


def _headings(title_path: tuple[str, ...], document_title: str) -> tuple[str, ...]:
    """Путь заголовков без заголовка документа и без подряд одинаковых пунктов."""
    title = document_title.strip()
    headings: list[str] = []
    for item in title_path:
        item = item.strip()
        if not item or item == title:
            continue
        if headings and headings[-1] == item:
            continue
        headings.append(item)
    return tuple(headings)


def _embed_text(title: str, headings: tuple[str, ...], text: str) -> str:
    """Хлебные крошки, заголовок, путь заголовков и текст. Пустые части пропускаются."""
    parts = []
    if title.strip():
        parts.append(title.strip())
    if headings:
        parts.append("\n".join(headings))
    body = text.lstrip("\n")
    if not parts:
        return body
    return "\n".join(parts) + "\n\n" + body
