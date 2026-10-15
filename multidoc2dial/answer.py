"""Ответ по найденным фрагментам.

Сначала поиск, затем маленькая локальная модель Qwen2.5-0.5B-Instruct.
Она видит только текст фрагментов и вопрос.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT))

from rag_common.embeddings import get_embedder

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
ANSWER_K = 3
MAX_NEW_TOKENS = 220
TEXT_LIMIT = 1500

_model: "AnswerModel | None" = None


def compose_answer(query: str, hits: list[dict], model) -> str:
    """Просит модель ответить по уже найденным фрагментам."""
    text = query.strip()
    if not text:
        raise ValueError("пустой запрос")
    if not hits:
        raise ValueError("нет фрагментов")
    return model.complete(_messages(text, hits)).strip()


def _messages(query: str, hits: list[dict]) -> list[dict]:
    sources = []
    for index, hit in enumerate(hits, start=1):
        body = (hit.get("text") or "").strip()[:TEXT_LIMIT]
        sources.append(f'[{index}] {hit.get("title") or ""}\n{body}')
    context = "\n\n".join(sources)
    return [
        {
            "role": "system",
            "content": (
                "Write a complete answer in several sentences, in the same language as the question. "
                "Use only the numbered sources. "
                "If they do not contain the answer, say you do not know. "
                "After the answer, cite the source numbers in brackets."
            ),
        },
        {
            "role": "user",
            "content": f"Sources:\n{context}\n\nQuestion: {query}",
        },
    ]


class AnswerModel:
    """Один загруженный экземпляр Qwen2.5-0.5B-Instruct."""

    def __init__(self, tokenizer, model) -> None:
        self._tokenizer = tokenizer
        self._model = model

    def complete(self, messages: list[dict]) -> str:
        prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        output = self._model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            min_new_tokens=40,
            do_sample=False,
            pad_token_id=self._tokenizer.eos_token_id,
        )
        new_tokens = output[0][inputs["input_ids"].shape[1] :]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True)


def get_answer_model() -> AnswerModel:
    """Загружает модель один раз."""
    global _model
    if _model is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if not torch.cuda.is_available():
            raise RuntimeError("PyTorch не видит видеокарту")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, dtype=torch.float16)
        model.to("cuda")
        model.eval()
        _model = AnswerModel(tokenizer, model)
    return _model


def main() -> None:
    """Ищет фрагменты и печатает ответ модели."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        query = input("Запрос: ").strip()
    from retrieve import _client, retrieve

    hits = retrieve(query, _client(), get_embedder(), limit=ANSWER_K)
    if not hits:
        print("Ничего не найдено.")
        return
    print("\nОтвет:\n", flush=True)
    print(compose_answer(query, hits, get_answer_model()), flush=True)
    print("\nИсточники:", flush=True)
    for index, hit in enumerate(hits, start=1):
        print(f"[{index}] {hit['title']}")
        print(hit["url"])


if __name__ == "__main__":
    main()
