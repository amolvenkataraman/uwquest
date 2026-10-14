# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Milestones (e.g. communication requirement, scholarships)."""
from __future__ import annotations

from ..core.models import Milestone
from ..core.parsers import grid_by_fields
from ..core.session import QuestSession

COMPONENT = "SA_LEARNER_SERVICES_2.SS_SR_MILESTONES.GBL"
_COLUMNS = {
    "milestone": "MLSTN_DESCR",
    "status": "DERIVED_SR_MLST_SSR_DESCR_MLSTN_CM",
    "program": "DERIVED_SR_MLST_SSR_DESCR_PROG",
}


def milestones(session: QuestSession) -> list[Milestone]:
    html = session.get(COMPONENT)
    return [Milestone(**row) for row in grid_by_fields(html, _COLUMNS)]
