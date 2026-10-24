"""Convert stipendii PDF set with Docling + table repair. Run from repo root:

    python docling/convert_stipendii.py
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Local package dir would shadow installed docling — drop repo root.
sys.path = [p for p in sys.path if p and Path(p).resolve() != ROOT]
# Keep this folder importable for table_repair
sys.path.insert(0, str(Path(__file__).resolve().parent))

from docling.datamodel.base_models import InputFormat  # noqa: E402
from docling.datamodel.pipeline_options import (  # noqa: E402
    PdfPipelineOptions,
    TableFormerMode,
    TableStructureOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption  # noqa: E402

from table_repair import repair_markdown_tables  # noqa: E402

PDF_DIR = ROOT / "docs" / "docling_pdf_10"
MD_DIR = ROOT / "docs" / "docling_md_10"
MANIFEST = ROOT / "docling" / "docling.jsonl"
REPORT = ROOT / "docling" / "docling_run_report.txt"


def load_manifest() -> list[dict]:
    rows = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def build_converter() -> DocumentConverter:
    # Baseline: no OCR / no VLM. Accurate TableFormer + cell matching.
    # (do_cell_matching=False drops many body rows on RUDN multi-page tables.)
    pipeline_options = PdfPipelineOptions(
        do_ocr=False,
        do_table_structure=True,
        table_structure_options=TableStructureOptions(
            do_cell_matching=True,
            mode=TableFormerMode.ACCURATE,
        ),
    )
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )


def pdf_to_markdown(converter: DocumentConverter, pdf_path: Path) -> str:
    conv = converter.convert(str(pdf_path))
    raw = conv.document.export_to_markdown(
        compact_tables=True,
        image_placeholder="<!-- image -->",
    )
    return repair_markdown_tables(raw)


def main(only: str | None = None) -> int:
    MD_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_manifest()
    converter = build_converter()
    try:
        import importlib.metadata as md

        docling_ver = md.version("docling")
    except Exception:
        docling_ver = "unknown"

    results: list[str] = []
    ok = notes = errors = 0
    print(
        f"docling={docling_ver} do_ocr=False table_mode=accurate "
        f"do_cell_matching=True + table_repair -> {MD_DIR}",
        flush=True,
    )

    for row in rows:
        if only and only not in row["document_old"] and only not in row["doc_id"]:
            continue
        pdf_path = PDF_DIR / row["document_old"]
        md_path = MD_DIR / row["document_new"]
        doc_id = row["doc_id"]
        print(f"[{doc_id}/10] {pdf_path.name} ...", flush=True)
        if not pdf_path.is_file():
            errors += 1
            results.append(f"ERROR doc_id={doc_id}: missing PDF {pdf_path.name}")
            continue
        try:
            text = pdf_to_markdown(converter, pdf_path)
            md_path.write_text(text, encoding="utf-8")
            nchars = len(text.strip())
            n_tbl = text.count("\n| ")
            if nchars < 50:
                notes += 1
                results.append(
                    f"NOTE doc_id={doc_id} {md_path.name}: very short ({nchars} chars)"
                )
                print(f"  NOTE short ({nchars} chars)", flush=True)
            else:
                ok += 1
                results.append(
                    f"OK doc_id={doc_id} {md_path.name}: {nchars} chars, "
                    f"pipe-ish lines~{n_tbl}"
                )
                print(f"  OK {nchars} chars", flush=True)
        except Exception as exc:
            errors += 1
            results.append(
                f"ERROR doc_id={doc_id} {pdf_path.name}: {type(exc).__name__}: {exc}"
            )
            results.append(traceback.format_exc())
            print(f"  ERROR {type(exc).__name__}: {exc}", flush=True)

    report = [
        "Docling run report — stipendii_10",
        f"utc: {datetime.now(timezone.utc).isoformat()}",
        f"docling_version: {docling_ver}",
        "pipeline: PdfPipelineOptions(do_ocr=False, do_table_structure=True, "
        "table_structure_options=TableStructureOptions(do_cell_matching=True, "
        "mode=ACCURATE)); no VLM",
        "postprocess: docling/table_repair.py — merge page-split markdown tables, "
        "fold spilled cell glue, coalesce continuation rows, keep separate Группа N tables",
        f"input: {PDF_DIR}",
        f"output: {MD_DIR}",
        f"manifest: {MANIFEST}",
        f"summary: ok={ok} notes={notes} errors={errors} total={len(rows) if not only else 'filtered'}",
        "",
        *results,
        "",
    ]
    REPORT.write_text("\n".join(report), encoding="utf-8")
    print("report:", REPORT)
    print(f"summary ok={ok} notes={notes} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    raise SystemExit(main(only=arg))
