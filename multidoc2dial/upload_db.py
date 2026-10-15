"""Запись уже собранных фрагментов в коллекцию Qdrant.

Снимок, нарезка и векторы к этому моменту уже лежат на диске.
Алиас mdd_current эта команда не ставит.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient, models

from preprocessing.chunking_config import load_chunking_config
from preprocessing.index_info import write_index_info
from preprocessing.upload_chunks import COLLECTION, upload_chunks
from rag_common.embeddings import DENSE_SIZE

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "chunking" / "mdd_sections_512.yaml"
CHUNKS = ROOT / "data" / "index" / "mdd_chunks_v1" / "chunks.jsonl"
VECTORS = ROOT / "data" / "index" / "mdd_chunks_v1" / "vectors.jsonl"
INFO = ROOT / "data" / "index" / "mdd_chunks_v1" / "index_info.json"
EMBEDDING_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
PAYLOAD_FIELDS = ("doc_id", "source", "section", "lang", "url", "content_type")


def main() -> None:
    env = _env()
    for path in (CHUNKS, VECTORS):
        if not path.is_file():
            raise SystemExit(f"Нет файла {path}. Сначала соберите снимок, фрагменты и векторы.")
    client = QdrantClient(
        url=_url(env["QDRANT_URL"]),
        api_key=env["QDRANT_API_KEY"],
        timeout=60,
        prefer_grpc=False,
    )
    _ensure_collection(client)
    moment = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sent = upload_chunks(CHUNKS, VECTORS, client, indexed_at=moment)
    write_index_info(
        CHUNKS,
        INFO,
        client,
        load_chunking_config(CONFIG),
        collection=COLLECTION,
        snapshot_id="mdd_v1",
        embedding_model_revision=EMBEDDING_REVISION,
        created_at=moment,
    )
    print(f"В коллекции {COLLECTION} записано точек: {sent}", flush=True)


def _env() -> dict[str, str]:
    path = ROOT / ".env"
    env: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key] = value.strip()
    if not env.get("QDRANT_URL") or not env.get("QDRANT_API_KEY"):
        raise SystemExit(
            "Эту команду запускать только когда в .env есть\n"
            "QDRANT_URL=...\n"
            "QDRANT_API_KEY=..."
        )
    return env


def _url(value: str) -> str:
    url = value.rstrip("/")
    if ":" not in url.split("//", 1)[-1]:
        url += ":6333"
    return url


def _ensure_collection(client: QdrantClient) -> None:
    if client.collection_exists(COLLECTION):
        return
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config={
            "dense": models.VectorParams(size=DENSE_SIZE, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )
    for field in PAYLOAD_FIELDS:
        client.create_payload_index(
            collection_name=COLLECTION,
            field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


if __name__ == "__main__":
    sys.exit(main())
