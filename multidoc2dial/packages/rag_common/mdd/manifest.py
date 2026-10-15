"""Опись снимка mdd_v1: одна строка manifest.jsonl на документ.

Текст в pages/ не переписывается. content_hash считается по нормализованной копии.
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_common.mdd.documents import MddDocument, iter_documents
from rag_common.mdd.ids import k1_doc_id, k1_url
from rag_common.text import normalized_hash

# День сборки описи. Час фиксирован, чтобы повторный запуск в тот же день дал тот же файл.
FETCHED_AT = "2026-09-30T00:00:00Z"


def manifest_row(document: MddDocument) -> dict:
    """Строка K1 для одного учебного документа."""
    doc_id = k1_doc_id(document.domain, document.source_doc_id)
    return {
        "schema_version": "k1.v1",
        "doc_id": doc_id,
        "source": "multidoc2dial",
        "url": k1_url(document.domain, document.source_doc_id),
        "aliases": [],
        "source_doc_id": document.source_doc_id,
        "title": document.title,
        "lang": "en",
        "content_type": "text/plain",
        "path": f"pages/{doc_id}.txt",
        "content_hash": normalized_hash(document.doc_text),
        "section": document.domain,
        "fetched_at": FETCHED_AT,
        "last_modified": None,
    }


def write_manifest(archive: Path, manifest_path: Path) -> int:
    """Пишет manifest.jsonl. Архив не распаковывает и txt-файлы не меняет."""
    rows = [manifest_row(document) for document in iter_documents(archive)]
    rows.sort(key=lambda row: row["doc_id"])
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(payload.encode("utf-8"))
    return len(rows)
