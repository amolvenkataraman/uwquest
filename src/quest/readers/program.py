# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""My Program: plan, academic load, campus."""
from __future__ import annotations

from ..core.models import Program
from ..core.parsers import field_value
from ..core.session import QuestSession

COMPONENT = "UW_SS_MENU.UW_SS_MYPROG_UG.GBL"


def program(session: QuestSession) -> Program:
    html = session.get(COMPONENT)
    return Program(
        plan=field_value(html, "UW_ACADPLTBL_VW_TRNSCR_DESCR"),
        academic_load=field_value(html, "UW_SSR_INSPROG_ACAD_LOAD_APPR"),
        campus=field_value(html, "UW_SSR_INSPROG_CAMPUS"),
    )
