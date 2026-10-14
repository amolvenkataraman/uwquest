# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""A one-call summary of your Quest standing, composed from the other readers."""
from __future__ import annotations

from ..core.session import QuestSession
from .account import account
from .enrollment_dates import enrollment_dates
from .holds import holds
from .program import program
from .schedule import schedule


def dashboard(session: QuestSession) -> dict:
    """Program, balances, holds, next enrollment, and this term's classes."""
    prog = program(session)
    acct = account(session)
    hold_list = holds(session)
    enr = enrollment_dates(session)
    sched = schedule(session)
    return {
        "program": prog.to_dict(),
        "holds": [h.to_dict() for h in hold_list],
        "hold_count": len(hold_list),
        "account": [a.to_dict() for a in acct],
        "next_enrollment": enr[0] if enr else None,
        "classes_this_term": len(sched),
        "schedule": [s.to_dict() for s in sched],
    }
