"""Чтение учебных документов multidoc2dial из zip в памяти.

Архив на диск не распаковывается. Файлы диалогов не открываются.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

from rag_common.mdd.mdd import _require_archive_hash

DOCUMENTS_MEMBER = "multidoc2dial/multidoc2dial_doc.json"


@dataclass(frozen=True)
class MddDocument:
    """Один учебный документ из архива, ещё без нашего doc_id."""

    domain: str
    source_doc_id: str
    title: str
    doc_text: str
    spans: dict


def iter_documents(archive: Path):
    """Читает 488 документов из zip в памяти и ничего не пишет на диск.

    Документы лежат в doc_data[домен][исходный doc_id].
    Если контрольная сумма архива не совпала, чтение останавливается.
    """
    archive = Path(archive)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    _require_archive_hash(archive)

    with zipfile.ZipFile(archive) as bundle:
        payload = json.loads(bundle.read(DOCUMENTS_MEMBER))

    for domain, docs in payload["doc_data"].items():
        for source_doc_id, doc in docs.items():
            if doc.get("domain") != domain or doc.get("doc_id") != source_doc_id:
                raise ValueError(f"документ {domain}/{source_doc_id} не совпал с сеткой doc_data")
            yield MddDocument(
                domain=domain,
                source_doc_id=source_doc_id,
                title=doc["title"],
                doc_text=doc["doc_text"],
                spans=doc["spans"],
            )
