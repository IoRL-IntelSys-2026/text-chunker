"""Номера фрагментов, общие для всех наборов.

chunk_id — uuid5 от номера документа, имени нарезки и порядкового номера.
Повторный вызов с теми же аргументами даёт тот же номер.
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

# Отдельное пространство имён, чтобы номер фрагмента не совпал с номером документа.
RAG_NS = uuid5(NAMESPACE_URL, "rag-rudn")


def make_chunk_id(doc_id: str, chunker: str, chunk_index: int) -> str:
    """Стабильный номер фрагмента. У другой нарезки тот же порядковый номер даёт другой id."""
    if not isinstance(chunk_index, int) or isinstance(chunk_index, bool) or chunk_index < 0:
        raise ValueError("порядковый номер фрагмента начинается с 0")
    return str(uuid5(RAG_NS, f"{doc_id}:{chunker}:{chunk_index}"))
