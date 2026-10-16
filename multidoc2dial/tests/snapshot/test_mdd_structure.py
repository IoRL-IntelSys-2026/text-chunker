"""Файл разделов на каждый документ.

Нарезка режет страницу по этим границам, поэтому они должны лежать внутри текста.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rag_common.datasets.mdd.documents import iter_documents
from rag_common.datasets.mdd.ids import k1_doc_id
from rag_common.datasets.mdd.structure import write_structure

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "data" / "cache" / "multidoc2dial.zip"


def test_structure_bounds_lie_inside_doc_text(tmp_path: Path) -> None:
    """У каждого из 488 документов есть разделы, и ни одна граница не вылезает за конец текста."""
    structure = tmp_path / "structure"
    assert write_structure(ARCHIVE, structure) == 488
    files = list(structure.glob("*.json"))
    assert len(files) == 488

    seen = 0
    for document in iter_documents(ARCHIVE):
        doc_id = k1_doc_id(document.domain, document.source_doc_id)
        sections = json.loads((structure / f"{doc_id}.json").read_text(encoding="utf-8"))
        assert sections
        for section in sections:
            assert list(section) == ["title_path", "char_start", "char_end"]
            start = section["char_start"]
            end = section["char_end"]
            assert 0 <= start <= end <= len(document.doc_text)
            assert all(isinstance(part, str) for part in section["title_path"])
        seen += 1
    assert seen == 488

    first = {path.name: hashlib.sha256(path.read_bytes()).digest() for path in files}
    assert write_structure(ARCHIVE, structure) == 488
    second = {
        path.name: hashlib.sha256(path.read_bytes()).digest() for path in structure.glob("*.json")
    }
    assert first == second
