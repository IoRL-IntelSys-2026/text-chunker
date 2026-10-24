# -*- coding: utf-8 -*-
"""Several Docling variants for Grafik_vyplaty_stipendii.pdf -> docs/docling_md/."""
from __future__ import annotations

import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path = [p for p in sys.path if p and Path(p).resolve() != ROOT]

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions  # noqa: E402
from docling.datamodel.base_models import InputFormat  # noqa: E402
from docling.datamodel.pipeline_options import (  # noqa: E402
    OcrMode,
    PdfPipelineOptions,
    RapidOcrOptions,
    TableFormerMode,
    TableStructureOptions,
    VlmConvertOptions,
    VlmPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption  # noqa: E402
from docling.pipeline.vlm_pipeline import VlmPipeline  # noqa: E402

PDF_PATH = ROOT / "docs" / "docling_pdf" / "Grafik_vyplaty_stipendii.pdf"
MD_DIR = ROOT / "docs" / "docling_md"
ACCEL = AcceleratorOptions(device=AcceleratorDevice.CUDA, num_threads=4)


def export_md(conv) -> str:
    return conv.document.export_to_markdown(
        compact_tables=True,
        image_placeholder="<!-- image -->",
    )


def run_vlm(tag: str, preset: str, images_scale: float = 2.0) -> Path:
    out = MD_DIR / f"Grafik_vyplaty_stipendii__{tag}.md"
    print(f"\n=== VLM {tag} preset={preset} scale={images_scale} ===", flush=True)
    t0 = time.perf_counter()
    opts = VlmPipelineOptions(
        vlm_options=VlmConvertOptions.from_preset(preset),
        generate_page_images=True,
        images_scale=images_scale,
        accelerator_options=ACCEL,
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=VlmPipeline,
                pipeline_options=opts,
            ),
        }
    )
    text = export_md(converter.convert(str(PDF_PATH)))
    header = (
        f"<!-- variant: {tag} | pipeline=VlmPipeline | preset={preset} "
        f"| images_scale={images_scale} | device=CUDA -->\n\n"
    )
    out.write_text(header + text, encoding="utf-8")
    dt = time.perf_counter() - t0
    print(f"OK {out.name}: chars={len(text.strip())} time={dt:.1f}s", flush=True)
    print(text[:500], flush=True)
    return out


def run_ocr_rapid(tag: str, scale: float = 3.0) -> Path:
    out = MD_DIR / f"Grafik_vyplaty_stipendii__{tag}.md"
    print(f"\n=== OCR {tag} RapidOCR cyrillic scale={scale} ===", flush=True)
    t0 = time.perf_counter()
    opts = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        force_full_page_ocr=True,
        ocr_options=RapidOcrOptions(
            lang=["cyrillic"],
            scale=scale,
            mode=OcrMode.FULL_PAGE,
            force_full_page_ocr=True,
        ),
        table_structure_options=TableStructureOptions(
            do_cell_matching=True,
            mode=TableFormerMode.ACCURATE,
        ),
        accelerator_options=ACCEL,
        generate_page_images=True,
        images_scale=2.0,
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=opts),
        }
    )
    text = export_md(converter.convert(str(PDF_PATH)))
    header = (
        f"<!-- variant: {tag} | pipeline=PdfPipeline | ocr=RapidOCR "
        f"lang=cyrillic scale={scale} full_page | device=CUDA -->\n\n"
    )
    out.write_text(header + text, encoding="utf-8")
    dt = time.perf_counter() - t0
    print(f"OK {out.name}: chars={len(text.strip())} time={dt:.1f}s", flush=True)
    print(text[:500], flush=True)
    return out


def run_vlm_chart(tag: str) -> Path:
    """VLM + chart extraction enrichment."""
    out = MD_DIR / f"Grafik_vyplaty_stipendii__{tag}.md"
    print(f"\n=== VLM+chart {tag} ===", flush=True)
    t0 = time.perf_counter()
    opts = VlmPipelineOptions(
        vlm_options=VlmConvertOptions.from_preset("granite_vision"),
        generate_page_images=True,
        generate_picture_images=True,
        images_scale=2.0,
        do_chart_extraction=True,
        accelerator_options=ACCEL,
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=VlmPipeline,
                pipeline_options=opts,
            ),
        }
    )
    text = export_md(converter.convert(str(PDF_PATH)))
    header = (
        f"<!-- variant: {tag} | pipeline=VlmPipeline | preset=granite_vision "
        f"| do_chart_extraction=True | device=CUDA -->\n\n"
    )
    out.write_text(header + text, encoding="utf-8")
    dt = time.perf_counter() - t0
    print(f"OK {out.name}: chars={len(text.strip())} time={dt:.1f}s", flush=True)
    print(text[:500], flush=True)
    return out


def main() -> int:
    if not PDF_PATH.is_file():
        print(f"ERROR missing {PDF_PATH}", flush=True)
        return 1
    MD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"utc={datetime.now(timezone.utc).isoformat()}", flush=True)

    # keep previous run as named baseline
    old = MD_DIR / "Grafik_vyplaty_stipendii.md"
    baseline = MD_DIR / "Grafik_vyplaty_stipendii__vlm_granite_docling_s2.md"
    if old.is_file() and not baseline.is_file():
        text = old.read_text(encoding="utf-8")
        if not text.startswith("<!-- variant:"):
            text = (
                "<!-- variant: vlm_granite_docling_s2 | pipeline=VlmPipeline | "
                "preset=granite_docling | images_scale=2.0 | device=CUDA | prior_run -->\n\n"
                + text
            )
        baseline.write_text(text, encoding="utf-8")
        print(f"kept baseline -> {baseline.name}", flush=True)

    results: list[tuple[str, str]] = []
    jobs = [
        ("vlm_granite_docling_s3", lambda: run_vlm("vlm_granite_docling_s3", "granite_docling", 3.0)),
        ("vlm_granite_vision_s2", lambda: run_vlm("vlm_granite_vision_s2", "granite_vision", 2.0)),
        ("vlm_got_ocr_s2", lambda: run_vlm("vlm_got_ocr_s2", "got_ocr", 2.0)),
        ("vlm_granite_vision_chart", lambda: run_vlm_chart("vlm_granite_vision_chart")),
        ("ocr_rapid_cyr_s3", lambda: run_ocr_rapid("ocr_rapid_cyr_s3", 3.0)),
        ("ocr_rapid_cyr_s4", lambda: run_ocr_rapid("ocr_rapid_cyr_s4", 4.0)),
    ]

    for name, fn in jobs:
        try:
            path = fn()
            results.append((name, f"OK {path.stat().st_size} bytes"))
        except Exception as exc:
            traceback.print_exc()
            results.append((name, f"FAIL {exc}"))
            err = MD_DIR / f"Grafik_vyplaty_stipendii__{name}.ERROR.txt"
            err.write_text(traceback.format_exc(), encoding="utf-8")

    print("\n=== SUMMARY ===", flush=True)
    for name, status in results:
        print(f"  {name}: {status}", flush=True)
    for p in sorted(MD_DIR.glob("Grafik_vyplaty_stipendii__*.md")):
        n = len(p.read_text(encoding="utf-8").strip())
        print(f"  file {p.name}: {n} chars", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
