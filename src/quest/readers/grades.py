# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Grades for a term (the term-picker handshake)."""
from __future__ import annotations

from ..core.models import CourseGrade
from ..core.parsers import find_go_action, grid_by_fields, parse_terms
from ..core.session import QuestSession
from ..errors import QuestError

COMPONENT = "UW_SS_MENU.UW_SSR_SSENRL_GRDE.GBL"
TERM_FIELD = "SSR_DUMMY_RECV1$sels$0"
_FALLBACK_GO = "UW_DRVD_SSS_SCT_SSR_PB_GO"
_COLUMNS = {
    "course": "win0divCLS_LINK",
    "description": "CLASS_TBL_VW_DESCR",
    "units": "STDNT_ENRL_SSV1_UNT_TAKEN",
    "grading": "GRADING_BASIS",
    "grade": "STDNT_ENRL_SSV1_CRSE_GRADE_OFF",
}


def available_terms(session: QuestSession) -> list[str]:
    """The term labels the grades page offers, most recent first."""
    return [label for _, label in parse_terms(session.get(COMPONENT))]


def grades(session: QuestSession, term: str | None = None) -> list[CourseGrade]:
    html = session.get(COMPONENT)
    terms = parse_terms(html)
    if terms:
        if term:
            match = [i for i, label in terms if label.lower() == term.lower()]
            if not match:
                have = ", ".join(label for _, label in terms)
                raise QuestError(f"term {term!r} not available. Choose one of: {have}")
            idx = match[0]
        else:
            idx = terms[0][0]  # most recent
        go = find_go_action(html) or _FALLBACK_GO
        html = session.action(COMPONENT, go, {TERM_FIELD: str(idx)})

    return [CourseGrade(**row) for row in grid_by_fields(html, _COLUMNS)]
