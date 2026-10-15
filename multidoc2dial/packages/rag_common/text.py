"""Нормализация текста для контрольной суммы описи.

Сам файл документа при этом не меняется: нормализация нужна только хешу.
"""

from __future__ import annotations

import hashlib
import re

_REPEATED_SPACES = re.compile(r" {2,}")


def normalize_text(text: str) -> str:
    """ё→е, без неразрывных пробелов и мягких переносов, повторные пробелы схлопнуты."""
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = text.replace("\u00a0", "").replace("\u00ad", "")
    return _REPEATED_SPACES.sub(" ", text)


def normalized_hash(text: str) -> str:
    """sha256 нормализованного текста, как content_hash для pages/* в K1."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()
