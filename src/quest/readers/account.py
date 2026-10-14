# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Account summary: per-term registration status and balance."""
from __future__ import annotations

from ..core.models import AccountTerm
from ..core.parsers import first_grid_rows
from ..core.session import QuestSession

COMPONENT = "SA_LEARNER_SERVICES.UW_SS_ACCT_SUMMARY.GBL"


def account(session: QuestSession) -> list[AccountTerm]:
    html = session.get(COMPONENT)
    out: list[AccountTerm] = []
    for row in first_grid_rows(html):
        vals = list(row.values())
        out.append(
            AccountTerm(
                term=row.get("Term") or (vals[0] if vals else ""),
                registered_status=row.get("Registered Status") or row.get("Status") or "",
                balance=row.get("Term Balance") or row.get("Balance") or (vals[-1] if vals else ""),
            )
        )
    return out
