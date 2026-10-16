"""Приёмочная статистика снимка K1 (C-PRE-03 / TSK-PRE-24).

validate смотрит формат; здесь — цифры для лида и PRS: типы, языки,
разделы, размеры, outlinks.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import median

import yaml

from rag_common.datasets.mdd.validate import validate_snapshot

DEFAULT_LIMITS = {
    "max_html_bytes": 2_000_000,
    "max_file_bytes": 20_000_000,
    "max_pages": 100,
}


def snapshot_stats(
    snapshot_dir: Path,
    *,
    limits: dict | None = None,
    config_path: Path | None = None,
) -> dict:
    """Считает приёмочную статистику по manifest.jsonl.

    Возвращает словарь как в TEAM_TASKS_SIMPLE (PRE-20 / TSK-PRE-24),
    плюс size_bytes и validation_errors.
    """
    snapshot_dir = Path(snapshot_dir)
    manifest_path = snapshot_dir / "manifest.jsonl"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    limits = _limits(limits, config_path)
    rows = [
        json.loads(line)
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    known_sections = _known_sections(snapshot_dir)
    by_content_type: Counter[str] = Counter()
    by_lang: Counter[str] = Counter()
    by_section: Counter[str] = Counter()
    unknown_sections: list[str] = []
    sizes: list[int] = []
    too_large: list[dict] = []
    no_outlinks = 0

    for row in rows:
        content_type = str(row.get("content_type") or "unknown")
        lang = str(row.get("lang") or "unknown")
        section = str(row.get("section") or "unknown")
        by_content_type[content_type] += 1
        by_lang[lang] += 1
        by_section[section] += 1
        if known_sections is not None and section not in known_sections:
            if section not in unknown_sections:
                unknown_sections.append(section)

        path_value = row.get("path")
        size = 0
        if isinstance(path_value, str):
            page = snapshot_dir / path_value
            if page.is_file():
                size = page.stat().st_size
        sizes.append(size)

        limit = _limit_for(content_type, limits)
        if size > limit:
            too_large.append(
                {
                    "doc_id": row.get("doc_id"),
                    "path": path_value,
                    "size_bytes": size,
                    "limit_bytes": limit,
                    "content_type": content_type,
                }
            )

        outlinks = row.get("outlinks")
        if outlinks is None or outlinks == []:
            no_outlinks += 1

    n_docs = len(rows)
    stats = {
        "n_docs": n_docs,
        "by_content_type": dict(sorted(by_content_type.items())),
        "by_lang": dict(sorted(by_lang.items())),
        "by_section": dict(sorted(by_section.items())),
        "unknown_sections": unknown_sections,
        "size_bytes": _size_summary(sizes),
        "too_large": too_large,
        "no_outlinks_share": (no_outlinks / n_docs) if n_docs else 0.0,
        "validation_errors": validate_snapshot(snapshot_dir),
    }
    return stats


def write_acceptance_report(
    snapshot_dir: Path,
    report_path: Path,
    *,
    limits: dict | None = None,
    config_path: Path | None = None,
) -> dict:
    """Пишет acceptance.md и возвращает словарь статистики."""
    stats = snapshot_stats(
        snapshot_dir,
        limits=limits,
        config_path=config_path,
    )
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render(stats, Path(snapshot_dir).name), encoding="utf-8")
    return stats


def _limits(limits: dict | None, config_path: Path | None) -> dict:
    merged = dict(DEFAULT_LIMITS)
    if config_path is not None and Path(config_path).is_file():
        payload = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
        merged.update(payload.get("limits") or {})
    if limits:
        merged.update(limits)
    return merged


def _known_sections(snapshot_dir: Path) -> set[str] | None:
    path = snapshot_dir / "reports" / "sections.json"
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["section"] for item in payload.get("sections", [])}


def _limit_for(content_type: str, limits: dict) -> int:
    if content_type in {"text/html", "application/xhtml+xml"}:
        return int(limits["max_html_bytes"])
    return int(limits["max_file_bytes"])


def _size_summary(sizes: list[int]) -> dict:
    if not sizes:
        return {"min": 0, "median": 0.0, "max": 0}
    return {
        "min": min(sizes),
        "median": float(median(sizes)),
        "max": max(sizes),
    }


def _render(stats: dict, snapshot_id: str) -> str:
    errors = stats.get("validation_errors") or []
    gate = "ок" if not errors else "есть нарушения формата K1"
    too_large = stats.get("too_large") or []
    if too_large:
        large_lines = [
            f"- `{item.get('doc_id')}` ({item.get('path')}): "
            f"{item.get('size_bytes')} байт > лимит {item.get('limit_bytes')}"
            for item in too_large[:50]
        ]
        if len(too_large) > 50:
            large_lines.append(f"- … ещё {len(too_large) - 50}")
    else:
        large_lines = ["- нет"]

    unknown = stats.get("unknown_sections") or []
    unknown_lines = [f"- `{name}`" for name in unknown] if unknown else ["- нет"]
    error_lines = [f"- {item}" for item in errors[:50]] if errors else ["- нет"]
    if len(errors) > 50:
        error_lines.append(f"- … ещё {len(errors) - 50}")

    size = stats.get("size_bytes") or {}
    return f"""# Приёмка снимка K1

- snapshot_id: `{snapshot_id}`
- документов: {stats.get("n_docs")}
- validate K1: **{gate}**

## Типы и языки

- by_content_type: {stats.get("by_content_type")}
- by_lang: {stats.get("by_lang")}

## Разделы

- by_section: {stats.get("by_section")}
- unknown_sections (нет в reports/sections.json):
{chr(10).join(unknown_lines)}

## Размеры файлов (байты по path)

- min: {size.get("min")}
- median: {size.get("median")}
- max: {size.get("max")}
- too_large:
{chr(10).join(large_lines)}

## Ссылки наружу

- no_outlinks_share: {stats.get("no_outlinks_share"):.6f}
  (доля документов без поля outlinks или с пустым списком)

## Нарушения validate K1

{chr(10).join(error_lines)}
"""
