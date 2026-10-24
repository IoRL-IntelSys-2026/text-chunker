# -*- coding: utf-8 -*-
"""QA: compare each PDF in docling.jsonl with docs/docling_md/*.md."""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "docs" / "docling_pdf"
MD_DIR = ROOT / "docs" / "docling_md"
MANIFEST = ROOT / "docling" / "docling.jsonl"
OUT = ROOT / "docling" / "md_pdf_qa_report.txt"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def find_file(folder: Path, name: str) -> Path | None:
    p = folder / name
    if p.is_file():
        return p
    want = nfc(name)
    for f in folder.iterdir():
        if f.is_file() and nfc(f.name) == want:
            return f
    stem = nfc(Path(name).stem)
    for f in folder.iterdir():
        if f.is_file() and nfc(f.stem) == stem:
            return f
    return None


def normalize(s: str) -> str:
    s = s.lower().replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\sа-яa-z0-9%№]", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str, min_len: int = 4) -> list[str]:
    return [t for t in normalize(s).split() if len(t) >= min_len]


def body_from_pdf_text(t: str) -> str:
    for junk in [
        "Документ подписан простой электронной подписью",
        "Информация о владельце:",
        "Уникальный программный ключ:",
        "Действительный документ",
        "Документ хранится в программе",
        "Электронная копия документа",
        "ФИО:",
        "Должность:",
        "Дата подписания:",
    ]:
        t = t.replace(junk, "")
    lines = []
    for ln in t.splitlines():
        s = ln.strip()
        if not s:
            continue
        if len(s) >= 32 and all(c in "0123456789abcdef" for c in s.lower()):
            continue
        if "e1cib/" in s or "ref=" in s:
            continue
        lines.append(s)
    return "\n".join(lines)


def extract_nums(s: str) -> set[str]:
    found = re.findall(r"\d[\d\s]{2,}\d", s.replace("\xa0", " "))
    return {re.sub(r"\s+", "", x) for x in found if len(re.sub(r"\s+", "", x)) >= 4}


def analyze_md(md: str) -> list[str]:
    flags: list[str] = []
    if len(md.strip()) < 80:
        flags.append("VERY_SHORT_MD")
    img = md.count("<!-- image -->")
    if img >= 3:
        flags.append(f"MANY_IMAGE_PH={img}")
    elif img >= 1:
        flags.append(f"IMAGE_PH={img}")
    if "<!-- formula-not-decoded -->" in md:
        flags.append("FORMULA_NOT_DECODED")
    if re.search(r'^""\s*$', md, re.M):
        flags.append("EMPTY_QUOTE_TITLE")
    if re.search(
        r"(Ректор|И\.о\.\s*Ректора).{0,120}\+?\d{1,3}[\s(.-]*\d{3}",
        md,
        re.S | re.I,
    ):
        flags.append("SIGNATURE_PHONE_NEAR_RECTOR")
    units = re.findall(
        r"^\|[^|\n]*\|\s*((?:Факультет|Институт|Академия|Высшая школа)[^|\n]*)\|",
        md,
        re.M,
    )
    if units and not any(u.strip().startswith("**") for u in units):
        flags.append(f"FLAT_UNIT_HEADERS={len(units)}")
    if "электронной подписью" in md.lower() or "Уникальный программный ключ" in md:
        flags.append("EDS_STAMP_IN_TEXT")
    efc = len(re.findall(r"^\|  \|", md, re.M))
    if efc >= 8:
        flags.append(f"FLAT_LIST_TABLE_ROWS={efc}")
    # broken words like "АЛЬФА- БАНК" / "стиненний" style — hard; skip
    if "ФРАЦЕВИЧА" in md.upper():
        flags.append("KNOWN_TYPO_FRACEVICHA")
    return flags


def severity_of(flags: list[str]) -> str:
    critical_exact = {
        "VERY_SHORT_MD",
        "SCAN_BUT_WEAK_MD",
        "LOW_TOKEN_COVERAGE",
        "MD_MUCH_SHORTER",
        "FORMULA_NOT_DECODED",
    }
    warn_pref = (
        "SIGNATURE_PHONE_NEAR_RECTOR",
        "FLAT_UNIT_HEADERS",
        "EDS_STAMP_IN_TEXT",
        "EMPTY_QUOTE_TITLE",
        "MANY_IMAGE_PH",
        "MISSING_FOOTNOTE_HINT",
        "MISSING_SIGNER_NAME",
    )
    if any(f in critical_exact or f.startswith("LOW_") for f in flags):
        return "critical"
    if any(f.startswith(p) or f == p for f in flags for p in warn_pref):
        return "warn"
    if flags:
        return "note"
    return "ok"


def spot_checks(doc_id: str, pdf_body: str, md: str) -> list[str]:
    flags: list[str] = []
    # 1843 footnote
    if doc_id == "7":
        if "браке" in pdf_body.lower() and "браке" not in md.lower():
            flags.append("MISSING_FOOTNOTE_HINT")
        if "неполной семьей" in pdf_body.lower() and "неполной" not in md.lower():
            flags.append("MISSING_FOOTNOTE_HINT")
    # 595 Kutepov
    if doc_id == "10":
        if "Кутепов" in pdf_body and "Кутепов" not in md:
            flags.append("MISSING_SIGNER_NAME")
    # 1356 point 2 truncation present in both
    if doc_id == "1":
        if re.search(r"2\.\s*6 года", md) or re.search(r"2\.\s*6 года", pdf_body):
            flags.append("TRUNCATED_POINT2_IN_SOURCE_OR_MD")
    # 352
    if doc_id == "8" and "formula-not-decoded" in md:
        flags.append("FORMULA_NOT_DECODED")
    return flags


def main() -> None:
    rows = [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report: list[str] = [
        "QA: PDF vs MD (full corpus from docling/docling.jsonl)",
        f"pdf_dir={PDF_DIR}",
        f"md_dir={MD_DIR}",
        "",
    ]
    summary: list[tuple[str, str, list[str], str]] = []

    for row in rows:
        doc_id = row["doc_id"]
        src = row.get("source", "?")
        pdf = find_file(PDF_DIR, row["document_old"])
        md_path = find_file(MD_DIR, row["document_new"])
        if not pdf or not md_path:
            summary.append((doc_id, "critical", ["MISSING_FILE"], row["document_new"]))
            report.append(f"## doc_id={doc_id} CRITICAL MISSING pdf={bool(pdf)} md={bool(md_path)}")
            report.append("")
            continue

        doc = pymupdf.open(pdf)
        pdf_pages = [(p.get_text("text") or "") for p in doc]
        n_pages = doc.page_count
        n_imgs = sum(len(p.get_images(full=True)) for p in doc)
        doc.close()

        pdf_raw = "\n".join(pdf_pages)
        pdf_body = body_from_pdf_text(pdf_raw)
        md = md_path.read_text(encoding="utf-8")
        table_rows = len(re.findall(r"^\| .+\|$", md, re.M))

        flags = analyze_md(md)
        flags.extend(spot_checks(doc_id, pdf_body, md))

        pdf_toks = set(tokens(pdf_body))
        md_toks = set(tokens(md))
        is_scan = len(pdf_body.strip()) < 300
        cov_f = None
        num_cov = None
        miss = []

        if is_scan:
            flags.append("SCAN_SOURCE_MANUAL_OR_OCR")
            if len(md.strip()) < 200:
                flags.append("SCAN_BUT_WEAK_MD")
        else:
            cov_f = (len(pdf_toks & md_toks) / len(pdf_toks)) if pdf_toks else 0.0
            if cov_f < 0.55:
                flags.append("LOW_TOKEN_COVERAGE")
            ratio = len(md.strip()) / max(1, len(pdf_body.strip()))
            if ratio < 0.35:
                flags.append("MD_MUCH_SHORTER")
            if ratio > 1.55:
                flags.append("MD_MUCH_LONGER")
            miss = sorted(pdf_toks - md_toks)
            miss = [t for t in miss if len(t) >= 8][:10]
            pn, mn = extract_nums(pdf_body), extract_nums(md)
            if pn:
                num_cov = len(pn & mn) / len(pn)

        # dedupe flags keeping order
        seen = set()
        uniq = []
        for f in flags:
            if f not in seen:
                seen.add(f)
                uniq.append(f)
        flags = uniq
        sev = severity_of(flags)
        summary.append((doc_id, sev, flags, md_path.name))

        cov_s = "n/a(scan)" if is_scan else f"{cov_f:.2f}"
        num_s = "n/a" if num_cov is None else f"{num_cov:.2f}"
        report.append(f"## doc_id={doc_id} [{src}] {sev.upper()} — {md_path.name}")
        report.append(
            f"  pages={n_pages} pdf_body={len(pdf_body.strip())} md_chars={len(md.strip())} "
            f"imgs={n_imgs} tables~{table_rows} token_cov={cov_s} num_cov={num_s}"
        )
        report.append(f"  flags: {', '.join(flags) if flags else '-'}")
        if miss:
            report.append(f"  missing_pdf_tokens: {', '.join(miss)}")
        if "SIGNATURE_PHONE_NEAR_RECTOR" in flags or "MISSING_SIGNER_NAME" in flags:
            body_lines = [
                ln for ln in md.splitlines() if ln.strip() and not ln.startswith("|")
            ]
            report.append("  signature_tail:")
            for ln in body_lines[-8:]:
                report.append(f"    | {ln[:140]}")
        report.append("")

    # summary tables
    report.append("=== SUMMARY BY SEVERITY ===")
    c = Counter(s for _, s, _, _ in summary)
    report.append(str(dict(c)))
    report.append("")
    report.append("=== CRITICAL / WARN ===")
    for doc_id, sev, flags, name in summary:
        if sev in ("critical", "warn"):
            report.append(f"  [{sev}] doc_id={doc_id} {name}")
            report.append(f"         {', '.join(flags)}")

    report.append("")
    report.append("=== ERROR CLASSES (corpus-wide) ===")
    report.append(
        "- EDS/штампы в тексте шапки; пустой \"\" вместо номера; телефон у блока Ректор\n"
        "- таблицы рвутся / плоские приложения без иерархии факультетов\n"
        "- сканы: md есть (ручной/OCR), сверка token_cov с PDF невозможна\n"
        "- точечные пропуски (сноски, ФИО подписанта, formula-not-decoded)"
    )

    OUT.write_text("\n".join(report), encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
