"""Ответ собирается из уже найденных фрагментов и вопроса.

Тест подставляет фальшивую модель и не загружает Qwen.
"""

from __future__ import annotations

import pytest

from answer import compose_answer


def test_answer_uses_chunk_text_and_question() -> None:
    """Модель получает текст фрагмента и вопрос. Наружу уходит её ответ, а не сырой кусок."""
    model = _Model()
    text = compose_answer(
        "How is aid calculated?",
        [{"title": "How Aid Is Calculated", "text": "Colleges calculate the amount."}],
        model,
    )
    assert text == "Colleges calculate it [1]."
    user = model.messages[1]["content"]
    assert "Colleges calculate the amount." in user
    assert "How is aid calculated?" in user
    assert "[1]" in user


def test_empty_hits_are_rejected() -> None:
    """Без фрагментов отвечать не из чего, поэтому модель не вызывается."""
    with pytest.raises(ValueError, match="нет фрагментов"):
        compose_answer("question", [], _Model())


class _Model:
    def __init__(self) -> None:
        self.messages = None

    def complete(self, messages):
        self.messages = messages
        return "Colleges calculate it [1]."
