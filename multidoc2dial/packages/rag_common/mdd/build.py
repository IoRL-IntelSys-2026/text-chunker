"""Вторая сборка снимка mdd_v1 из архива.

Повторный запуск пишет те же файлы: дата и сумма архива зафиксированы в коде.
"""

from __future__ import annotations

from pathlib import Path

from rag_common.mdd.manifest import write_manifest
from rag_common.mdd.pages import write_pages
from rag_common.mdd.reports import write_reports
from rag_common.mdd.snapshot_info import write_snapshot_info
from rag_common.mdd.structure import write_structure


def build_snapshot(archive: Path, snapshot_dir: Path) -> None:
    """Собирает pages, structure, опись, паспорт и отчёты. Архив не распаковывает."""
    snapshot_dir = Path(snapshot_dir)
    write_pages(archive, snapshot_dir / "pages")
    write_structure(archive, snapshot_dir / "structure")
    write_manifest(archive, snapshot_dir / "manifest.jsonl")
    write_snapshot_info(archive, snapshot_dir / "snapshot_info.json")
    write_reports(archive, snapshot_dir / "reports")
