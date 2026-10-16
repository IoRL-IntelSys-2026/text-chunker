"""Отчёт о качестве нарезки и локальные ворота K2 (C-PRE-09).

Пишет data/index/<collection>/quality_report.md.
На mdd ненулевой dup_ratio ожидаем; порог 2 % и пометка баг-репорта — для РУДН.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

from rag_common.text import normalize_text

K2_REQUIRED = (
    "schema_version",
    "chunk_id",
    "doc_id",
    "source",
    "url",
    "content_type",
    "title",
    "breadcrumbs",
    "headings",
    "chunk_index",
    "n_chunks",
    "text",
    "char_start",
    "char_end",
    "embed_text",
    "token_count",
    "has_generated_text",
    "content_hash",
    "doc_content_hash",
    "snapshot_id",
    "fetched_at",
    "md_path",
    "chunker",
    "embedding_model",
)
COLLECTION_RE = re.compile(
    r"^[a-z0-9]+_(?:chunks|exp_[a-z0-9]+)_v\d+$",
    re.I,
)
RUDN_DUP_THRESHOLD = 0.02


@dataclass
class DupGroup:
    text_hash: str
    count: int
    doc_ids: list[str]
    sample_urls: list[str]
    sample_text: str


@dataclass
class QualityStats:
    snapshot_id: str
    collection: str
    manifest_documents: int
    chunks_total: int
    token_min: int | None
    token_median: float | None
    token_p95: float | None
    token_max: int | None
    histogram: list[tuple[str, int]]
    dropped_short: int | None
    merged_headings: int | None
    dup_ratio: float
    top_groups: list[DupGroup]
    lang_counts: dict[str, int]
    content_type_counts: dict[str, int]
    status_counts: dict[str, int]
    step_times_s: dict[str, float]
    versions: dict[str, str]
    needs_prs_bug: bool
    gate_ok: bool
    gate_problems: list[str] = field(default_factory=list)


def write_quality_report(
    *,
    chunks_path: Path,
    report_path: Path,
    snapshot_dir: Path | None = None,
    collection: str,
    step_times_s: dict[str, float] | None = None,
    dropped_short: int | None = None,
    merged_headings: int | None = None,
    run_gate: bool = True,
) -> QualityStats:
    """Считает метрики, пишет quality_report.md. Возвращает статистику."""
    chunks_path = Path(chunks_path)
    report_path = Path(report_path)
    rows = _load_chunks(chunks_path)
    if not rows:
        raise ValueError(f"файл фрагментов пуст: {chunks_path}")

    snapshot_id = str(rows[0].get("snapshot_id") or "unknown")
    manifest_documents = 0
    status_counts: dict[str, int] = {}
    if snapshot_dir is not None and (Path(snapshot_dir) / "manifest.jsonl").is_file():
        manifest_rows = _load_jsonl(Path(snapshot_dir) / "manifest.jsonl")
        manifest_documents = len(manifest_rows)
        status_counts = {"ok": manifest_documents}
    else:
        manifest_documents = len({row["doc_id"] for row in rows})
        status_counts = {"unknown": manifest_documents}

    tokens = [int(row["token_count"]) for row in rows if isinstance(row.get("token_count"), int)]
    token_min = min(tokens) if tokens else None
    token_max = max(tokens) if tokens else None
    token_median = float(median(tokens)) if tokens else None
    token_p95 = _percentile(tokens, 95) if tokens else None
    histogram = _histogram(tokens)

    dup_ratio, top_groups = _duplicate_groups(rows)
    source = str(rows[0].get("source") or "")
    needs_prs_bug = dup_ratio >= RUDN_DUP_THRESHOLD and source not in {"multidoc2dial", "mdd"}

    lang_counts = dict(Counter(str(row.get("lang") or "unknown") for row in rows))
    # по документам, не по чанкам
    by_doc_lang: dict[str, str] = {}
    by_doc_type: dict[str, str] = {}
    for row in rows:
        doc_id = str(row["doc_id"])
        by_doc_lang.setdefault(doc_id, str(row.get("lang") or "unknown"))
        by_doc_type.setdefault(doc_id, str(row.get("content_type") or "unknown"))
    lang_counts = dict(Counter(by_doc_lang.values()))
    content_type_counts = dict(Counter(by_doc_type.values()))

    versions = {
        "schema_version": str(rows[0].get("schema_version") or ""),
        "chunker": str(rows[0].get("chunker") or ""),
        "embedding_model": str(rows[0].get("embedding_model") or ""),
    }

    gate_problems: list[str] = []
    if run_gate:
        gate_problems = check_k2_chunks(
            rows,
            collection=collection,
            snapshot_dir=Path(snapshot_dir) if snapshot_dir is not None else None,
        )

    stats = QualityStats(
        snapshot_id=snapshot_id,
        collection=collection,
        manifest_documents=manifest_documents,
        chunks_total=len(rows),
        token_min=token_min,
        token_median=token_median,
        token_p95=token_p95,
        token_max=token_max,
        histogram=histogram,
        dropped_short=dropped_short,
        merged_headings=merged_headings,
        dup_ratio=dup_ratio,
        top_groups=top_groups[:20],
        lang_counts=lang_counts,
        content_type_counts=content_type_counts,
        status_counts=status_counts,
        step_times_s=dict(step_times_s or {}),
        versions=versions,
        needs_prs_bug=needs_prs_bug,
        gate_ok=not gate_problems,
        gate_problems=gate_problems,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(stats), encoding="utf-8")
    return stats


def check_k2_chunks(
    rows: list[dict] | None = None,
    *,
    chunks_path: Path | None = None,
    collection: str,
    snapshot_dir: Path | None = None,
) -> list[str]:
    """Локальные ворота K2 по chunks.jsonl. Пустой список — ок."""
    if rows is None:
        if chunks_path is None:
            raise ValueError("нужны rows или chunks_path")
        rows = _load_chunks(chunks_path)
    problems: list[str] = []
    if not COLLECTION_RE.match(collection):
        problems.append(
            f"имя коллекции {collection!r} не по правилу K2 "
            "(ожидается <source>_chunks_vN или <source>_exp_<кратко>_vN)"
        )
    if not rows:
        return problems + ["файл фрагментов пуст"]

    pages: dict[str, str] = {}
    manifest_hashes: dict[str, str] = {}
    if snapshot_dir is not None:
        snapshot_dir = Path(snapshot_dir)
        for line in (snapshot_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            item = json.loads(line)
            manifest_hashes[item["doc_id"]] = item["content_hash"]
            page = snapshot_dir / "pages" / f"{item['doc_id']}.txt"
            if page.is_file():
                pages[item["doc_id"]] = page.read_text(encoding="utf-8")

    for index, row in enumerate(rows, start=1):
        for key in K2_REQUIRED:
            if key not in row:
                problems.append(f"строка {index}: нет поля {key}")
        if row.get("schema_version") != "k2.v1":
            problems.append(f"строка {index}: schema_version != k2.v1")
        if row.get("has_generated_text") is not False:
            problems.append(f"строка {index}: has_generated_text должен быть false в обязательной части")
        text = row.get("text")
        if not isinstance(text, str) or not text.strip():
            problems.append(f"строка {index}: пустой text")
        start, end = row.get("char_start"), row.get("char_end")
        doc_id = row.get("doc_id")
        if (
            isinstance(start, int)
            and isinstance(end, int)
            and isinstance(text, str)
            and isinstance(doc_id, str)
            and doc_id in pages
        ):
            if pages[doc_id][start:end] != text:
                problems.append(f"строка {index}: срез страницы не совпадает с text")
        if isinstance(doc_id, str) and manifest_hashes:
            if doc_id not in manifest_hashes:
                problems.append(f"строка {index}: doc_id нет в manifest снимка")
            elif row.get("doc_content_hash") != manifest_hashes[doc_id]:
                problems.append(f"строка {index}: doc_content_hash не совпал с manifest")
        if len(problems) >= 30:
            problems.append("… слишком много ошибок, остальное пропущено")
            break
    return problems


def _duplicate_groups(rows: list[dict]) -> tuple[float, list[DupGroup]]:
    """dup_ratio и группы с ≥2 разными doc_id."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        text = row.get("text")
        if not isinstance(text, str):
            continue
        key = normalize_text(text).lower()
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        buckets[digest].append(row)

    groups: list[DupGroup] = []
    numerator = 0
    for digest, items in buckets.items():
        doc_ids = sorted({str(item["doc_id"]) for item in items})
        if len(doc_ids) < 2:
            continue
        numerator += len(items) - 1
        urls = []
        for item in items:
            url = item.get("url")
            if isinstance(url, str) and url not in urls:
                urls.append(url)
            if len(urls) >= 3:
                break
        sample = str(items[0].get("text") or "")
        if len(sample) > 160:
            sample = sample[:157] + "..."
        groups.append(
            DupGroup(
                text_hash=digest[:12],
                count=len(items),
                doc_ids=doc_ids,
                sample_urls=urls,
                sample_text=sample.replace("\n", " "),
            )
        )
    groups.sort(key=lambda g: (-len(g.doc_ids), -g.count, g.text_hash))
    n = len(rows)
    ratio = (numerator / n) if n else 0.0
    return ratio, groups


