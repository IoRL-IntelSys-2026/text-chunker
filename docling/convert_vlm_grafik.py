# -*- coding: utf-8 -*-
"""Docling VlmPipeline on Grafik_vyplaty_stipendii.pdf -> docs/docling_md/."""
from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path = [p for p in sys.path if p and Path(p).resolve() != ROOT]

from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions  # noqa: E402
from docling.datamodel.base_models import InputFormat  # noqa: E402
from docling.datamodel.pipeline_options import (  # noqa: E402
    VlmConvertOptions,
    VlmPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption  # noqa: E402
from docling.pipeline.vlm_pipeline import VlmPipeline  # noqa: E402

PDF_PATH = ROOT / "docs" / "docling_pdf" / "Grafik_vyplaty_stipendii.pdf"
MD_DIR = ROOT / "docs" / "docling_md"
MD_PATH = MD_DIR / "Grafik_vyplaty_stipendii.md"


def main() -> int:
    if not PDF_PATH.is_file():
        print(f"ERROR: missing {PDF_PATH}", flush=True)
        return 1

    MD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"utc={datetime.now(timezone.utc).isoformat()}", flush=True)
    print(f"input={PDF_PATH}", flush=True)
    print(f"output={MD_PATH}", flush=True)

    vlm_options = VlmConvertOptions.from_preset("granite_docling")
    pipeline_options = VlmPipelineOptions(
        vlm_options=vlm_options,
        generate_page_images=True,
        images_scale=2.0,
        accelerator_options=AcceleratorOptions(
            device=AcceleratorDevice.CUDA,
            num_threads=4,
        ),
    )
    print(
        f"preset=granite_docling device=CUDA images_scale={pipeline_options.images_scale}",
        flush=True,
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=VlmPipeline,
                pipeline_options=pipeline_options,
            ),
        }
    )

    try:
        conv = converter.convert(str(PDF_PATH))
        text = conv.document.export_to_markdown(
            compact_tables=True,
            image_placeholder="<!-- image -->",
        )
        MD_PATH.write_text(text, encoding="utf-8")
        print(f"OK chars={len(text.strip())} -> {MD_PATH.name}", flush=True)
        print("--- preview ---", flush=True)
        print(text[:1500], flush=True)
        return 0
    except Exception:
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
