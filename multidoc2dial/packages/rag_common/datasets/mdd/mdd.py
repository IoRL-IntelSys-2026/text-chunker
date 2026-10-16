"""Архив multidoc2dial: копия в кэш и проверка контрольной суммы.

Архив не распаковывается. Если сумма не совпала, чтение останавливается.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

ARCHIVE_NAME = "multidoc2dial.zip"
# sha256 официального zip, посчитан по локальной копии data/cache/multidoc2dial.zip
ARCHIVE_SHA256 = "f0c034c249663d7b3cb08b19cf2cc2c3d101372485be982621d4711931a1ce00"


class ArchiveHashMismatch(Exception):
    """Контрольная сумма архива не совпала с записанной в коде."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_archive_hash(path: Path) -> None:
    actual = file_sha256(path)
    if actual != ARCHIVE_SHA256:
        raise ArchiveHashMismatch(
            f"sha256 архива {actual}, в коде записано {ARCHIVE_SHA256}"
        )


def prepare_archive(source: Path, cache_dir: Path) -> Path:
    """Сверяет sha256 и кладёт zip в cache_dir, не распаковывая его.

    При несовпадении суммы файл в кэш не копируется и чтение останавливается.
    """
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(source)

    _require_archive_hash(source)

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / ARCHIVE_NAME
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return target
