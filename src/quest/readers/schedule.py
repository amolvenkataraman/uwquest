# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Class schedule for the current term.

PeopleSoft renders the schedule as one block per enrolled course: a divider with
the course name, a class-level scroll (status/units/grading) and a meetings
scroll (one row per meeting pattern). The data lives in nested value cells with
stable field ids, so this reads those ids rather than the layout tables.
"""
from __future__ import annotations

from selectolax.lexbor import LexborHTMLParser

from ..core.models import Meeting, ScheduleClass
from ..core.parsers import _clean
from ..core.session import QuestSession

COMPONENT = "SA_LEARNER_SERVICES.SSR_SSENRL_LIST.GBL"

# Field-id bases of the value cells inside each course block.
_MTG = {
    "class_nbr": "DERIVED_CLS_DTL_CLASS_NBR",
    "section": "MTG_SECTION",
    "component": "MTG_COMP",
    "days_times": "MTG_SCHED",
    "room": "MTG_LOC",
    "instructor": "DERIVED_CLS_DTL_SSR_INSTR_LONG",
    "start_end": "MTG_DATES",
}
_CLASS = {"status": "STATUS", "units": "DERIVED_REGFRM1_UNT_TAKEN", "grading": "GB_DESCR"}


def _values(node, base: str) -> dict[int, str]:
    """{row index -> text} for value cells whose id is exactly ``base$<digits>``."""
    out: dict[int, str] = {}
    if node is None:
        return out
    prefix = base + "$"
    for el in node.css("span, a, div"):
        i = el.attributes.get("id", "")
        if i.startswith(prefix):
            suf = i[len(prefix):]
            if suf.isdigit() and int(suf) not in out:
                text = _clean(el.text())
                if text:
                    out[int(suf)] = text
    return out


def schedule(session: QuestSession) -> list[ScheduleClass]:
    html = session.get(COMPONENT)
    tree = LexborHTMLParser(html)
    by_id = {t.attributes.get("id", ""): t for t in tree.css("table")}
    dividers = [_clean(t.text()) for t in tree.css("td.PAGROUPDIVIDER")]

    out: list[ScheduleClass] = []
    n = 0
    while True:
        cls_t = by_id.get(f"SSR_DUMMY_RECVW$scroll${n}")
        mtg_t = by_id.get(f"CLASS_MTG_VW$scroll${n}")
        if cls_t is None and mtg_t is None:
            break
        cls = {k: next(iter(_values(cls_t, base).values()), "") for k, base in _CLASS.items()}
        fields = {k: _values(mtg_t, base) for k, base in _MTG.items()}
        rows = sorted({i for v in fields.values() for i in v})
        meetings = [
            Meeting(**{k: fields[k].get(i, "") for k in _MTG}) for i in rows
        ]
        out.append(
            ScheduleClass(
                course=dividers[n] if n < len(dividers) else "",
                status=cls["status"],
                units=cls["units"],
                grading=cls["grading"],
                meetings=meetings,
            )
        )
        n += 1
    return out