def _percentile(values: list[int], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (pct / 100) * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    weight = rank - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def _histogram(tokens: list[int], bins: int = 8) -> list[tuple[str, int]]:
    if not tokens:
        return []
    lo, hi = min(tokens), max(tokens)
    if lo == hi:
        return [(f"{lo}", len(tokens))]
    width = max(1, math.ceil((hi - lo + 1) / bins))
    edges = list(range(lo, hi + 1, width))
    if edges[-1] <= hi:
        edges.append(hi + 1)
    counts = [0] * (len(edges) - 1)
    for value in tokens:
        for i in range(len(edges) - 1):
            if edges[i] <= value < edges[i + 1]:
                counts[i] += 1
                break
        else:
            counts[-1] += 1
    return [(f"{edges[i]}–{edges[i + 1] - 1}", counts[i]) for i in range(len(counts))]


def _render_report(stats: QualityStats) -> str:
    hist_lines = []
    if stats.histogram:
        peak = max(count for _, count in stats.histogram) or 1
        for label, count in stats.histogram:
            bar = "█" * max(1, round(20 * count / peak)) if count else ""
            hist_lines.append(f"- `{label}`: {count} {bar}")
    else:
        hist_lines = ["- (нет данных)"]

    group_lines = []
    for i, group in enumerate(stats.top_groups, start=1):
        group_lines.append(
            f"{i}. docs={len(group.doc_ids)}, chunks={group.count}, "
            f"hash={group.text_hash}, urls={', '.join(group.sample_urls) or '—'}; "
            f"пример: {group.sample_text!r}"
        )
    if not group_lines:
        group_lines = ["(групп с повторами между документами нет)"]

    times = (
        "\n".join(f"- {name}: {seconds:.1f} с" for name, seconds in stats.step_times_s.items())
        if stats.step_times_s
        else "- не замерялось в этом прогоне"
    )
    gate = "ок" if stats.gate_ok else "есть замечания"
    bug = (
        "да — нужен баг-репорт PRS (dup_ratio ≥ 2 % на не-mdd)"
        if stats.needs_prs_bug
        else "нет (на mdd ненулевой dup_ratio ожидаем и только фиксируем)"
    )
    dropped = "—" if stats.dropped_short is None else str(stats.dropped_short)
    merged = "—" if stats.merged_headings is None else str(stats.merged_headings)

    problems = (
        "\n".join(f"- {item}" for item in stats.gate_problems)
        if stats.gate_problems
        else "- нет"
    )

    return f"""# Отчёт о качестве

## Снимок и коллекция

- snapshot_id: `{stats.snapshot_id}`
- collection: `{stats.collection}`
- документов в manifest / уникальных doc_id: {stats.manifest_documents}
- статусы документов: {stats.status_counts}

## Чанки и токены

- чанков всего: {stats.chunks_total}
- токены text: min={stats.token_min}, медиана={_fmt(stats.token_median)}, p95={_fmt(stats.token_p95)}, max={stats.token_max}
- отброшено коротких: {dropped}
- слито заголовков: {merged}

### Гистограмма длины чанков (токены)

{chr(10).join(hist_lines)}

## Повторы между документами

- dup_ratio: {stats.dup_ratio:.6f} (= Σ(|g|−1) / N)
- нужен баг-репорт PRS: {bug}

### Топ-20 групп одинаковых чанков

{chr(10).join(group_lines)}

## Языки и типы (по документам)

- lang: {stats.lang_counts}
- content_type: {stats.content_type_counts}

## Время шагов

{times}

## Версии

- schema_version: `{stats.versions.get("schema_version", "")}`
- chunker: `{stats.versions.get("chunker", "")}`
- embedding_model: `{stats.versions.get("embedding_model", "")}`

## Ворота K2 (локально по chunks.jsonl)

- результат: **{gate}**
{problems}
"""


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}"


def _load_chunks(path: Path) -> list[dict]:
    return _load_jsonl(path)


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows
