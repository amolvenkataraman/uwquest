# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Academic requirements (advisement report).

Experimental: UW renders this report dynamically, so a plain GET may not carry
the full requirement tree. This returns whatever requirement rows are present
(with their satisfied/not-satisfied status) as a best effort. For reliable
academic data, the transcript reader is the better source for now.
"""
from __future__ import annotations

import re

from selectolax.lexbor import LexborHTMLParser

from ..core.parsers import _clean
from ..core.session import QuestSession

COMPONENT = "SA_LEARNER_SERVICES.SAA_SS_DPR_ADB.GBL"
_STATUS = re.compile(r"(Not Satisfied|Satisfied|In Progress|Complete)", re.I)


def academic_requirements(session: QuestSession) -> list[dict]:
    """Requirement rows found on the advisement report (experimental)."""
    tree = LexborHTMLParser(session.get(COMPONENT))
    out: list[dict] = []
    seen: set[str] = set()
    for el in tree.css("div.ps_box-group, tr, div.ps-htmlarea, span"):
        text = _clean(el.text())
        if not text or len(text) > 160 or text in seen:
            continue
        m = _STATUS.search(text)
        if m:
            seen.add(text)
            out.append({"requirement": text[: m.start()].strip(" :-"), "status": m.group(1)})
    return out
