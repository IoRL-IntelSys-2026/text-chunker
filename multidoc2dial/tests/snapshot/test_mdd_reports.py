"""Отчёты снимка: сколько документов в каждой теме.

Нули в статистике обхода показывают, что страницы взяты из архива, а не скачаны с сайта.
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_common.datasets.mdd.reports import write_reports

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "cache" / "multidoc2dial.zip"
PAGE = ROOT / "data" / "snapshots" / "mdd_v1" / "pages" / "0a6f1ad6-6a7d-5462-abe5-516ceca3c4bb.txt"


def test_reports_list_four_domains_and_zero_crawl(tmp_path: Path) -> None:
    """Четыре темы дают 149, 109, 138 и 92 документа. Скачиваний, ошибок и дублей в отчёте обхода нет."""
    before = PAGE.read_bytes()
    reports = tmp_path / "reports"
    counts = write_reports(ARCHIVE, reports)
    assert counts == {"dmv": 149, "ssa": 109, "va": 138, "studentaid": 92}

    sections = json.loads((reports / "sections.json").read_text(encoding="utf-8"))["sections"]
    assert [item["document_count"] for item in sections] == [149, 109, 138, 92]
    assert [item["section"] for item in sections] == ["dmv", "ssa", "va", "studentaid"]

    crawl = json.loads((reports / "crawl_stats.json").read_text(encoding="utf-8"))
    assert crawl == {
        "found": 0,
        "downloaded": 0,
        "errors": 0,
        "redirects": 0,
        "duplicates": 0,
    }
    assert json.loads((reports / "boilerplate_report.json").read_text(encoding="utf-8")) == {
        "blocks": []
    }
    assert json.loads((reports / "duplicates.json").read_text(encoding="utf-8")) == {"groups": []}

    page_stats = (reports / "page_stats.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(page_stats) == 488
    assert all(json.loads(line)["removed_blocks"] == 0 for line in page_stats)
    assert PAGE.read_bytes() == before

    first = {path.name: path.read_bytes() for path in reports.iterdir()}
    write_reports(ARCHIVE, reports)
    second = {path.name: path.read_bytes() for path in reports.iterdir()}
    assert first == second
