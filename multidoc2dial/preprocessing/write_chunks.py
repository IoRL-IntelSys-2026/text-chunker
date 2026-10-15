"""Запись фрагментов в chunks.jsonl.

Одна строка — один фрагмент: ссылка на документ из описи и границы в тексте.
Векторов в файле нет. Повторный запуск перезаписывает файл.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from preprocessing.chunk_document import load_chunk_documents
from preprocessing.chunking_config import load_chunking_config
from preprocessing.embed_limit import fit_embed_limit
from preprocessing.fragment_card import fragment_card
from preprocessing.long_sections import split_long_sections
from preprocessing.number_fragments import number_fragments
from preprocessing.small_pieces import drop_small_pieces
from preprocessing.token_count import count_tokens


def write_chunks(snapshot_dir: Path, config_path: Path, chunks_path: Path) -> int:
    """Пишет chunks.jsonl заново. Возвращает число строк."""
    snapshot_dir = Path(snapshot_dir)
    config = load_chunking_config(config_path)
    documents = {document.doc_id: document for document in load_chunk_documents(snapshot_dir)}
    rows = []
    for manifest_row in _manifest_rows(snapshot_dir):
        document = documents[manifest_row["doc_id"]]
        rows.extend(_document_rows(snapshot_dir, document, manifest_row, config))
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    chunks_path = Path(chunks_path)
    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    chunks_path.write_bytes(payload.encode("utf-8"))
    return len(rows)


def _document_rows(snapshot_dir: Path, document, manifest_row: dict, config: dict) -> list[dict]:
    pieces, _notes = split_long_sections(
        document,
        max_tokens=config["max_tokens"],
        overlap_tokens=config["overlap_tokens"],
        tokenizer_name=config["tokenizer"],
    )
    kept, _report = drop_small_pieces(
        document,
        pieces,
        min_tokens=config["min_tokens"],
        tokenizer_name=config["tokenizer"],
    )
    kept = fit_embed_limit(
        document,
        kept,
        max_tokens=config["max_tokens"],
        overlap_tokens=config["overlap_tokens"],
        tokenizer_name=config["tokenizer"],
    )
    cards = [fragment_card(document, piece) for piece in kept]
    numbered = number_fragments(cards, config["chunker"])
    return [
        _fragment_row(snapshot_dir.name, manifest_row, item, config["tokenizer"], config["embedding_model"])
        for item in numbered
    ]


def _fragment_row(snapshot_id: str, manifest_row: dict, item, tokenizer_name: str, embedding_model: str) -> dict:
    """Строка K2 без векторов и без indexed_at."""
    card = item.card
    return {
        "schema_version": "k2.v1",
        "chunk_id": item.chunk_id,
        "doc_id": card.doc_id,
        "source": manifest_row["source"],
        "source_doc_id": manifest_row["source_doc_id"],
        "url": manifest_row["url"],
        "content_type": manifest_row["content_type"],
        "title": card.title,
        "breadcrumbs": list(card.breadcrumbs),
        "section": manifest_row["section"],
        "lang": manifest_row["lang"],
        "headings": list(card.headings),
        "chunk_index": item.chunk_index,
        "n_chunks": item.n_chunks,
        "text": card.text,
        "char_start": card.char_start,
        "char_end": card.char_end,
        "embed_text": card.embed_text,
        "token_count": count_tokens(card.text, tokenizer_name),
        "has_generated_text": card.has_generated_text,
        "content_hash": hashlib.sha256(card.text.encode("utf-8")).hexdigest(),
        "doc_content_hash": manifest_row["content_hash"],
        "snapshot_id": snapshot_id,
        "last_modified": manifest_row["last_modified"],
        "last_modified_source": manifest_row.get("last_modified_source"),
        "fetched_at": manifest_row["fetched_at"],
        "md_path": manifest_row["path"],
        "chunker": item.chunker,
        "embedding_model": embedding_model,
    }


def _manifest_rows(snapshot_dir: Path) -> list[dict]:
    rows = []
    for line in (snapshot_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows
