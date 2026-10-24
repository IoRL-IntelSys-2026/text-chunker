# -*- coding: utf-8 -*-
"""One-off deep QA for docs 4–22. Run: python docling/_deep_qa_rest.py"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docling" / "docling.jsonl"
PDF_DIR = ROOT / "docs" / "docling_pdf"
MD_DIR = ROOT / "docs" / "docling_md"
OUT = ROOT / "docling" / "_deep_qa_rest_out.txt"


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


def normalize(s: str) -> str:
    s = s.lower().replace("ё", "е")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\sа-яa-z0-9%№]", " ", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str, min_len: int = 4) -> list[str]:
    return [t for t in normalize(s).split() if len(t) >= min_len]


def extract_nums(s: str) -> set[str]:
    found = re.findall(r"\d[\d\s]{2,}\d", s.replace("\xa0", " "))
    return {re.sub(r"\s+", "", x) for x in found if len(re.sub(r"\s+", "", x)) >= 4}


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BROKEN_MAILTO = re.compile(r"\w+\[[^\]]+@[^]]+\]\(mailto:[^)]+\)")
ESCAPED_EMAIL = re.compile(r"[A-Za-z0-9]+(?:\\_[A-Za-z0-9]+)+@[A-Za-z0-9.-]+")


def main() -> None:
    recs = []
    for line in MANIFEST.open(encoding="utf-8"):
        r = json.loads(line)
        if int(r["doc_id"]) >= 4:
            recs.append(r)

    out: list[str] = []
    for r in sorted(recs, key=lambda x: int(x["doc_id"])):
        did = int(r["doc_id"])
        pdf = find_file(PDF_DIR, r["document_old"])
        md_path = find_file(MD_DIR, r["document_new"])
        notes: list[str] = []
        if not pdf or not md_path:
            out.append(f"#{did} MISSING pdf={pdf} md={md_path}")
            continue
        md = md_path.read_text(encoding="utf-8")
        doc = pymupdf.open(pdf)
        pdf_raw = "\n".join(p.get_text() for p in doc)
        pdf_body = body_from_pdf_text(pdf_raw)
        pages = len(doc)
        pdf_len = len(pdf_body.strip())
        md_len = len(md)
        imgs = md.count("<!-- image -->")
        formula = "<!-- formula-not-decoded -->" in md
        eds = (
            "электронной подписью" in md.lower()
            or "Уникальный программный ключ" in md
            or "Действительный документ" in md
            or "Электронная версия документа" in md
            or "Электронная копия документа" in md
        )
        empty_q = bool(re.search(r'^""\s*$', md, re.M))
        sig_phone = bool(
            re.search(
                r"(Ректор|И\.о\.\s*Ректора).{0,160}\+?\d{1,3}[\s(.-]*\d{3}",
                md,
                re.S | re.I,
            )
        )
        prikaz_misplaced = False
        m_body = re.search(r"ПРИКАЗЫВАЮ", md, re.I)
        if m_body and re.search(
            r"ПРИКАЗЫВАЮ[\s\S]{80,}?^##\s*ПРИКАЗ\s*$", md, re.M | re.I
        ):
            prikaz_misplaced = True
        # mid-body № after ПРИКАЗЫВАЮ
        if m_body and re.search(
            r"ПРИКАЗЫВАЮ[\s\S]{200,}?^№\s*\d+", md, re.M | re.I
        ):
            notes.append("NUMBER_AFTER_BODY")

        pdf_emails = sorted(set(EMAIL_RE.findall(pdf_body)))
        md_unesc = md.replace("\\_", "_")
        md_emails = sorted(set(EMAIL_RE.findall(md_unesc)))
        broken = BROKEN_MAILTO.findall(md)
        esc_em = ESCAPED_EMAIL.findall(md)
        miss_em = [e for e in pdf_emails if e.lower() not in {x.lower() for x in md_emails}]

        if pdf_len < 80:
            cov = None
            miss_tok: list[str] = []
            num_cov = None
            miss_n: list[str] = []
            notes.append("SCAN_OR_EMPTY_PDF_TEXT")
        else:
            pt, mt = set(tokens(pdf_body)), set(tokens(md))
            cov = round(len(pt & mt) / max(1, len(pt)), 3)
            miss_tok = sorted(
                [t for t in (pt - mt) if not re.fullmatch(r"_+", t)],
                key=lambda x: (-len(x), x),
            )[:15]
            pn, mn = extract_nums(pdf_body), extract_nums(md)
            num_cov = round(len(pn & mn) / max(1, len(pn)), 3) if pn else 1.0
            miss_n = sorted(pn - mn, key=lambda x: (-len(x), x))[:10]

        for name in [
            "Кутепов",
            "ФРАЦЕВИЧА",
            "Казакова",
            "Эбзеева",
            "Никитина",
            "Базавлук",
            "Гладуш",
        ]:
            in_pdf = name.lower() in normalize(pdf_raw)
            in_md = name.lower() in md.lower()
            if in_pdf and not in_md:
                notes.append(f"MISSING_NAME_{name}")
            if name == "ФРАЦЕВИЧА" and ("ФРАЦЕВИЧА" in md.upper() or "фрацевича" in md.lower()):
                notes.append("TYPO_FRACEVICHA_IN_MD")

        for g in ["форсмажор", "Вузовучаст", "Вузпартн", "сканкопи", "научнотехнич"]:
            if g.lower() in md.lower():
                notes.append(f"GLUE:{g}")

        if prikaz_misplaced:
            notes.append("MISPLACED_PRIKAZ")
        if broken:
            notes.append(f"BROKEN_MAILTO={len(broken)}")
        if esc_em:
            notes.append(f"ESC_EMAIL={len(esc_em)}")
        if miss_em:
            notes.append(f"MISS_EMAIL={miss_em}")

        # footnote for 1843
        if did == 7:
            if "брак" not in md.lower() and "супруг" not in md.lower():
                notes.append("LIKELY_MISSING_FAMILY_FOOTNOTE")

        # formula context
        if formula:
            notes.append("FORMULA_NOT_DECODED")

        flat_rows = len(re.findall(r"^\|  \|", md, re.M))
        if flat_rows >= 8:
            notes.append(f"FLAT_ROWS={flat_rows}")

        notes_s = ",".join(notes)
        out.append(
            f"#{did:02d} {r['document_new'][:60]}\n"
            f"  p={pages} pdf={pdf_len} md={md_len} cov={cov} num={num_cov} imgs={imgs} "
            f"eds={int(eds)} emptyQ={int(empty_q)} sigPhone={int(sig_phone)}\n"
            f"  notes: {notes_s or '-'}"
        )
        if miss_tok:
            out.append(f"  miss_tok: {miss_tok}")
        if miss_n:
            out.append(f"  miss_num: {miss_n}")
        if pdf_emails:
            out.append(f"  pdf_email: {pdf_emails}")

        # head/tail snippets for short orders
        if pages <= 6 and pdf_len > 80:
            head = " | ".join(ln.strip() for ln in md.splitlines()[:8] if ln.strip())[:200]
            tail = " | ".join(ln.strip() for ln in md.splitlines()[-10:] if ln.strip())[:220]
            out.append(f"  md_head: {head}")
            out.append(f"  md_tail: {tail}")

    text = "\n".join(out) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
