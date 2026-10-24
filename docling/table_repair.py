"""Repair Docling markdown tables split across pages / broken out of grid.

Does not hardcode document content — only structural heuristics.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PAGE_MARK_RE = re.compile(
    r"^(?:№\s*\d+[\-\u2013]?[а-яa-z]?|"
    r"стр\.?\s*\d+|"
    r"-\s*\d+\s*-|"
    r"\d+\s*/\s*\d+)\s*$",
    re.IGNORECASE,
)
SEP_CELL_RE = re.compile(r"^:?-{3,}:?$")


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _is_table_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    # Docling compact_tables sometimes emits "| - | - |" instead of "| --- | --- |"
    normalized = [c.strip().replace("–", "-").replace("—", "-") for c in cells]
    if all(c == "-" for c in normalized):
        return True
    return all(SEP_CELL_RE.match(c.replace(" ", "")) for c in normalized if c != "")


def _ncols(line: str) -> int:
    return len(_split_row(line))


@dataclass
class TableBlock:
    lines: list[str]

    @property
    def ncols(self) -> int:
        return _ncols(self.lines[0]) if self.lines else 0

    def _has_real_header(self) -> bool:
        if len(self.lines) < 2 or not _is_separator_row(_split_row(self.lines[1])):
            return False
        first = _split_row(self.lines[0])
        # Real headers are short labels. Long cells before a separator are
        # data rows (Docling often inserts "| - | - |" mid-table).
        return max((len(c) for c in first), default=0) <= 80

    def body_rows(self) -> list[str]:
        """Data rows only (skip header + separator if present)."""
        if self._has_real_header():
            return self.lines[2:]
        # Mid-table "| - | - |" is junk, not a header boundary — drop only that line.
        return [ln for ln in self.lines if not _is_separator_row(_split_row(ln))]

    def header_lines(self) -> list[str]:
        if self._has_real_header():
            return self.lines[:2]
        return []
def _parse_blocks(md: str) -> list[tuple[str, object]]:
    """Return list of ('table', TableBlock) or ('text', str)."""
    lines = md.splitlines()
    blocks: list[tuple[str, object]] = []
    i = 0
    n = len(lines)
    while i < n:
        if _is_table_line(lines[i]):
            start = i
            while i < n and _is_table_line(lines[i]):
                i += 1
            blocks.append(("table", TableBlock(lines[start:i])))
            continue
        start = i
        while i < n and not _is_table_line(lines[i]):
            i += 1
        text = "\n".join(lines[start:i]).strip("\n")
        if text.strip() != "" or (blocks and blocks[-1][0] == "table"):
            # keep blank-only only as separator hint via empty strip later
            blocks.append(("text", text))
    return blocks


def _is_glue_text(text: str) -> bool:
    """Text between tables that is page junk or spilled table cell, not a new section."""
    t = text.strip()
    if not t:
        return True
    # pure page marks / short debris
    parts = [p.strip() for p in re.split(r"\n+", t) if p.strip()]
    if not parts:
        return True
    if all(PAGE_MARK_RE.match(p) or len(p) <= 3 for p in parts):
        return True
    # spilled table content: no markdown headings, mostly short lines / list dashes
    if any(p.startswith("#") for p in parts):
        return False
    if re.search(r"^\d+\.\s+\S", t, re.M):  # numbered order clause
        return False
    # likely cell spill: contains rubles / level names / leading dashes, few long prose paras
    joined = " ".join(parts)
    if len(joined) > 1200:
        return False
    spill_hints = (
        "рубл",
        "баллов",
        "олимпиад",
        "ВсОШ",
        "ЕГЭ",
        "Бронзов",
        "Серебрян",
        "Золот",
        "Платин",
        "Бриллиант",
        "Высший",
    )
    if any(h in joined for h in spill_hints):
        return True
    # short multi-line fragment without sentence punctuation density
    if len(parts) >= 2 and max(len(p) for p in parts) < 80:
        return True
    return False


def _normalize_glue_to_row(text: str, ncols: int) -> list[str] | None:
    """Turn spilled glue text into one table row if possible."""
    t = text.strip()
    if not t or PAGE_MARK_RE.match(t):
        return None
    # collapse whitespace
    compact = re.sub(r"[ \t]+", " ", t)
    compact = re.sub(r"\n+", " ", compact).strip()
    if not compact:
        return None

    # Amount may sit in the middle of spilled text (Docling page breaks).
    m = re.search(
        r"(\d[\d\s]{0,12}\d|\d+)\s*(рублей|руб\.?)",
        compact,
        re.IGNORECASE,
    )
    if m and ncols >= 2:
        left = (compact[: m.start()] + " " + compact[m.end() :]).strip()
        left = re.sub(r"\s+", " ", left).strip(" -–—\t")
        right = f"{m.group(1).strip()} {m.group(2)}".replace("  ", " ")
        if left:
            row = [left] + [""] * (ncols - 2) + [right]
            return row

    # try split amount at end
    m = re.search(
        r"^(.*?)(\d[\d\s]{0,12}\d|\d+)\s*(рублей|руб\.?)\s*$",
        compact,
        re.IGNORECASE,
    )
    if m and ncols >= 2:
        left = m.group(1).strip(" -–—\t")
        right = f"{m.group(2).strip()} {m.group(3)}".replace("  ", " ")
        row = [left] + [""] * (ncols - 2) + [right]
        return row

    # single-column-ish dump into first cell
    row = [compact] + [""] * (ncols - 1)
    return row


def _format_row(cells: list[str], ncols: int) -> str:
    cells = list(cells)
    if len(cells) < ncols:
        cells += [""] * (ncols - len(cells))
    elif len(cells) > ncols:
        cells = cells[: ncols - 1] + [" ".join(cells[ncols - 1 :])]
    return "| " + " | ".join(cells) + " |"


def _separator(ncols: int) -> str:
    return "| " + " | ".join("---" for _ in range(ncols)) + " |"


def _looks_like_new_logical_table(b: TableBlock) -> bool:
    """True if B starts a new table (e.g. next appendix group), not a page split."""
    if not b.lines:
        return True
    head = " ".join(_split_row(b.lines[0]))
    if re.search(r"Группа\s*\d", head, re.IGNORECASE):
        return True
    if re.search(r"\bКатегори", head, re.IGNORECASE):
        return True
    if re.search(r"\bУровн", head, re.IGNORECASE):
        return True
    if re.search(r"^\s*№\b", head):
        return True
    # header present and first cell short label-like
    if b.header_lines() and len(head) <= 80 and not head[:1].islower():
        # still allow merge if header is anonymous 0/1 from broken export
        cells = _split_row(b.lines[0])
        if all(re.fullmatch(r"\d+", c) for c in cells if c):
            return False
    return False


def _is_junk_data_row(cells: list[str]) -> bool:
    if not cells:
        return True
    cleaned = [c.strip().replace("–", "-").replace("—", "-") for c in cells]
    if all(c == "" or c == "-" for c in cleaned):
        return True
    return False


def _is_continuation_row(cells: list[str]) -> bool:
    """Row continues previous cell (split mid-sentence across pages)."""
    if not cells:
        return False
    first = cells[0].strip()
    rest = cells[1:] if len(cells) > 1 else []
    amount = " ".join(rest).strip()
    if not first:
        # Empty first column with text in other columns is a normal body row
        # (common in RUDN "Группа N | specialty" tables), not a continuation.
        if any(c.strip() for c in rest):
            return False
        return True
    if first[:1].islower() or first.startswith(")"):
        return True
    # mid-phrase leftovers / list continuation of previous level
    if first.startswith(
        ("индивидуальн", "достижен", "и ", "или ", "по ", "на ", "- ", "– ", "— ")
    ):
        return True
    # broken amount column like lone "и" while left looks like bullet continuation
    if amount in {"и", "-", "–", "—"} and first.startswith("-"):
        return True
    return False


def _coalesce_rows(table: TableBlock) -> TableBlock:
    header = table.header_lines()
    body = table.body_rows() if header else table.lines[:]
    if not header and len(table.lines) >= 2 and _is_separator_row(_split_row(table.lines[1])):
        header = table.lines[:2]
        body = table.lines[2:]

    ncols = table.ncols
    out_rows: list[list[str]] = []
    for line in body:
        cells = _split_row(line)
        if len(cells) < ncols:
            cells += [""] * (ncols - len(cells))
        if _is_junk_data_row(cells):
            continue
        if out_rows and _is_continuation_row(cells):
            prev = out_rows[-1]
            # append text to first cell; fill empty amount from continuation if any
            prev[0] = (prev[0].rstrip() + " " + cells[0].lstrip()).strip()
            for i in range(1, ncols):
                cand = cells[i].strip()
                if not cand or cand in {"и", "-", "–", "—"}:
                    continue
                if not prev[i].strip():
                    prev[i] = cand
            continue
        out_rows.append(cells[:ncols])

    if not header:
        if not out_rows:
            return table
        header = [_format_row(out_rows[0], ncols), _separator(ncols)]
        out_rows = out_rows[1:]
    else:
        # normalize "| - | - |" style separators to markdown ---
        header = [header[0], _separator(ncols)]

    lines = header + [_format_row(r, ncols) for r in out_rows]
    return TableBlock(lines)


def _parse_numbered_cell(text: str) -> tuple[str, str] | None:
    m = re.match(r"^(\d+)\.\s*(.+)$", text.strip())
    if not m:
        return None
    return m.group(1) + ".", m.group(2).strip()


def _merge_group_header_with_list(a: TableBlock, b: TableBlock) -> TableBlock:
    """Attach 1-column specialty list to a 2-column Группа header table."""
    header = a.header_lines() or [a.lines[0], _separator(2)]
    body = a.body_rows()
    for line in b.lines:
        if _is_separator_row(_split_row(line)):
            continue
        cells = _split_row(line)
        if _is_junk_data_row(cells):
            continue
        # 1-col body -> put text in second column
        text = cells[0] if cells else ""
        if not text.strip():
            continue
        body.append(_format_row(["", text], 2))
    return _coalesce_rows(TableBlock(header + body))


def _merge_ragged_numbered_tail(a: TableBlock, b: TableBlock) -> TableBlock | None:
    """Merge 2-col '17. category | amount' tail into 3-col '№ | category | amount' table."""
    if a.ncols != 3 or b.ncols != 2:
        return None
    header = a.header_lines()
    if not header:
        return None
    body = list(a.body_rows())
    for line in b.body_rows() if b.header_lines() else b.lines:
        cells = _split_row(line)
        if _is_separator_row(cells) or _is_junk_data_row(cells):
            continue
        left = cells[0] if cells else ""
        right = cells[1] if len(cells) > 1 else ""
        parsed = _parse_numbered_cell(left)
        if parsed:
            num, cat = parsed
            body.append(_format_row([num, cat, right], 3))
        else:
            body.append(_format_row(["", left, right], 3))
    return _coalesce_rows(TableBlock(header + body))


def _try_special_merge(a: TableBlock, b: TableBlock, glue: str) -> TableBlock | None:
    if not _is_glue_text(glue):
        return None
    # Группа header (often only header rows) + 1-col continuation list
    a_head = " ".join(_split_row(a.lines[0])) if a.lines else ""
    if (
        a.ncols == 2
        and b.ncols == 1
        and re.search(r"Группа\s*\d", a_head, re.IGNORECASE)
    ):
        return _merge_group_header_with_list(a, b)
    ragged = _merge_ragged_numbered_tail(a, b)
    if ragged is not None:
        return ragged
    return None


def _merge_tables(a: TableBlock, b: TableBlock, glue: str) -> TableBlock:
    ncols = a.ncols
    header = a.header_lines()
    if not header and b.header_lines():
        header = b.header_lines()
    if not header:
        # synthesize minimal header from first row of a
        header = [a.lines[0], _separator(ncols)]
        body_a = a.lines[1:]
    else:
        body_a = a.body_rows()

    body_b = b.body_rows()
    # if b has no separator and first row looks like header duplicate of a — skip it
    if b.header_lines() and a.header_lines():
        if _split_row(b.lines[0]) == _split_row(a.lines[0]):
            body_b = b.body_rows()

    extra: list[str] = []
    row_cells = _normalize_glue_to_row(glue, ncols)
    if row_cells is not None:
        extra.append(_format_row(row_cells, ncols))

    # drop empty trailing cells-only rows
    def keep(line: str) -> bool:
        cells = _split_row(line)
        return any(c.strip() for c in cells)

    merged_lines = header + [ln for ln in body_a + extra + body_b if keep(ln)]
    return _coalesce_rows(TableBlock(merged_lines))


def repair_markdown_tables(md: str) -> str:
    blocks = _parse_blocks(md)
    out: list[tuple[str, object]] = []
    i = 0
    while i < len(blocks):
        kind, payload = blocks[i]
        if kind != "table":
            out.append((kind, payload))
            i += 1
            continue

        current = payload  # type: TableBlock
        i += 1
        while i < len(blocks):
            # optional glue text
            glue = ""
            j = i
            if j < len(blocks) and blocks[j][0] == "text":
                glue = str(blocks[j][1])
                j += 1
            if j < len(blocks) and blocks[j][0] == "table":
                nxt: TableBlock = blocks[j][1]  # type: ignore[assignment]
                special = _try_special_merge(current, nxt, glue)
                if special is not None:
                    current = special
                    i = j + 1
                    continue
                if (
                    nxt.ncols == current.ncols
                    and _is_glue_text(glue)
                    and not _looks_like_new_logical_table(nxt)
                ):
                    current = _merge_tables(current, nxt, glue)
                    i = j + 1
                    continue
            break
        out.append(("table", _coalesce_rows(current)))

    # render
    parts: list[str] = []
    for kind, payload in out:
        if kind == "table":
            parts.append("\n".join(payload.lines))  # type: ignore[union-attr]
        else:
            text = str(payload).strip("\n")
            if text.strip():
                parts.append(text)
    return "\n\n".join(parts).rstrip() + "\n"
