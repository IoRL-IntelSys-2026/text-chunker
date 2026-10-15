"""Запись текста документов multidoc2dial в файлы снимка.

Текст не нормализуется и не конвертируется: в файл попадают байты doc_text.
"""

from __future__ import annotations

from pathlib import Path

from rag_common.mdd.documents import iter_documents
from rag_common.mdd.ids import k1_doc_id


def write_pages(archive: Path, pages_dir: Path) -> int:
    """Пишет pages/<наш doc_id>.txt для каждого документа. Архив не распаковывает."""
    pages_dir = Path(pages_dir)
    pages_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for document in iter_documents(archive):
        doc_id = k1_doc_id(document.domain, document.source_doc_id)
        target = pages_dir / f"{doc_id}.txt"
        target.write_bytes(document.doc_text.encode("utf-8"))
        written += 1
    return written
