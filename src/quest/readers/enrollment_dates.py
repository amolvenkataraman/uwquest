# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Enrollment appointments: when you may enroll, and your unit limits."""
from __future__ import annotations

from ..core.parsers import grid_by_fields
from ..core.session import QuestSession

COMPONENT = "SA_LEARNER_SERVICES.SSR_SSENRL_APPT.GBL"
_COLUMNS = {"session": "OPEN_NAME", "begins_on": "OPEN_START"}


def enrollment_dates(session: QuestSession) -> list[dict]:
    """Enrollment appointment rows: session and when enrollment opens."""
    return grid_by_fields(session.get(COMPONENT), _COLUMNS)
