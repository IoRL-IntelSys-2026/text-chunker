"""Отчёт о качестве и формула dup_ratio."""

from __future__ import annotations

import json
from pathlib import Path

from preprocessing.quality import check_k2_chunks, write_quality_report


def _row(**overrides):
    base = {
        "schema_version": "k2.v1",
        "chunk_id": "11111111-1111-5111-8111-111111111111",
        "doc_id": "aaaaaaaa-aaaa-5aaa-8aaa-aaaaaaaaaaaa",
        "source": "multidoc2dial",
        "source_doc_id": "doc-a",
        "url": "mdd://dmv/a",
        "content_type": "text/plain",
        "title": "A",
        "breadcrumbs": [],
        "section": "dmv",
        "lang": "en",
        "headings": ["H"],
        "chunk_index": 0,
        "n_chunks": 1,
        "text": "Contacts block",
        "char_start": 0,
        "char_end": 14,
        "embed_text": "A\n\nContacts block",
        "token_count": 2,
        "has_generated_text": False,
        "content_hash": "x",
        "doc_content_hash": "y",
        "snapshot_id": "mdd_v1",
        "last_modified": None,
        "fetched_at": "2026-09-30T00:00:00Z",
        "md_path": "pages/a.txt",
        "chunker": "mdd-sections+recursive/v1/512/64",
        "embedding_model": "BAAI/bge-m3",
    }
    base.update(overrides)
    return base


def test_dup_ratio_counts_cross_document_copies(tmp_path: Path) -> None:
    rows = []
    for i in range(10):
        doc_id = f"{i:08x}-aaaa-5aaa-8aaa-aaaaaaaaaaaa"
        rows.append(
            _row(
                chunk_id=f"{i:08x}-bbbb-5bbb-8bbb-bbbbbbbbbbbb",
                doc_id=doc_id,
                url=f"mdd://dmv/{i}",
                text="Contacts block",
                char_end=14,
            )
        )
    # уникальный чанк в том же наборе
    rows.append(
        _row(
            chunk_id="ffffffff-bbbb-5bbb-8bbb-bbbbbbbbbbbb",
            doc_id="ffffffff-aaaa-5aaa-8aaa-aaaaaaaaaaaa",
            url="mdd://dmv/unique",
            text="Unique paragraph here",
            token_count=3,
        )
    )
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    report_path = tmp_path / "quality_report.md"
    stats = write_quality_report(
        chunks_path=chunks_path,
        report_path=report_path,
        collection="mdd_chunks_v1",
        run_gate=False,
    )
    # группа из 10 одинаковых: Σ(|g|-1) = 9, N = 11
    assert abs(stats.dup_ratio - (9 / 11)) < 1e-9
    assert stats.top_groups
    assert len(stats.top_groups[0].doc_ids) == 10
    assert not stats.needs_prs_bug
    text = report_path.read_text(encoding="utf-8")
    assert "dup_ratio" in text
    assert "Топ-20" in text


def test_k2_gate_rejects_generated_flag() -> None:
    rows = [_row(has_generated_text=True)]
    problems = check_k2_chunks(rows, collection="mdd_chunks_v1")
    assert any("has_generated_text" in item for item in problems)


def test_k2_gate_rejects_bad_collection_name() -> None:
    problems = check_k2_chunks([_row()], collection="bad-name")
    assert any("правилу K2" in item for item in problems)
