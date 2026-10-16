"""Адаптер multidoc2dial → снимок K1.

Собирает pages, structure, опись, паспорт и отчёты из учебного zip.
Архив на диск не распаковывается.
"""

from __future__ import annotations

from pathlib import Path

from rag_common.datasets.mdd.build import build_snapshot as _build_snapshot


def build_snapshot(archive: Path, snapshot_dir: Path) -> None:
    """Собирает снимок mdd_v1. Повторный запуск пишет те же файлы."""
    _build_snapshot(archive, snapshot_dir)
