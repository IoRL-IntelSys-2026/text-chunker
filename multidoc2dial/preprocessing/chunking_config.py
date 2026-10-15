"""Чтение конфига нарезки.

Лимит max_tokens обязателен. Без него длина фрагмента ничем не ограничена.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def load_chunking_config(path: Path) -> dict:
    """Читает yaml-конфиг. Останавливается, если лимит max_tokens не задан числом."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Конфиг нарезки должен быть набором полей")
    limit = raw.get("max_tokens")
    if type(limit) is not int or limit <= 0:
        raise ValueError("В конфиге нарезки нет лимита max_tokens")
    return raw
