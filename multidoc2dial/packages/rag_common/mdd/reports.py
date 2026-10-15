"""Отчёты снимка mdd_v1.

sections.json считает документы по темам. Остальные отчёты K1 нулевые:
архив не обходился как сайт.
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_common.mdd.documents import iter_documents
from rag_common.mdd.ids import k1_doc_id

SECTION_ORDER = ("dmv", "ssa", "va", "studentaid")
SECTION_DESCRIPTIONS = {
    "dmv": "Автотранспорт: права и регистрация",
    "ssa": "Социальное страхование",
    "va": "Дела ветеранов",
    "studentaid": "Помощь студентам с оплатой учёбы",
}


def _dump(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_reports(archive: Path, reports_dir: Path) -> dict[str, int]:
    """Пишет reports/. Архив не распаковывает, тексты снимка не меняет."""
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    counts = {section: 0 for section in SECTION_ORDER}
    page_lines: list[str] = []
    for document in iter_documents(archive):
        if document.domain not in counts:
            raise ValueError(f"неизвестная тема {document.domain}")
        counts[document.domain] += 1
        page_lines.append(
            json.dumps(
                {
                    "doc_id": k1_doc_id(document.domain, document.source_doc_id),
                    "depth": 0,
                    "removed_blocks": 0,
                    "audience": None,
                },
                ensure_ascii=False,
            )
        )

    sections = {
        "sections": [
            {
                "section": section,
                "document_count": counts[section],
                "description": SECTION_DESCRIPTIONS[section],
            }
            for section in SECTION_ORDER
        ]
    }
    (reports_dir / "sections.json").write_bytes(_dump(sections))
    (reports_dir / "crawl_stats.json").write_bytes(
        _dump(
            {
                "found": 0,
                "downloaded": 0,
                "errors": 0,
                "redirects": 0,
                "duplicates": 0,
            }
        )
    )
    (reports_dir / "boilerplate_report.json").write_bytes(_dump({"blocks": []}))
    (reports_dir / "duplicates.json").write_bytes(_dump({"groups": []}))
    page_lines.sort()
    page_payload = "".join(line + "\n" for line in page_lines)
    (reports_dir / "page_stats.jsonl").write_bytes(page_payload.encode("utf-8"))
    return counts
