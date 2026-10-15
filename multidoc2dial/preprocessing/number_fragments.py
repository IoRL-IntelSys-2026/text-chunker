"""Нумерация фрагментов внутри одного документа.

Номера идут с 0 без пропусков. chunk_id считается из номера документа,
имени нарезки и этого порядкового номера.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag_common.ids import make_chunk_id

from preprocessing.fragment_card import FragmentCard


@dataclass(frozen=True)
class NumberedFragment:
    """Карточка фрагмента с порядковым номером и стабильным chunk_id."""

    card: FragmentCard
    chunk_index: int
    n_chunks: int
    chunk_id: str
    chunker: str


def number_fragments(cards: list[FragmentCard], chunker: str) -> list[NumberedFragment]:
    """Нумерует фрагменты одного документа. Повторный вызов даёт те же chunk_id."""
    doc_ids = {card.doc_id for card in cards}
    if len(doc_ids) > 1:
        raise ValueError("номера ставятся внутри одного документа")
    total = len(cards)
    return [
        NumberedFragment(
            card=card,
            chunk_index=index,
            n_chunks=total,
            chunk_id=make_chunk_id(card.doc_id, chunker, index),
            chunker=chunker,
        )
        for index, card in enumerate(cards)
    ]
