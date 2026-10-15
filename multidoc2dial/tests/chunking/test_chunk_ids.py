"""Номер фрагмента chunk_id.

Он считается из номера документа, имени нарезки и порядкового номера. Повтор должен дать тот же id, иначе в базе появится вторая точка.
"""

from __future__ import annotations

import pytest

from preprocessing.fragment_card import FragmentCard
from preprocessing.number_fragments import number_fragments
from rag_common.ids import make_chunk_id

DOC_ID = "ea46edf1-1887-5c61-b896-fe0bdd4b0742"
CHUNKER = "mdd-sections+recursive/v1/512/64"


def test_t_cmn_10_chunk_id_matches_recorded_uuid() -> None:
    """Известные документ, нарезка и номер 0 дают заранее записанный chunk_id."""
    assert make_chunk_id(DOC_ID, CHUNKER, 0) == "0b2ac76b-ef96-5f35-a183-0177e4a2497c"


def test_indexes_start_at_zero_and_repeat_keeps_ids() -> None:
    """Номера внутри документа идут с 0 без пропусков. Повтор даёт те же chunk_id, другая нарезка — другие."""
    cards = [_card(DOC_ID), _card(DOC_ID), _card(DOC_ID)]
    first = number_fragments(cards, CHUNKER)
    second = number_fragments(cards, CHUNKER)
    assert [item.chunk_index for item in first] == [0, 1, 2]
    assert {item.n_chunks for item in first} == {3}
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert len({item.chunk_id for item in first}) == 3
    assert first[0].chunk_id == make_chunk_id(DOC_ID, CHUNKER, 0)
    assert number_fragments(cards, "fixed/v1/512/64")[0].chunk_id != first[0].chunk_id


def test_numbering_rejects_mixed_documents() -> None:
    """Нельзя пронумеровать одной пачкой куски разных документов: порядковый номер тогда смешается."""
    cards = [_card(DOC_ID), _card("11111111-1111-1111-1111-111111111111")]
    with pytest.raises(ValueError):
        number_fragments(cards, CHUNKER)


def _card(doc_id: str) -> FragmentCard:
    return FragmentCard(
        doc_id=doc_id,
        title="Title",
        breadcrumbs=(),
        headings=("Section",),
        text="Body",
        embed_text="Title\n\nBody",
        char_start=0,
        char_end=4,
        has_generated_text=False,
    )
