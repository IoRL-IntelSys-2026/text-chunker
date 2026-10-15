"""Долго: грузит токенизатор BAAI/bge-m3.

Длина фрагмента считается токенами этой модели. Повтор того же текста должен дать то же число.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from preprocessing.chunking_config import load_chunking_config
from preprocessing.token_count import count_tokens

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "chunking" / "mdd_sections_512.yaml"
SAMPLE = "How aid is calculated for students."


def test_same_text_has_the_same_token_count() -> None:
    """Один и тот же текст дважды даёт одно число токенов, иначе лимит 512 на двух запусках сработал бы по-разному."""
    name = load_chunking_config(CONFIG)["tokenizer"]
    assert name == "BAAI/bge-m3"
    assert count_tokens(SAMPLE, name) == count_tokens(SAMPLE, name) == 8


def test_token_count_is_not_letters_or_words() -> None:
    """Число токенов не равно числу букв и не равно числу слов: лимит в конфиге про куски словаря модели."""
    name = load_chunking_config(CONFIG)["tokenizer"]
    tokens = count_tokens(SAMPLE, name)
    assert tokens != len(SAMPLE)
    assert tokens != len(SAMPLE.split())
