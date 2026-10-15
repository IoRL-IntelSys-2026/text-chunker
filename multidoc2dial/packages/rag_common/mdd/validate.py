"""Проверка снимка mdd_v1 по правилам K1.

Команды rag-validate в проекте ещё нет. Эти проверки закрывают T-CMN-01
для учебного снимка из готового текста: html-страниц сайта здесь нет.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from rag_common.mdd.mdd import ARCHIVE_SHA256
from rag_common.text import normalized_hash

REQUIRED_ROW = (
    "schema_version",
    "doc_id",
    "source",
    "url",
    "aliases",
    "source_doc_id",
    "title",
    "lang",
    "content_type",
    "path",
    "content_hash",
    "section",
    "fetched_at",
    "last_modified",
)


def _utc(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def validate_snapshot(snapshot_dir: Path) -> list[str]:
    """Возвращает список нарушений. Пустой список — снимок проходит проверку."""
    snapshot_dir = Path(snapshot_dir)
    errors: list[str] = []
    if snapshot_dir.name != "mdd_v1":
        errors.append(f"имя снимка {snapshot_dir.name}, для пилота нужно mdd_v1")

    info_path = snapshot_dir / "snapshot_info.json"
    manifest_path = snapshot_dir / "manifest.jsonl"
    reports = snapshot_dir / "reports" / "sections.json"
    for path in (info_path, manifest_path, reports):
        if not path.is_file():
            errors.append(f"нет файла {path.name}")
    if errors:
        return errors

    info = json.loads(info_path.read_text(encoding="utf-8"))
    if info.get("schema_version") != "k1.v1":
        errors.append("в паспорте schema_version не k1.v1")
    if info.get("archive_sha256") != ARCHIVE_SHA256:
        errors.append("в паспорте другая контрольная сумма архива")
    if not _utc(info.get("created_at")):
        errors.append("дата паспорта не в UTC")

    listed = {
        item["section"]: item["document_count"]
        for item in json.loads(reports.read_text(encoding="utf-8"))["sections"]
    }
    rows = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if info.get("document_count") != len(rows):
        errors.append("число документов в паспорте не равно числу строк описи")
    if len({row.get("doc_id") for row in rows}) != len(rows):
        errors.append("doc_id в описи повторяются")

    seen_sections: dict[str, int] = {}
    for index, row in enumerate(rows, start=1):
        missing = [field for field in REQUIRED_ROW if field not in row]
        if missing:
            errors.append(f"строка {index} без полей {', '.join(missing)}")
            continue
        if row["schema_version"] != "k1.v1" or row["source"] != "multidoc2dial":
            errors.append(f"строка {index}: схема или источник не учебные")
        if row["doc_id"] != str(uuid5(NAMESPACE_URL, row["url"])):
            errors.append(f"строка {index}: doc_id не равен uuid5 от адреса")
        if not _utc(row["fetched_at"]) or row["last_modified"] is not None:
            errors.append(f"строка {index}: время не в UTC или заполнена дата изменения")
        page = snapshot_dir / row["path"]
        if not page.is_file():
            errors.append(f"строка {index}: нет файла {row['path']}")
            continue
        text = page.read_text(encoding="utf-8")
        if row["content_hash"] != normalized_hash(text):
            errors.append(f"строка {index}: content_hash не совпал с текстом")
        structure = snapshot_dir / "structure" / f"{row['doc_id']}.json"
        if not structure.is_file():
            errors.append(f"строка {index}: нет файла разделов")
            continue
        for section in json.loads(structure.read_text(encoding="utf-8")):
            start = section["char_start"]
            end = section["char_end"]
            if not 0 <= start <= end <= len(text):
                errors.append(f"{row['doc_id']}: раздел выходит за текст")
                break
        section_name = row["section"]
        seen_sections[section_name] = seen_sections.get(section_name, 0) + 1
        if section_name not in listed:
            errors.append(f"строка {index}: тема {section_name} не описана в sections.json")

    if seen_sections != listed:
        errors.append("числа тем в описи и в sections.json различаются")
    return errors
