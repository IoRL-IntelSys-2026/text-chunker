"""Приёмочная статистика K1 (PRE-24)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from preprocessing.acceptance import snapshot_stats, write_acceptance_report

ROOT = Path(__file__).resolve().parents[2]
MDD = ROOT / "data" / "snapshots" / "mdd_v1"
CONFIG = ROOT / "configs" / "chunking" / "mdd_sections_512.yaml"


def _write_mini_snapshot(folder: Path) -> None:
    pages = folder / "pages"
    pages.mkdir(parents=True)
    reports = folder / "reports"
    reports.mkdir(parents=True)
    (reports / "sections.json").write_text(
        json.dumps(
            {
                "sections": [
                    {"section": "dmv", "document_count": 1, "description": "dmv"},
                    {"section": "ssa", "document_count": 1, "description": "ssa"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    rows = []
    for doc_id, section, text in (
        ("aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa", "dmv", "hello"),
        ("bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb", "ssa", "world!"),
        ("cccccccc-cccc-5ccc-8ccc-cccccccccccc", "other", "x"),
    ):
        path = f"pages/{doc_id}.txt"
        (folder / path).write_text(text, encoding="utf-8")
        row = {
            "schema_version": "k1.v1",
            "doc_id": doc_id,
            "source": "test",
            "url": f"mdd://{section}/{doc_id}",
            "aliases": [],
            "title": section,
            "lang": "en",
            "content_type": "text/plain",
            "path": path,
            "content_hash": "x",
            "section": section,
            "fetched_at": "2026-09-30T00:00:00Z",
            "last_modified": None,
        }
        if section == "ssa":
            row["outlinks"] = ["https://example.com"]
        rows.append(row)
    (folder / "manifest.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    (folder / "snapshot_info.json").write_text("{}", encoding="utf-8")


def test_snapshot_stats_mini(tmp_path: Path) -> None:
    snap = tmp_path / "mini"
    snap.mkdir()
    _write_mini_snapshot(snap)
    stats = snapshot_stats(snap, limits={"max_html_bytes": 10, "max_file_bytes": 10})
    assert stats["n_docs"] == 3
    assert stats["by_content_type"] == {"text/plain": 3}
    assert stats["by_lang"] == {"en": 3}
    assert stats["by_section"]["dmv"] == 1
    assert stats["by_section"]["ssa"] == 1
    assert stats["by_section"]["other"] == 1
    assert stats["unknown_sections"] == ["other"]
    assert stats["no_outlinks_share"] == pytest.approx(2 / 3)
    # "world!" и пути — размеры маленькие; при лимите 10 байт часть может попасть в too_large
    assert "min" in stats["size_bytes"]
    report = tmp_path / "acceptance.md"
    write_acceptance_report(snap, report, limits={"max_file_bytes": 1_000_000})
    assert report.is_file()
    assert "Приёмка снимка" in report.read_text(encoding="utf-8")


@pytest.mark.skipif(not MDD.is_dir(), reason="нет локального снимка mdd_v1")
def test_snapshot_stats_mdd_v1() -> None:
    stats = snapshot_stats(MDD, config_path=CONFIG)
    assert stats["n_docs"] == 488
    assert stats["by_content_type"] == {"text/plain": 488}
    assert stats["by_lang"] == {"en": 488}
    assert stats["by_section"] == {
        "dmv": 149,
        "ssa": 109,
        "va": 138,
        "studentaid": 92,
    }
    assert stats["unknown_sections"] == []
    assert stats["too_large"] == []
    assert stats["no_outlinks_share"] == pytest.approx(1.0)
    assert stats["validation_errors"] == []
