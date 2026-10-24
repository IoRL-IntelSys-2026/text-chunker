"""Post-process Docling markdown for RAG (EDS strip, header order, images).

Usage:
  python docling/postprocess_md.py path/to/file.md
  python docling/postprocess_md.py path/to/file.md --in-place
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

EDS_BLOCK_RE = re.compile(
    r"(?:Документ подписан простой электронной подписью|"
    r"Информация о владельце:|"
    r"Уникальный программный ключ:|"
    r"Действительный документ|"
    r"Документ хранится в программе|"
    r"Электронная копия документа)"
    r".*?(?=\n\n|\n(?:#{1,3}\s|Федеральное|\d+\s+[а-я]|\Z))",
    re.S | re.I,
)

EDS_LINE_RE = re.compile(
    r"^(?:"
    r"Документ подписан простой электронной подписью.*"
    r"|Информация о владельце:.*"
    r"|ФИО:\s*.*"
    r"|Должность:\s*.*"
    r"|Дата подписания:\s*.*"
    r"|Уникальный программный ключ:\s*.*"
    r"|[0-9a-f]{32,}"
    r"|Действительный документ.*"
    r"|Документ хранится в программе.*"
    r"|Электронная копия документа.*"
    r")\s*$",
    re.I,
)

IMAGE_PH_RE = re.compile(r"<!--\s*image\s*-->\s*\n?", re.I)

# Mid-body header cluster Docling sometimes emits after page break
MISPLACED_PRIKAZ_RE = re.compile(
    r"\n(?:<!--\s*image\s*-->\s*\n+)?##\s*ПРИКАЗ\s*\n+"
    r"(?:Москва\s*\n+)?"
    r"(№\s*[^\n]+)\s*\n+",
    re.I,
)


def strip_eds(md: str) -> str:
    lines = []
    for ln in md.splitlines():
        if EDS_LINE_RE.match(ln.strip()):
            continue
        # stamp often glued into one long line at top
        if "электронной подписью" in ln.lower() and (
            "Уникальный программный ключ" in ln or "ФИО:" in ln
        ):
            # drop stamp; keep leading university name if present before stamp
            before = re.split(
                r"Документ подписан простой электронной подписью",
                ln,
                maxsplit=1,
                flags=re.I,
            )[0].strip()
            if before and "ФИО:" not in before:
                lines.append(before)
            continue
        if "Документ подписан простой электронной подписью" in ln:
            parts = re.split(
                r"Уникальный программный ключ:\s*[0-9a-f]+\s*",
                ln,
                maxsplit=1,
                flags=re.I,
            )
            if len(parts) == 2 and parts[1].strip() and "ФИО:" not in parts[1]:
                lines.append(parts[1].strip())
            continue
        # leftover stamp fields glued after university name
        ln = re.sub(
            r"\s*ФИО:\s*.*?Должность:\s*.*?Дата подписания:\s*\S+(?:\s+\S+)?\s*",
            " ",
            ln,
            flags=re.I,
        )
        ln = re.sub(r"\s*Уникальный программный ключ:\s*[0-9a-f]+\s*", " ", ln, flags=re.I)
        lines.append(ln.rstrip())
    text = "\n".join(lines)
    text = EDS_BLOCK_RE.sub("\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def strip_image_placeholders(md: str) -> str:
    return IMAGE_PH_RE.sub("\n", md)


def repair_misplaced_prikaz_header(md: str) -> str:
    """If ## ПРИКАЗ / № appear after ПРИКАЗЫВАЮ, move them to the top."""
    m = MISPLACED_PRIKAZ_RE.search(md)
    if not m:
        return md
    # only treat as misplaced when body already started
    head = md[: m.start()]
    if not re.search(r"ПРИКАЗЫВАЮ", head, re.I):
        return md

    number = m.group(1).strip()
    body = md[: m.start()] + md[m.end() :]

    # pull date if present near start of body
    date_m = re.search(
        r"^(\d{1,2}\s+[а-яё]+(?:\s+\d{4}\s*г\.?)\s*)$",
        body,
        re.M | re.I,
    )
    date_line = date_m.group(1).strip() if date_m else ""

    # remove empty "" title artifact and lone Москва left in body
    body = re.sub(r'^""\s*$', "", body, flags=re.M)
    body = re.sub(r"^Москва\s*$", "", body, flags=re.M)

    header_bits = ["## ПРИКАЗ", ""]
    if date_line:
        header_bits.append(date_line)
    header_bits.extend(["Москва", number, ""])
    header = "\n".join(header_bits)

    # drop duplicate date from body (will sit under header)
    if date_line:
        body = re.sub(
            rf"^{re.escape(date_line)}\s*$",
            "",
            body,
            count=1,
            flags=re.M,
        )

    # university name often first — keep it above ПРИКАЗ if present
    uni = re.match(
        r"^(Федеральное[\s\S]*?\(РУДН\))\s*\n+",
        body.strip() + "\n",
    )
    if uni:
        uni_block = uni.group(1).strip() + "\n\n"
        rest = body.strip()[len(uni.group(0).rstrip()) :].lstrip()
        # uni match consumed trailing newlines differently — safer split
        rest = body[uni.end() :] if uni.end() <= len(body) else body
        # fallback: simple
        parts = body.split("\n", 1)
        # rebuild from regex on full body
        bm = re.match(
            r"^(?P<uni>Федеральное[\s\S]*?\(РУДН\))\s*(?P<rest>[\s\S]*)$",
            body.strip(),
        )
        if bm:
            out = bm.group("uni").strip() + "\n\n" + header + bm.group("rest").lstrip()
            return re.sub(r"\n{3,}", "\n\n", out).strip() + "\n"

    out = header + body.lstrip()
    return re.sub(r"\n{3,}", "\n\n", out).strip() + "\n"


