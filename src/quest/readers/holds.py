# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Holds / service indicators."""
from __future__ import annotations

from ..core.models import Hold
from ..core.parsers import find_message, first_grid_rows
from ..core.session import QuestSession

COMPONENT = "CC_PORTFOLIO.SS_CC_HOLDS.GBL"
_EMPTY = [r"There are no (?:current )?holds[^<.]*", r"No holds[^<.]*"]


def holds(session: QuestSession) -> list[Hold]:
    html = session.get(COMPONENT)
    if find_message(html, _EMPTY):
        return []
    out: list[Hold] = []
    for row in first_grid_rows(html):
        vals = list(row.values())
        out.append(
            Hold(
                reason=row.get("Hold Item") or row.get("Hold") or (vals[0] if vals else ""),
                department=row.get("Department") or row.get("Institution") or "",
                detail=row.get("Reason") or (vals[-1] if len(vals) > 1 else ""),
            )
        )
    return out
