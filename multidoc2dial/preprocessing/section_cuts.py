"""Нарезка документа по границам разделов.

Один раздел даёт один кусок: текст[char_start:char_end].
Кусок кончается на границе своего раздела и в соседний не заходит.
"""

from __future__ import annotations

from dataclasses import dataclass

from preprocessing.chunk_document import ChunkDocument


@dataclass(frozen=True)
class SectionCut:
    """Кусок ровно по одному разделу."""

    doc_id: str
    title_path: tuple[str, ...]
    char_start: int
    char_end: int
    text: str


def cut_by_sections(document: ChunkDocument) -> list[SectionCut]:
    """Режет документ по разделам. Текст куска равен срезу документа."""
    cuts = []
    for section in document.sections:
        start = section["char_start"]
        end = section["char_end"]
        if not 0 <= start <= end <= len(document.text):
            raise ValueError(f"раздел {document.doc_id} выходит за текст")
        cuts.append(
            SectionCut(
                doc_id=document.doc_id,
                title_path=tuple(section["title_path"]),
                char_start=start,
                char_end=end,
                text=document.text[start:end],
            )
        )
    return cuts
