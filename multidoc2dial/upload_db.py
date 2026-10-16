"""Запись уже собранных фрагментов в коллекцию Qdrant.

Снимок, нарезка и векторы к этому моменту уже лежат на диске.
Алиас mdd_current эта команда не ставит.
Предпочтительный запуск: python ingest.py index
"""

from __future__ import annotations

import sys
from pathlib import Path

from preprocessing.index import index_collection
from preprocessing.upload_chunks import COLLECTION

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "chunking" / "mdd_sections_512.yaml"
CHUNKS = ROOT / "data" / "index" / "mdd_chunks_v1" / "chunks.jsonl"
VECTORS = ROOT / "data" / "index" / "mdd_chunks_v1" / "vectors.jsonl"
INFO = ROOT / "data" / "index" / "mdd_chunks_v1" / "index_info.json"


def main() -> None:
    sent = index_collection(
        chunks_path=CHUNKS,
        vectors_path=VECTORS,
        info_path=INFO,
        config_path=CONFIG,
        collection=COLLECTION,
        snapshot_id="mdd_v1",
    )
    print(f"В коллекции {COLLECTION} записано точек: {sent}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
