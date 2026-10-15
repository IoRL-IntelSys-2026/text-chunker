"""Карточка фрагмента хранит текст куска отдельно от строки для поиска.

В text только срез документа. Заголовок попадает в embed_text, по нему потом считается вектор.
"""

from __future__ import annotations

from preprocessing.chunk_document import ChunkDocument
from preprocessing.fragment_card import fragment_card
from preprocessing.long_sections import SectionPiece


def test_document_title_stays_out_of_text_and_embed_text_is_separate() -> None:
    """Заголовок документа не вклеен в text. embed_text собран из заголовка и куска. Текст не помечен как написанный моделью."""
    document = ChunkDocument(
        doc_id="doc",
        title="How Aid Is Calculated",
        text="Section\n\nThe school calculates the aid amount.",
        sections=({"title_path": ["Section", "Section"], "char_start": 0, "char_end": 10},),
    )
    piece = SectionPiece(
        "doc",
        ("Section", "Section", "How Aid Is Calculated"),
        9,
        44,
        "The school calculates the aid amount.",
        False,
    )
    card = fragment_card(document, piece)
    assert card.text == piece.text
    assert not card.text.startswith(document.title)
    assert card.embed_text.startswith(document.title)
    assert card.text in card.embed_text
    assert card.embed_text != card.text
    assert card.breadcrumbs == ()
    assert card.headings == ("Section",)
    assert card.has_generated_text is False
