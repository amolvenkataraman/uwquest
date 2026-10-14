# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""HTML parsing helpers for PeopleSoft classic grids and pages.

PeopleSoft renders data as <table> grids with header cells carrying a
`PSLEVEL*GRIDCOLUMNHDR` class and body cells carrying `PSLEVEL*GRID*ROW`. These
helpers pull clean header/row data out without depending on exact field ids.
"""
from __future__ import annotations

import re

from selectolax.lexbor import LexborHTMLParser as HTMLParser

_WS = re.compile(r"\s+")


def _clean(text: str) -> str:
    return _WS.sub(" ", text.replace("\xa0", " ")).strip()


def find_message(html: str, patterns: list[str]) -> str | None:
    """Return the first matching status/empty-state message, if present."""
    for p in patterns:
        m = re.search(p, html, re.I)
        if m:
            return _clean(m.group(0))
    return None


def _is_grid(table) -> bool:
    cls = table.attributes.get("class") or ""
    if "GRID" in cls.upper() or "ps_grid" in cls:
        return True
    # a table that contains PeopleSoft grid header cells
    return table.css_first("th.PSLEVEL1GRIDCOLUMNHDR, th[class*=GRIDCOLUMNHDR]") is not None


def grids(html: str) -> list:
    """All PeopleSoft data-grid tables on the page, in document order."""
    tree = HTMLParser(html)
    return [t for t in tree.css("table") if _is_grid(t)]


def parse_grid(table) -> list[dict]:
    """Turn one grid <table> node into a list of {header: value} rows."""
    headers: list[str] = []
    for th in table.css("th"):
        headers.append(_clean(th.text()))
    rows: list[dict] = []
    for tr in table.css("tr"):
        cells = tr.css("td")
        if not cells:
            continue
        values = [_clean(td.text()) for td in cells]
        if not any(values):
            continue
        if headers and len(headers) == len(values):
            rows.append(dict(zip(headers, values, strict=False)))
        else:
            rows.append({str(i): v for i, v in enumerate(values)})
    return rows


def first_grid_rows(html: str, min_cols: int = 2) -> list[dict]:
    """Rows of the first grid with at least `min_cols` header columns."""
    for table in grids(html):
        rows = parse_grid(table)
        if rows and len(rows[0]) >= min_cols:
            return rows
    return []


def page_title(html: str) -> str:
    m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    return _clean(m.group(1)) if m else ""


_TERM = re.compile(r"id='TERM_CAR\$(\d+)'[^>]*>([^<]+)<")
_GO = re.compile(r"'([A-Z0-9_]*(?:SSR_PB_GO|PB_GO)[A-Z0-9_]*)'")


def parse_terms(html: str) -> list[tuple[int, str]]:
    """Term picker rows as (row index, label), e.g. (0, 'Fall 2026')."""
    return [(int(i), _clean(label)) for i, label in _TERM.findall(html)]


def find_go_action(html: str) -> str | None:
    """The 'continue' / GO ICAction id on a term-picker page, if present."""
    m = _GO.search(html)
    return m.group(1) if m else None


def _id_text_map(source) -> dict[str, str]:
    tree = source if hasattr(source, "css") else HTMLParser(source)
    out: dict[str, str] = {}
    for el in tree.css("span, a, div"):
        i = el.attributes.get("id", "")
        if "$" in i and i not in out:
            text = _clean(el.text())
            if text:
                out[i] = text
    return out


def field_value(source, base: str, index: int = 0) -> str:
    """Text of the value cell whose id is ``base$<index>``."""
    return _id_text_map(source).get(f"{base}${index}", "")


def text_by_id(source, element_id: str) -> str:
    """Text of the element with this exact id (for non-indexed detail fields)."""
    tree = source if hasattr(source, "css") else HTMLParser(source)
    el = tree.css_first(f"[id='{element_id}']")
    return _clean(el.text()) if el else ""


def grid_by_fields(source, columns: dict[str, str]) -> list[dict]:
    """Extract a PeopleSoft nested grid by field id.

    `columns` maps output names to field-id bases (e.g. {"grade": "CRSE_GRADE_OFF"}).
    Each grid row shares an index suffix (`BASE$<row>`); returns one dict per row.
    """
    idmap = _id_text_map(source)
    cols: dict[str, dict[int, str]] = {}
    for name, base in columns.items():
        prefix = base + "$"
        d: dict[int, str] = {}
        for key, val in idmap.items():
            if key.startswith(prefix):
                suf = key[len(prefix):]
                if suf.isdigit():
                    d[int(suf)] = val
        cols[name] = d
    indices = sorted({i for d in cols.values() for i in d})
    return [{name: cols[name].get(i, "") for name in columns} for i in indices]
