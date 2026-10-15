"""Паспорт снимка mdd_v1: версия, сумма архива и число документов.

Тексты, разделы и опись не переписываются.
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_common.mdd.documents import iter_documents
from rag_common.mdd.manifest import FETCHED_AT
from rag_common.mdd.mdd import ARCHIVE_SHA256, file_sha256

ADAPTER_VERSION = "1"


def snapshot_info(archive: Path) -> dict:
    """Собирает паспорт. Сумма берётся с файла архива и сверяется с записанной в коде."""
    archive = Path(archive)
    actual = file_sha256(archive)
    if actual != ARCHIVE_SHA256:
        raise ValueError(f"sha256 архива {actual}, в коде записано {ARCHIVE_SHA256}")
    count = sum(1 for _ in iter_documents(archive))
    return {
        "schema_version": "k1.v1",
        "adapter_version": ADAPTER_VERSION,
        "archive_sha256": actual,
        "document_count": count,
        "created_at": FETCHED_AT,
    }


def write_snapshot_info(archive: Path, info_path: Path) -> dict:
    """Пишет snapshot_info.json. Архив не распаковывает."""
    payload = snapshot_info(archive)
    info_path = Path(info_path)
    info_path.parent.mkdir(parents=True, exist_ok=True)
    info_path.write_bytes(
        (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return payload
