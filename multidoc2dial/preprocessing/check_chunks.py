"""Проверка нарезки по записанному файлу фрагментов.

Срез документа совпадает с text. Пустых фрагментов нет.
Строка для поиска не длиннее лимита, границы не вылезают из раздела.
Повторный запуск даёт те же строки.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from preprocessing.chunk_document import load_chunk_documents
from preprocessing.chunking_config import load_chunking_config
from preprocessing.token_count import count_tokens
from preprocessing.write_chunks import write_chunks


def check_chunks(snapshot_dir: Path, config_path: Path, chunks_path: Path) -> int:
    """Проверяет chunks.jsonl. При ошибке останавливается. Возвращает число строк."""
    snapshot_dir = Path(snapshot_dir)
    chunks_path = Path(chunks_path)
    config = load_chunking_config(config_path)
    documents = {document.doc_id: document for document in load_chunk_documents(snapshot_dir)}
    rows = _rows(chunks_path)
    if not rows:
        raise ValueError("файл фрагментов пуст")
    problems = []
    for index, row in enumerate(rows, start=1):
        problems.extend(_problems(documents, row, index, config["max_tokens"], config["tokenizer"]))
        if len(problems) >= 20:
            break
    if problems:
        raise ValueError("\n".join(problems))
    with tempfile.TemporaryDirectory() as folder:
        copy = Path(folder) / "chunks.jsonl"
        write_chunks(snapshot_dir, config_path, copy)
        if copy.read_bytes() != chunks_path.read_bytes():
            raise ValueError("повторный запуск дал другие строки")
    return len(rows)


def _problems(documents, row: dict, index: int, max_tokens: int, tokenizer_name: str) -> list[str]:
    document = documents.get(row.get("doc_id"))
    if document is None:
        return [f"строка {index}: документа нет в снимке"]
    start = row.get("char_start")
    end = row.get("char_end")
    text = row.get("text")
    if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
        return [f"строка {index}: нет границ"]
    if not isinstance(text, str) or not text.strip():
        return [f"строка {index}: пустой фрагмент"]
    if not 0 <= start <= end <= len(document.text) or document.text[start:end] != text:
        return [f"строка {index}: срез документа не совпадает с text"]
    embed_text = row.get("embed_text")
    if not isinstance(embed_text, str) or count_tokens(embed_text, tokenizer_name) > max_tokens:
        return [f"строка {index}: embed_text длиннее {max_tokens}"]
    if not _inside_section(document.sections, start, end):
        return [f"строка {index}: границы вылезают из раздела"]
    return []


def _inside_section(sections: tuple[dict, ...] | list[dict], start: int, end: int) -> bool:
    """Кусок лежит внутри одного раздела или внутри соседних с тем же заголовком."""
    if any(section["char_start"] <= start and end <= section["char_end"] for section in sections):
        return _covered(sections, start, end)
    overlapping = [
        section
        for section in sections
        if section["char_start"] < end and section["char_end"] > start
    ]
    top = [section for section in overlapping if not _nested(section, overlapping)]
    if not top:
        return False
    if len({tuple(section["title_path"]) for section in top}) != 1:
        return False
    if start < min(section["char_start"] for section in top):
        return False
    if end > max(section["char_end"] for section in top):
        return False
    return _covered(sections, start, end)


def _nested(section: dict, sections: list[dict]) -> bool:
    for other in sections:
        if other is section:
            continue
        if other["char_start"] <= section["char_start"] and section["char_end"] <= other["char_end"]:
            if other["char_start"] < section["char_start"] or section["char_end"] < other["char_end"]:
                return True
    return False


def _covered(sections, start: int, end: int) -> bool:
    """Каждый символ куска входит хотя бы в один раздел."""
    cursor = start
    for section in sorted(sections, key=lambda item: (item["char_start"], item["char_end"])):
        if section["char_end"] <= cursor or section["char_start"] >= end:
            continue
        if section["char_start"] > cursor:
            return False
        cursor = max(cursor, section["char_end"])
        if cursor >= end:
            return True
    return cursor >= end


def _rows(chunks_path: Path) -> list[dict]:
    rows = []
    for line in chunks_path.read_bytes().decode("utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows
