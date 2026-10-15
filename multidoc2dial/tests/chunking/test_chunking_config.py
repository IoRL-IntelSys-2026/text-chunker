"""Настройки нарезки: без записанного лимита длина фрагмента ничем не ограничена."""

from __future__ import annotations

from pathlib import Path

import pytest

from preprocessing.chunking_config import load_chunking_config

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "chunking" / "mdd_sections_512.yaml"


def test_mdd_sections_config_records_limit_overlap_minimum_and_name() -> None:
    """В конфиге записаны лимит 512, перекрытие 64, минимум 24 и имя способа нарезки по разделам."""
    config = load_chunking_config(CONFIG)
    assert config["max_tokens"] == 512
    assert config["overlap_tokens"] == 64
    assert config["min_tokens"] == 24
    assert config["chunker"] == "mdd-sections+recursive/v1/512/64"


def test_config_without_max_tokens_is_rejected(tmp_path: Path) -> None:
    """Файл без лимита max_tokens отвергается, чтобы нарезка не выпустила кусок любой длины."""
    path = tmp_path / "no_limit.yaml"
    path.write_text("overlap_tokens: 64\nmin_tokens: 24\n", encoding="utf-8")
    with pytest.raises(ValueError, match="max_tokens"):
        load_chunking_config(path)
