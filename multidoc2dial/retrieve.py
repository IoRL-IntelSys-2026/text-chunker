"""Поиск фрагментов по строке запроса.

Запрос считается той же моделью bge-m3. Qdrant ищет по смыслу и по словам
и склеивает два списка. Наружу отдаются карточки найденных фрагментов.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "packages"))
sys.path.insert(0, str(ROOT))

from qdrant_client import QdrantClient, models

from rag_common.embeddings import get_embedder

COLLECTION = "mdd_chunks_v1"
TOP_K = 5
PREFETCH = 20
RRF_K = 60


def retrieve(query: str, client, embedder, *, limit: int = TOP_K) -> list[dict]:
    """Возвращает до limit фрагментов, ближайших к строке запроса."""
    text = query.strip()
    if not text:
        raise ValueError("пустой запрос")
    if limit < 1:
        raise ValueError("нужен хотя бы один фрагмент")
    encoded = embedder.encode_query(text)
    found = client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            models.Prefetch(query=list(encoded.dense), using="dense", limit=PREFETCH),
            models.Prefetch(
                query=models.SparseVector(
                    indices=list(encoded.sparse.indices),
                    values=list(encoded.sparse.values),
                ),
                using="sparse",
                limit=PREFETCH,
            ),
        ],
        query=models.RrfQuery(rrf=models.Rrf(k=RRF_K)),
        limit=limit,
        with_payload=True,
    )
    hits = []
    for point in found.points:
        payload = point.payload or {}
        hits.append({
            "score": point.score,
            "chunk_id": payload.get("chunk_id"),
            "title": payload.get("title"),
            "url": payload.get("url"),
            "text": payload.get("text"),
        })
    return hits


def main() -> None:
    """Читает запрос из аргументов или с клавиатуры и печатает фрагменты."""
    import os

    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["TQDM_DISABLE"] = "1"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        query = input("Запрос: ").strip()
    from answer import compose_answer, get_answer_model

    hits = retrieve(query, _client(), get_embedder(), limit=3)
    if not hits:
        print("Ничего не найдено.", flush=True)
        return
    model = get_answer_model()
    text = compose_answer(query, hits, model)
    print("\nОтвет:\n", flush=True)
    print(text, flush=True)
    print("\nИсточники:", flush=True)
    for index, hit in enumerate(hits, start=1):
        print(f"[{index}] {hit['title']}", flush=True)
        print(hit["url"], flush=True)


def _client() -> QdrantClient:
    env = {}
    for line in Path(".env").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            env[key] = value
    url = env["QDRANT_URL"].rstrip("/")
    if ":" not in url.split("//", 1)[-1]:
        url += ":6333"
    return QdrantClient(url=url, api_key=env["QDRANT_API_KEY"], timeout=60, prefer_grpc=False)


if __name__ == "__main__":
    main()
