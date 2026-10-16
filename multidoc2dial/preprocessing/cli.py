"""CLI конвейера PRE: python -m preprocessing … или python ingest.py …

Подкоманды: adapt-mdd | accept | chunk | embed | index | quality | all | alias | snapshot.
Каждый шаг перезаписывает свой выход. Шаг convert появится вместе с конвертером.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer

from preprocessing.acceptance import write_acceptance_report
from preprocessing.adapters.mdd import build_snapshot
from preprocessing.embed_chunks import write_vectors
from preprocessing.index import (
    create_collection_snapshot,
    index_collection,
    set_alias,
)
from preprocessing.quality import write_quality_report
from preprocessing.write_chunks import write_chunks

app = typer.Typer(
    name="ingest",
    help="Конвейер PRE: снимок mdd, нарезка, векторы, Qdrant.",
    no_args_is_help=True,
    add_completion=False,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "data" / "cache" / "multidoc2dial.zip"
DEFAULT_SNAPSHOT = ROOT / "data" / "snapshots" / "mdd_v1"
DEFAULT_CONFIG = ROOT / "configs" / "chunking" / "mdd_sections_512.yaml"
DEFAULT_COLLECTION = "mdd_chunks_v1"


def _index_dir(collection: str) -> Path:
    return ROOT / "data" / "index" / collection


def _log(step: str, started: float) -> None:
    typer.echo(f"{step}: {time.perf_counter() - started:.1f} с")


@app.command("adapt-mdd")
def adapt_mdd(
    out: Path = typer.Option(
        DEFAULT_SNAPSHOT,
        "--out",
        help="Папка снимка K1",
        show_default=True,
    ),
    archive: Path = typer.Option(
        DEFAULT_ARCHIVE,
        "--archive",
        help="Учебный zip multidoc2dial",
        show_default=True,
    ),
) -> None:
    """Собрать снимок mdd_v1 из zip без распаковки на диск."""
    started = time.perf_counter()
    if not archive.is_file():
        raise typer.BadParameter(f"нет архива {archive}")
    typer.echo(f"Собираю снимок в {out}")
    build_snapshot(archive, out)
    _log("adapt-mdd", started)


@app.command("accept")
def accept_cmd(
    snapshot: Path = typer.Option(
        DEFAULT_SNAPSHOT,
        "--snapshot",
        help="Папка снимка K1",
        show_default=True,
    ),
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        help="Конфиг с лимитами размеров",
        show_default=True,
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Куда писать acceptance.md (по умолчанию <snapshot>/acceptance.md)",
    ),
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="Код выхода 1, если validate K1 нашёл нарушения",
    ),
) -> None:
    """Приёмочная статистика K1 → acceptance.md (PRE-24)."""
    started = time.perf_counter()
    if not snapshot.is_dir():
        raise typer.BadParameter(f"нет снимка {snapshot}")
    report_path = out or (snapshot / "acceptance.md")
    stats = write_acceptance_report(
        snapshot,
        report_path,
        config_path=config,
    )
    typer.echo(f"Отчёт: {report_path}")
    typer.echo(json.dumps(
        {
            "n_docs": stats["n_docs"],
            "by_content_type": stats["by_content_type"],
            "by_lang": stats["by_lang"],
            "by_section": stats["by_section"],
            "unknown_sections": stats["unknown_sections"],
            "too_large": stats["too_large"],
            "no_outlinks_share": stats["no_outlinks_share"],
        },
        ensure_ascii=False,
    ))
    errors = stats.get("validation_errors") or []
    typer.echo(f"validate K1: {'ок' if not errors else f'нарушений {len(errors)}'}")
    if errors and strict:
        for item in errors[:20]:
            typer.echo(f"  - {item}")
        raise typer.Exit(code=1)
    _log("accept", started)


@app.command("chunk")
def chunk_cmd(
    snapshot: Path = typer.Option(
        DEFAULT_SNAPSHOT,
        "--snapshot",
        help="Папка снимка K1",
        show_default=True,
    ),
    collection: str = typer.Option(
        DEFAULT_COLLECTION,
        "--collection",
        help="Имя коллекции = папка data/index/<collection>",
        show_default=True,
    ),
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        help="Конфиг нарезки",
        show_default=True,
    ),
) -> None:
    """Нарезать документы снимка в chunks.jsonl."""
    started = time.perf_counter()
    chunks_path = _index_dir(collection) / "chunks.jsonl"
    typer.echo(f"Режу фрагменты → {chunks_path}")
    count = write_chunks(snapshot, config, chunks_path)
    typer.echo(f"Фрагментов: {count}")
    _log("chunk", started)


@app.command("embed")
def embed_cmd(
    collection: str = typer.Option(
        DEFAULT_COLLECTION,
        "--collection",
        help="Имя коллекции = папка data/index/<collection>",
        show_default=True,
    ),
) -> None:
    """Посчитать векторы bge-m3 в vectors.jsonl."""
    started = time.perf_counter()
    index_dir = _index_dir(collection)
    chunks_path = index_dir / "chunks.jsonl"
    vectors_path = index_dir / "vectors.jsonl"
    if not chunks_path.is_file():
        raise typer.BadParameter(f"нет файла {chunks_path}; сначала ingest chunk")
    typer.echo(f"Считаю векторы → {vectors_path}")
    count = write_vectors(chunks_path, vectors_path)
    typer.echo(f"Векторов: {count}")
    _log("embed", started)


@app.command("index")
def index_cmd(
    collection: str = typer.Option(
        DEFAULT_COLLECTION,
        "--collection",
        help="Имя коллекции в Qdrant",
        show_default=True,
    ),
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        help="Конфиг нарезки для паспорта",
        show_default=True,
    ),
    snapshot_id: str = typer.Option(
        "mdd_v1",
        "--snapshot-id",
        help="Идентификатор снимка K1 в index_info.json",
        show_default=True,
    ),
) -> None:
    """Залить фрагменты и векторы в Qdrant, записать index_info.json."""
    started = time.perf_counter()
    index_dir = _index_dir(collection)
    sent = index_collection(
        chunks_path=index_dir / "chunks.jsonl",
        vectors_path=index_dir / "vectors.jsonl",
        info_path=index_dir / "index_info.json",
        config_path=config,
        collection=collection,
        snapshot_id=snapshot_id,
    )
    typer.echo(f"В коллекции {collection} записано точек: {sent}")
    _log("index", started)


@app.command("quality")
def quality_cmd(
    collection: str = typer.Option(
        DEFAULT_COLLECTION,
        "--collection",
        help="Имя коллекции = папка data/index/<collection>",
        show_default=True,
    ),
    snapshot: Path = typer.Option(
        DEFAULT_SNAPSHOT,
        "--snapshot",
        help="Снимок K1 для проверки срезов и manifest",
        show_default=True,
    ),
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="Остановиться, если ворота K2 не прошли",
    ),
) -> None:
    """Отчёт quality_report.md и локальные ворота K2 по chunks.jsonl."""
    started = time.perf_counter()
    index_dir = _index_dir(collection)
    chunks_path = index_dir / "chunks.jsonl"
    report_path = index_dir / "quality_report.md"
    if not chunks_path.is_file():
        raise typer.BadParameter(f"нет файла {chunks_path}; сначала ingest chunk")
    snap = snapshot if snapshot.is_dir() else None
    stats = write_quality_report(
        chunks_path=chunks_path,
        report_path=report_path,
        snapshot_dir=snap,
        collection=collection,
        run_gate=True,
    )
    typer.echo(f"Отчёт: {report_path}")
    typer.echo(f"чанков={stats.chunks_total}, dup_ratio={stats.dup_ratio:.6f}")
    typer.echo(f"ворота K2: {'ок' if stats.gate_ok else 'есть замечания'}")
    if not stats.gate_ok:
        for item in stats.gate_problems[:20]:
            typer.echo(f"  - {item}")
        if strict:
            raise typer.Exit(code=1)
    _log("quality", started)


@app.command("all")
def all_cmd(
    snapshot: Path = typer.Option(
        DEFAULT_SNAPSHOT,
        "--snapshot",
        help="Папка снимка K1",
        show_default=True,
    ),
    collection: str = typer.Option(
        DEFAULT_COLLECTION,
        "--collection",
        help="Имя коллекции",
        show_default=True,
    ),
    config: Path = typer.Option(
        DEFAULT_CONFIG,
        "--config",
        help="Конфиг нарезки",
        show_default=True,
    ),
) -> None:
    """Нарезка + отчёт качества + векторы + загрузка в Qdrant. Снимок K1 должен уже быть."""
    started = time.perf_counter()
    if not snapshot.is_dir():
        raise typer.BadParameter(
            f"нет снимка {snapshot}; сначала ingest adapt-mdd"
        )
    chunk_cmd(snapshot=snapshot, collection=collection, config=config)
    quality_cmd(collection=collection, snapshot=snapshot, strict=True)
    embed_cmd(collection=collection)
    index_cmd(
        collection=collection,
        config=config,
        snapshot_id=snapshot.name,
    )
    _log("all", started)


@app.command("alias")
def alias_cmd(
    collection: str = typer.Option(
        ...,
        "--collection",
        help="Коллекция, на которую вешаем имя",
    ),
    alias: str = typer.Option(
        ...,
        "--alias",
        help="Рабочее имя, например mdd_current",
    ),
) -> None:
    """Атомарно назначить alias коллекции (после проверки качества)."""
    started = time.perf_counter()
    set_alias(collection=collection, alias=alias)
    typer.echo(f"Алиас {alias} → {collection}")
    _log("alias", started)


@app.command("snapshot")
def snapshot_cmd(
    collection: str = typer.Option(
        DEFAULT_COLLECTION,
        "--collection",
        help="Коллекция Qdrant для резервной копии",
        show_default=True,
    ),
) -> None:
    """Сохранить снапшот коллекции в Qdrant перед демо или переиндексацией."""
    started = time.perf_counter()
    name = create_collection_snapshot(collection=collection)
    typer.echo(f"Снапшот коллекции {collection}: {name}")
    _log("snapshot", started)


def main(argv: Optional[list[str]] = None) -> None:
    """Точка входа для python -m preprocessing и ingest.py."""
    app(args=argv, prog_name="ingest")


if __name__ == "__main__":
    main()
