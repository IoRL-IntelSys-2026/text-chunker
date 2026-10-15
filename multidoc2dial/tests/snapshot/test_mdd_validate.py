"""Долго: читает весь готовый снимок и собирает его второй раз.

Проверка, что снимок целый: номера, файлы, хеши и границы сходятся.
Повторная сборка из того же архива должна дать те же файлы байт в байт.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_common.mdd.build import build_snapshot
from rag_common.mdd.validate import validate_snapshot

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "cache" / "multidoc2dial.zip"
SNAPSHOT = ROOT / "data" / "snapshots" / "mdd_v1"


def _files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_t_cmn_01_snapshot_and_identical_rebuild(tmp_path: Path) -> None:
    """Готовый снимок проходит проверку без ошибок, а вторая сборка во временную папку совпадает с ним побайтно."""
    assert validate_snapshot(SNAPSHOT) == []
    rebuilt = tmp_path / "mdd_v1"
    build_snapshot(ARCHIVE, rebuilt)
    assert validate_snapshot(rebuilt) == []
    assert _files(rebuilt) == _files(SNAPSHOT)
