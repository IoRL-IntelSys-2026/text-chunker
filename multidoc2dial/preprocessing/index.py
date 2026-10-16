"""Индексатор Qdrant: коллекция, upsert, алиас и снапшот коллекции.

Единственный модуль, который пишет в Qdrant.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient, models

from preprocessing.chunking_config import load_chunking_config
from preprocessing.index_info import write_index_info
from preprocessing.upload_chunks import COLLECTION, upload_chunks
from rag_common.embeddings import DENSE_SIZE

ROOT = Path(__file__).resolve().parents[1]
EMBEDDING_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
PAYLOAD_FIELDS = ("doc_id", "source", "section", "lang", "url", "content_type")


def load_qdrant_env(env_path: Path | None = None) -> dict[str, str]:
    """Читает QDRANT_URL и QDRANT_API_KEY из окружения и необязательного .env."""
    path = Path(env_path) if env_path is not None else ROOT / ".env"
    env: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    url = os.environ.get("QDRANT_URL") or env.get("QDRANT_URL")
    key = os.environ.get("QDRANT_API_KEY") or env.get("QDRANT_API_KEY")
    if not url or not key:
        raise RuntimeError(
            "Нужны QDRANT_URL и QDRANT_API_KEY в окружении или в файле .env"
        )
    return {"QDRANT_URL": url, "QDRANT_API_KEY": key}


def make_client(env: dict[str, str] | None = None) -> QdrantClient:
    """Клиент Qdrant из переменных окружения."""
    env = env or load_qdrant_env()
    return QdrantClient(
        url=_url(env["QDRANT_URL"]),
        api_key=env["QDRANT_API_KEY"],
        timeout=60,
        prefer_grpc=False,
    )


def ensure_collection(client: QdrantClient, collection: str = COLLECTION) -> None:
    """Создаёт коллекцию и payload-индексы, если их ещё нет."""
    if client.collection_exists(collection):
        return
    client.create_collection(
        collection_name=collection,
        vectors_config={
            "dense": models.VectorParams(size=DENSE_SIZE, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={"sparse": models.SparseVectorParams()},
    )
    for field in PAYLOAD_FIELDS:
        client.create_payload_index(
            collection_name=collection,
            field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


def index_collection(
    *,
    chunks_path: Path,
    vectors_path: Path,
    info_path: Path,
    config_path: Path,
    collection: str = COLLECTION,
    snapshot_id: str = "mdd_v1",
    client: QdrantClient | None = None,
) -> int:
    """Заливает фрагменты в коллекцию и пишет index_info.json. Возвращает число точек."""
    chunks_path = Path(chunks_path)
    vectors_path = Path(vectors_path)
    for path in (chunks_path, vectors_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    client = client or make_client()
    ensure_collection(client, collection)
    moment = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sent = upload_chunks(
        chunks_path,
        vectors_path,
        client,
        collection=collection,
        indexed_at=moment,
    )
    write_index_info(
        chunks_path,
        Path(info_path),
        client,
        load_chunking_config(config_path),
        collection=collection,
        snapshot_id=snapshot_id,
        embedding_model_revision=EMBEDDING_REVISION,
        created_at=moment,
    )
    return sent


def set_alias(
    *,
    collection: str,
    alias: str,
    client: QdrantClient | None = None,
) -> None:
    """Атомарно вешает alias на коллекцию. Старый alias с тем же именем снимается."""
    client = client or make_client()
    if not client.collection_exists(collection):
        raise FileNotFoundError(f"коллекции {collection} нет в Qdrant")
    operations: list = []
    existing = {item.alias_name for item in client.get_aliases().aliases}
    if alias in existing:
        operations.append(
            models.DeleteAliasOperation(
                delete_alias=models.DeleteAlias(alias_name=alias)
            )
        )
    operations.append(
        models.CreateAliasOperation(
            create_alias=models.CreateAlias(
                collection_name=collection,
                alias_name=alias,
            )
        )
    )
    client.update_collection_aliases(change_aliases_operations=operations)


def create_collection_snapshot(
    *,
    collection: str,
    client: QdrantClient | None = None,
) -> str:
    """Снимает снапшот коллекции в Qdrant. Возвращает имя снапшота."""
    client = client or make_client()
    if not client.collection_exists(collection):
        raise FileNotFoundError(f"коллекции {collection} нет в Qdrant")
    result = client.create_snapshot(collection_name=collection)
    name = getattr(result, "name", None) or str(result)
    return name


def _url(value: str) -> str:
    url = value.rstrip("/")
    if ":" not in url.split("//", 1)[-1]:
        url += ":6333"
    return url
