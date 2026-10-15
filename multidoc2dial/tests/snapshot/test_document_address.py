"""Адрес документа и короткий номер файла.

Адрес mdd:// — постоянное имя страницы. doc_id считается из него и становится именем txt.
"""

from __future__ import annotations

from pathlib import Path

from rag_common.mdd.documents import iter_documents
from rag_common.mdd.ids import k1_doc_id, k1_url, make_doc_id

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "cache" / "multidoc2dial.zip"
SOURCE_WITH_SPECIALS = "Top 5|Mistakes#3_0"


def test_t_pre_01_k1_url_encodes_space_pipe_and_hash() -> None:
    """Пробел, вертикальная черта и решётка в исходном номере кодируются в адресе, иначе их нельзя положить в путь."""
    assert k1_url("dmv", SOURCE_WITH_SPECIALS) == "mdd://dmv/Top%205%7CMistakes%233_0"


def test_t_cmn_10_doc_id_matches_recorded_uuid() -> None:
    """Один и тот же адрес всегда даёт один и тот же doc_id, повторный запуск не переименовывает файл."""
    url = k1_url("dmv", SOURCE_WITH_SPECIALS)
    assert k1_doc_id("dmv", SOURCE_WITH_SPECIALS) == "ea46edf1-1887-5c61-b896-fe0bdd4b0742"
    assert k1_doc_id("dmv", SOURCE_WITH_SPECIALS) == make_doc_id(url)


def test_step4_same_document_keeps_same_id() -> None:
    """У всех 488 документов номера уникальны и не меняются при повторе. Исходный номер архива хранится отдельно: на него ссылаются диалоги."""
    first = _ids()
    second = _ids()
    assert len(first) == 488
    assert first == second
    assert len(set(first.values())) == 488
    assert all(source_doc_id != our_id for (_, source_doc_id), our_id in first.items())


def _ids() -> dict[tuple[str, str], str]:
    return {
        (document.domain, document.source_doc_id): k1_doc_id(document.domain, document.source_doc_id)
        for document in iter_documents(ARCHIVE)
    }
