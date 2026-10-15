"""Векторы пишутся пачками, по одной строке на фрагмент и в том же порядке, что chunks.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

from rag_common.embeddings import DENSE_SIZE, MODEL_NAME, Embedder
from preprocessing.embed_chunks import write_vectors


def test_vectors_match_chunk_rows_and_are_encoded_in_batches(tmp_path: Path) -> None:
    """Число строк векторов равно числу фрагментов. Модель получает пачку текстов, а не по одному."""
    chunks = tmp_path / "chunks.jsonl"
    lines = [
        {"chunk_id": f"id-{index}", "embed_text": f"fragment {index}"}
        for index in range(5)
    ]
    chunks.write_bytes(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in lines).encode("utf-8")
    )
    model = _BatchModel()
    target = tmp_path / "vectors.jsonl"
    count = write_vectors(chunks, target, Embedder(model, MODEL_NAME), batch_size=2, max_length=512)
    assert count == 5
    assert model.sizes == [2, 2, 1]
    vectors = [json.loads(line) for line in target.read_bytes().decode("utf-8").splitlines()]
    assert [row["chunk_id"] for row in vectors] == [row["chunk_id"] for row in lines]
    assert all(len(row["dense"]) == DENSE_SIZE for row in vectors)
    assert vectors[0]["sparse_indices"] == [1, 4]


class _BatchModel:
    def __init__(self) -> None:
        self.sizes: list[int] = []

    def encode(self, texts, return_dense, return_sparse, return_colbert_vecs, batch_size, max_length):
        assert return_dense is True and return_sparse is True and return_colbert_vecs is False
        assert batch_size == 2
        assert max_length == 512
        self.sizes.append(len(texts))
        return {
            "dense_vecs": [[0.2] * DENSE_SIZE for _text in texts],
            "lexical_weights": [{4: 0.25, 1: 0.5} for _text in texts],
        }
