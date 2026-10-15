"""Документ для нарезки: текст, разделы и заголовок из снимка.

Текст читается из pages/ как есть. Файл страницы эта функция не меняет.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChunkDocument:
    """Один документ, который дальше режем на фрагменты."""

    doc_id: str
    title: str
    text: str
    sections: tuple[dict, ...]


def load_chunk_documents(snapshot_dir: Path) -> list[ChunkDocument]:
    """Собирает документы снимка: текст из pages/, разделы из structure/, заголовок из описи."""
    snapshot_dir = Path(snapshot_dir)
    documents = []
    for line in (snapshot_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        doc_id = row["doc_id"]
        page_bytes = (snapshot_dir / "pages" / f"{doc_id}.txt").read_bytes()
        sections = json.loads((snapshot_dir / "structure" / f"{doc_id}.json").read_text(encoding="utf-8"))
        documents.append(
            ChunkDocument(
                doc_id=doc_id,
                title=row["title"],
                text=page_bytes.decode("utf-8"),
                sections=tuple(sections),
            )
        )
    return documents
