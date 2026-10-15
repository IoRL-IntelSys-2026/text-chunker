"""Счётчик длины токенизатором bge-m3.

Длина — число кусков текста у модели, а не число букв и не число слов.
Служебные метки начала и конца модель добавляет сама, в длину фрагмента они не входят.
"""

from __future__ import annotations

from functools import lru_cache

from tokenizers import Tokenizer


@lru_cache(maxsize=4)
def _tokenizer(name: str) -> Tokenizer:
    return Tokenizer.from_pretrained(name)


def token_spans(text: str, tokenizer_name: str) -> list[tuple[int, int]]:
    """Границы каждого токена в тексте: (начало, конец) в символах."""
    encoded = _tokenizer(tokenizer_name).encode(text, add_special_tokens=False)
    return [(start, end) for start, end in encoded.offsets]


def count_tokens(text: str, tokenizer_name: str) -> int:
    """Сколько токенов в тексте у названного токенизатора. Повторный вызов даёт то же число."""
    return len(token_spans(text, tokenizer_name))