def glue_broken_stipend_phrase(md: str) -> str:
    """Join '...стипендиальной' + 'комиссии РУДН), не ниже...' across the old break."""
    return re.sub(
        r"(стипендиальной)\s*\n+(комиссии\s+РУДН\))",
        r"\1 \2",
        md,
        flags=re.I,
    )


def repair_signature_block(md: str) -> str:
    """Separate rector from executor phone; restore Ефремова if phone present without name."""
    # Normalize trailing signature
    pat = re.compile(
        r"##\s*Ректор\s*\n+"
        r"(?:О\.А\.\s*Ястребов\s*\n+)?"
        r"(?:И\.В\.\s*Ефремова\s*\n+)?"
        r"(\+7[\d\s().\-,доб]+)\s*$",
        re.I | re.S,
    )

    def repl(m: re.Match[str]) -> str:
        phone = m.group(1).strip()
        return (
            "## Ректор\n\n"
            "О.А. Ястребов\n\n"
            "Исполнитель: И.В. Ефремова  \n"
            f"{phone}\n"
        )

    md2, n = pat.subn(repl, md)
    if n:
        return md2

    # Variant: rector name then phone, no Efremova line
    pat2 = re.compile(
        r"(##\s*Ректор\s*\n+О\.А\.\s*Ястребов\s*\n+)(\+7[\d\s().\-,доб]+)\s*$",
        re.I,
    )
    return pat2.sub(
        r"\1\nИсполнитель: И.В. Ефремова  \n\2\n",
        md,
    )


def postprocess_md(md: str) -> str:
    md = strip_image_placeholders(md)
    md = strip_eds(md)
    md = repair_misplaced_prikaz_header(md)
    md = glue_broken_stipend_phrase(md)
    md = repair_signature_block(md)
    md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
    return md


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("md_path", type=Path)
    ap.add_argument("--in-place", action="store_true")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path (default: stdout or in-place)",
    )
    args = ap.parse_args()
    raw = args.md_path.read_text(encoding="utf-8")
    out = postprocess_md(raw)
    if args.in_place:
        args.md_path.write_text(out, encoding="utf-8")
        print(f"updated {args.md_path} ({len(raw)} -> {len(out)} chars)")
    elif args.output:
        args.output.write_text(out, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(out, end="")


if __name__ == "__main__":
    main()
