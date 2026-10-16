"""Простой поиск: запрос уходит двумя векторами, наружу возвращается текст фрагмента."""

from __future__ import annotations

import pytest
from qdrant_client import models

from rag_common.embeddings import DENSE_SIZE, EmbeddingResult, SparseVec
from retrieve import COLLECTION, RRF_K, retrieve


def test_retrieve_returns_chunk_text() -> None:
    """Найденный фрагмент отдаёт заголовок, адрес и текст."""
    client = _Client()
    hits = retrieve("how is aid calculated", client, _Embedder(), limit=1)
    assert client.collection == COLLECTION
    assert client.query.rrf.k == RRF_K
    assert [item.using for item in client.prefetch] == ["dense", "sparse"]
    assert len(client.prefetch[0].query) == DENSE_SIZE
    assert list(client.prefetch[1].query.indices) == [7, 20]
    assert hits == [{
        "score": 0.5,
        "chunk_id": "chunk-1",
        "title": "How Aid Is Calculated",
        "url": "mdd://studentaid/aid",
        "text": "The colleges calculate the amount.",
    }]


def test_empty_query_is_rejected() -> None:
    """Пустая строка в поиск не отправляется."""
    with pytest.raises(ValueError, match="пустой запрос"):
        retrieve("   ", _Client(), _Embedder())


class _Embedder:
    def encode_query(self, text: str) -> EmbeddingResult:
        assert text == "how is aid calculated"
        return EmbeddingResult(dense=tuple([0.1] * DENSE_SIZE), sparse=SparseVec((7, 20), (0.4, 0.2)))


class _Client:
    def __init__(self) -> None:
        self.collection = ""
        self.prefetch = []
        self.query = None

    def query_points(self, collection_name, prefetch, query, limit, with_payload):
        assert isinstance(query, models.RrfQuery)
        assert limit == 1
        assert with_payload is True
        self.collection = collection_name
        self.prefetch = prefetch
        self.query = query
        point = type("Point", (), {
            "score": 0.5,
            "payload": {
                "chunk_id": "chunk-1",
                "title": "How Aid Is Calculated",
                "url": "mdd://studentaid/aid",
                "text": "The colleges calculate the amount.",
            },
        })()
        return type("Response", (), {"points": [point]})()
