# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Financial aid: award years on record."""
from __future__ import annotations

from ..core.parsers import grid_by_fields
from ..core.session import QuestSession

COMPONENT = "SA_LEARNER_SERVICES.SS_FA_AWARDS.GBL"
_COLUMNS = {
    "aid_year": "AID_YEAR_LINK_FLD",
    "institution": "INSTITUTION_TBL_DESCR",
    "description": "DERIVED_FA_SS_1_DESCR60",
}


def financial_aid(session: QuestSession) -> list[dict]:
    """Aid years available. (Per-year award detail is a drill, added later.)"""
    return grid_by_fields(session.get(COMPONENT), _COLUMNS)
