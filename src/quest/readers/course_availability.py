# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Course availability via Class Search — live section status, no enrollment.

A pure read: searches classes and reports each section with its Open / Closed /
Waitlist status and meeting details. It never touches the shopping cart or the
enrollment engine.
"""
from __future__ import annotations

import re
import unicodedata

from selectolax.lexbor import LexborHTMLParser

from ..core.models import ClassSection
from ..core.parsers import _clean, text_by_id
from ..core.session import QuestSession
from ..errors import QuestError

COMPONENT = "UW_CEM.UW_CLASS_SRCH.GBL"
SEARCH_ACTION = "CLASS_SRCH_WRK2_SSR_PB_CLASS_SRCH"
BACK_ACTION = "CLASS_SRCH_WRK2_SSR_PB_BACK"
_SEAT_FIELDS = {
    "enrollment_cap": "SSR_CLS_DTL_WRK_ENRL_CAP",
    "enrollment_total": "SSR_CLS_DTL_WRK_ENRL_TOT",
    "available_seats": "SSR_CLS_DTL_WRK_AVAILABLE_SEATS",
    "waitlist_total": "SSR_CLS_DTL_WRK_WAIT_TOT",
}
MAX_SEAT_DRILLS = 40

_RESULT_FIELDS = {
    "class_nbr": "MTG_CLASS_NBR",
    "section": "MTG_CLASSNAME",
    "days_time": "MTG_DAYTIME",
    "room": "MTG_ROOM",
    "instructor": "MTG_INSTR",
    "dates": "MTG_TOPIC",
    "campus": "UW_DERIVED_CLSR_CAMPUS",
}
_STATUS_ALTS = {"Open", "Closed"}


def _strip_marks(text: str) -> str:
    return "".join(c for c in text if unicodedata.category(c) != "Cf").strip()


def _term_options(html: str) -> list[tuple[str, str]]:
    sel = re.search(r"name=['\"][^'\"]*STRM[^'\"]*['\"](.*?)</select>", html, re.S)
    if not sel:
        return []
    opts = re.findall(r"<option value=['\"](\d+)['\"][^>]*>([^<]+)</option>", sel.group(1))
    return [(code, _strip_marks(label)) for code, label in opts]


def _field_name(html: str, needle: str) -> str | None:
    m = re.search(r"name='([^']*" + needle + r"[^']*)'", html)
    return m.group(1) if m else None


def _by_base(tree, base: str) -> dict[int, str]:
    out: dict[int, str] = {}
    prefix = base + "$"
    for el in tree.css("span, a, div"):
        i = el.attributes.get("id", "")
        if i.startswith(prefix) and i[len(prefix):].isdigit():
            idx = int(i[len(prefix):])
            if idx not in out:
                text = _clean(el.text())
                if text:
                    out[idx] = text
    return out


def _is_status(alt: str) -> bool:
    return alt in _STATUS_ALTS or alt.startswith("Wait")


def _statuses_by_index(tree) -> dict[int, str]:
    """Map each section index to its status icon, found in the section's own row.

    The status icon carries no id, and a legend repeats the same icons, so the
    only reliable key is DOM proximity to that section's class-name cell.
    """
    out: dict[int, str] = {}
    for el in tree.css("[id^='MTG_CLASSNAME$']"):
        m = re.search(r"\$(\d+)$", el.attributes.get("id", ""))
        if not m:
            continue
        idx = int(m.group(1))
        node = el
        for _ in range(8):  # walk up to the enclosing row, then look inside it
            node = node.parent
            if node is None:
                break
            if node.tag == "tr":
                for img in node.css("img"):
                    if _is_status(img.attributes.get("alt", "")):
                        out[idx] = img.attributes.get("alt", "")
                        break
                break
    return out


def course_availability(
    session: QuestSession,
    subject: str,
    catalog_nbr: str | None = None,
    term: str | None = None,
    *,
    open_only: bool = False,
    with_seats: bool = False,
) -> list[ClassSection]:
    html = session.get(COMPONENT)
    terms = _term_options(html)
    if not terms:
        raise QuestError("class search did not offer any terms")
    if term:
        match = [c for c, label in terms if label.lower() == term.lower()]
        if not match:
            have = ", ".join(label for _, label in terms)
            raise QuestError(f"term {term!r} not available. Choose one of: {have}")
        term_code = match[0]
    else:
        term_code = terms[0][0]

    inst = _field_name(html, "INSTITUTION") or "CLASS_SRCH_WRK2_INSTITUTION$31$"
    strm = _field_name(html, "STRM") or "CLASS_SRCH_WRK2_STRM$35$"
    fields = {
        inst: "UWATR",
        strm: term_code,
        "SSR_CLSRCH_WRK_SUBJECT$0": subject.upper(),
        "SSR_CLSRCH_WRK_SSR_EXACT_MATCH1$1": "E" if catalog_nbr else "G",
        "SSR_CLSRCH_WRK_ACAD_CAREER$2": "UG",
        "SSR_CLSRCH_WRK_SSR_OPEN_ONLY$chk$3": "Y" if open_only else "N",
    }
    if catalog_nbr:
        fields["SSR_CLSRCH_WRK_CATALOG_NBR$1"] = str(catalog_nbr)

    html = session.action(COMPONENT, SEARCH_ACTION, fields)
    tree = LexborHTMLParser(html)
    cols = {name: _by_base(tree, base) for name, base in _RESULT_FIELDS.items()}
    indices = sorted({i for d in cols.values() for i in d})
    status = _statuses_by_index(tree)
    sections = [
        ClassSection(
            status=status.get(i, ""),
            **{name: cols[name].get(i, "") for name in _RESULT_FIELDS},
        )
        for i in indices
    ]
    if with_seats:
        # Each section is a drill-in then back-out, so this is 2 requests per
        # section. Capped to keep a broad search from hammering the SIS.
        for pos, i in enumerate(indices[:MAX_SEAT_DRILLS]):
            detail = session.action(COMPONENT, f"MTG_CLASS_NBR${i}")
            for attr, element_id in _SEAT_FIELDS.items():
                setattr(sections[pos], attr, text_by_id(detail, element_id))
            session.action(COMPONENT, BACK_ACTION)
    return sections
