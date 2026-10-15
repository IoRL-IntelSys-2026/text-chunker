"""Эмбеддинги bge-m3: плотный и разреженный векторы за один проход.

Модуль знает одну модель, BAAI/bge-m3. Кэша векторов нет.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

MODEL_NAME = "BAAI/bge-m3"
DENSE_SIZE = 1024

_embedder: Embedder | None = None


@dataclass(frozen=True)
class SparseVec:
    """Разреженный вектор: номера слов и их веса."""

    indices: tuple[int, ...]
    values: tuple[float, ...]


@dataclass(frozen=True)
class EmbeddingResult:
    """Два вектора одного текста."""

    dense: tuple[float, ...]
    sparse: SparseVec


class Embedder:
    """Обёртка над моделью. Документы и запросы считает одна и та же модель."""

    def __init__(self, model, model_name: str = MODEL_NAME) -> None:
        self._model = model
        self.model_name = model_name

    def encode_documents(
        self,
        texts: list[str],
        *,
        batch_size: int = 12,
        max_length: int = 8192,
    ) -> list[EmbeddingResult]:
        """Считает оба вектора для списка текстов пачками, одним проходом модели."""
        return self._encode(texts, batch_size=batch_size, max_length=max_length)

    def encode_query(self, text: str) -> EmbeddingResult:
        """Считает оба вектора для одного запроса той же моделью."""
        return self._encode([text], batch_size=1, max_length=8192)[0]

    def _encode(self, texts: list[str], *, batch_size: int, max_length: int) -> list[EmbeddingResult]:
        if not texts:
            return []
        if batch_size < 1:
            raise ValueError("пачка должна содержать хотя бы один текст")
        raw = self._model.encode(
            texts,
            batch_size=batch_size,
            max_length=max_length,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        dense_rows = raw["dense_vecs"]
        sparse_rows = raw["lexical_weights"]
        if len(dense_rows) != len(texts) or len(sparse_rows) != len(texts):
            raise ValueError("модель вернула не столько векторов, сколько текстов")
        return [
            EmbeddingResult(_dense(row), _sparse(weights))
            for row, weights in zip(dense_rows, sparse_rows, strict=True)
        ]


def get_embedder(model_name: str = MODEL_NAME) -> Embedder:
    """Загружает BAAI/bge-m3. Другое имя модели не принимается."""
    global _embedder
    if model_name != MODEL_NAME:
        raise ValueError("модуль знает только модель BAAI/bge-m3")
    if _embedder is None:
        _embedder = Embedder(_load_model(), MODEL_NAME)
    return _embedder


def _load_model():
    import torch
    from FlagEmbedding import BGEM3FlagModel

    return BGEM3FlagModel(MODEL_NAME, use_fp16=torch.cuda.is_available())


def _dense(row) -> tuple[float, ...]:
    values = tuple(float(item) for item in row)
    if len(values) != DENSE_SIZE or any(math.isnan(item) for item in values):
        raise ValueError("плотный вектор должен содержать 1024 числа")
    return values


def _sparse(weights) -> SparseVec:
    pairs = []
    for key, weight in weights.items():
        value = float(weight)
        if value <= 0:
            continue
        pairs.append((int(key), value))
    pairs.sort(key=lambda item: item[0])
    return SparseVec(
        indices=tuple(index for index, _value in pairs),
        values=tuple(value for _index, value in pairs),
    )
