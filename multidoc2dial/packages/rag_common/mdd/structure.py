"""Разделы документа multidoc2dial: границы внутри doc_text.

Из spans берём раздел (id_sec, start_sec, end_sec, заголовок и родители).
Цитаты text_sp в этот файл не пишем. Текст страницы не меняется.
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_common.mdd.documents import MddDocument, iter_documents
from rag_common.mdd.ids import k1_doc_id


def sections_for(document: MddDocument) -> list[dict]:
    """Один объект на раздел: путь заголовков и границы в символах."""
    grouped: dict[str, list[dict]] = {}
    for span in document.spans.values():
        grouped.setdefault(span["id_sec"], []).append(span)

    sections = []
    for spans in grouped.values():
        start = spans[0]["start_sec"]
        end = spans[0]["end_sec"]
        if any(span["start_sec"] != start or span["end_sec"] != end for span in spans):
            raise ValueError(f"у раздела {spans[0]['id_sec']} разные границы")
        if not 0 <= start <= end <= len(document.doc_text):
            raise ValueError(f"раздел {spans[0]['id_sec']} выходит за текст")

        fragment = document.doc_text[start:end]
        chosen = next((span for span in spans if span["title"] and span["title"] in fragment), None)
        if chosen is None:
            chosen = next((span for span in spans if span["title"]), spans[0])

        title_path = [parent["text"] for parent in chosen["parent_titles"]]
        if chosen["title"]:
            title_path.append(chosen["title"])
        sections.append({"title_path": title_path, "char_start": start, "char_end": end})

    sections.sort(key=lambda item: (item["char_start"], item["char_end"], item["title_path"]))
    return sections


def write_structure(archive: Path, structure_dir: Path) -> int:
    """Пишет structure/<наш doc_id>.json. Архив не распаковывает."""
    structure_dir = Path(structure_dir)
    structure_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for document in iter_documents(archive):
        doc_id = k1_doc_id(document.domain, document.source_doc_id)
        payload = json.dumps(sections_for(document), ensure_ascii=False, indent=2) + "\n"
        (structure_dir / f"{doc_id}.json").write_bytes(payload.encode("utf-8"))
        written += 1
    return written
