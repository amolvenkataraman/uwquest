# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Readers: one function per Quest page, returning plain data."""

from .academic_requirements import academic_requirements
from .account import account
from .course_availability import course_availability
from .dashboard import dashboard
from .enrollment_dates import enrollment_dates
from .financial_aid import financial_aid
from .grades import available_terms, grades
from .holds import holds
from .milestones import milestones
from .program import program
from .schedule import schedule
from .transcript import transcript_pdf

__all__ = [
    "academic_requirements",
    "account",
    "available_terms",
    "course_availability",
    "dashboard",
    "enrollment_dates",
    "financial_aid",
    "grades",
    "holds",
    "milestones",
    "program",
    "schedule",
    "transcript_pdf",
]
