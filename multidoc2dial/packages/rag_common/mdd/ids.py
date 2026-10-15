"""Наш адрес и номер документа multidoc2dial.

Исходный номер сохраняется отдельно: в нём бывают пробелы, | и #,
поэтому именем файла он не становится.
"""

from __future__ import annotations

from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5


def make_doc_id(url: str) -> str:
    """uuid5 от канонического адреса. Повторный вызов даёт тот же номер."""
    return str(uuid5(NAMESPACE_URL, url))


def k1_url(domain: str, source_doc_id: str) -> str:
    """Адрес вида mdd://<тема>/<исходный номер в кодировке URL>."""
    return f"mdd://{domain}/{quote(source_doc_id, safe='')}"


def k1_doc_id(domain: str, source_doc_id: str) -> str:
    """Наш doc_id. Исходный номер в аргументе не меняется."""
    return make_doc_id(k1_url(domain, source_doc_id))
