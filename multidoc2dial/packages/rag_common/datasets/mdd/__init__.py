"""Загрузчик учебного архива multidoc2dial (C-PRE-01).

Публичные точки: k1_url, k1_doc_id, make_doc_id, iter_documents.
Сборку снимка K1 вызывает preprocessing.adapters.mdd.build_snapshot.
"""

from rag_common.datasets.mdd.documents import MddDocument, iter_documents
from rag_common.datasets.mdd.ids import k1_doc_id, k1_url, make_doc_id
from rag_common.datasets.mdd.mdd import ARCHIVE_SHA256, file_sha256

__all__ = [
    "ARCHIVE_SHA256",
    "MddDocument",
    "file_sha256",
    "iter_documents",
    "k1_doc_id",
    "k1_url",
    "make_doc_id",
]
