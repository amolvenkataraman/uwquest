# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Demo mode: run the CLI or TUI against synthetic data, with no network access.

Used to record the README demo. Every record below is made up (fictional student,
instructors, grades and balances); nothing here came from a real Quest account.

    python scripts/demo.py status
    python scripts/demo.py grades --term "Winter 2026"
    python scripts/demo.py tui
"""
from __future__ import annotations

import sys

from quest import cli, readers
from quest.core.models import (
    AccountTerm,
    ClassSection,
    CourseGrade,
    Meeting,
    Milestone,
    Program,
    ScheduleClass,
)
from quest.errors import QuestError

FALL = "09/09/2026 - 12/08/2026"

PROGRAM = Program("Computer Science, Honours, Co-operative Program", "Full-Time",
                  "University of Waterloo - Main")

ACCOUNT = [
    AccountTerm("Fall 2026", "Fees Arranged", "0.00"),
    AccountTerm("Winter 2026", "Fees Arranged", "0.00"),
    AccountTerm("Spring 2025", "Fees Arranged", "0.00"),
    AccountTerm("Fall 2024", "Fees Arranged", "0.00"),
]

TERMS = [a.term for a in ACCOUNT]

ENROLLMENT_DATES = [
    {"session": "Course Selection Session", "begins_on": "October 26, 2026"},
    {"session": "Regular Academic Session", "begins_on": "November 23, 2026"},
]


def _cls(course, section, comp, when, room, who, nbr):
    return ScheduleClass(course, "Enrolled", "0.50", "Numeric Grading Basis", "",
                         [Meeting(nbr, section, comp, when, room, who, FALL)])


SCHEDULE = [
    _cls("CS 341 - Algorithms", "002", "LEC", "TTh 11:30AM - 12:50PM", "MC 2065",
         "Maya Okafor", "4410"),
    _cls("CS 350 - Operating Systems", "001", "LEC", "MW 10:00AM - 11:20AM", "MC 4020",
         "Daniel Reyes", "4523"),
    _cls("CS 370 - Numerical Computation", "003", "LEC", "MW 1:00PM - 2:20PM", "DC 1350",
         "Hannah Lindqvist", "4687"),
    _cls("STAT 231 - Statistics", "001", "LEC", "TTh 2:30PM - 3:50PM", "M3 1006",
         "Arjun Mehta", "5102"),
    _cls("PHIL 145 - Critical Thinking", "081", "LEC", "TBA", "ONLN - Online",
         "Elena Rossi", "5390"),
]

GRADES = {
    "Winter 2026": [
        CourseGrade("CS 240", "Data Structures & Data Mgmt", "0.50", "Numeric Grading Basis", "84"),
        CourseGrade("CS 245", "Logic and Computation", "0.50", "Numeric Grading Basis", "77"),
        CourseGrade("CS 246", "Object-Oriented Software Devel", "0.50", "Numeric Grading Basis",
                    "90"),
        CourseGrade("MATH 239", "Intro Combinatorics", "0.50", "Numeric Grading Basis", "72"),
        CourseGrade("ECON 102", "Intro Macroeconomics", "0.50", "Credit/No Credit", "CR"),
    ],
}
GRADES["Fall 2026"] = [
    CourseGrade(c.course.split(" - ")[0], c.course.split(" - ")[1], c.units, c.grading, "")
    for c in SCHEDULE
]

MILESTONES = [
    Milestone("UG Communication - Part 1", "", "Completed", "Computer Science HC"),
    Milestone("Work Term 1", "", "Completed", "Computer Science HC"),
    Milestone("Work Term 2", "", "Completed", "Computer Science HC"),
    Milestone("Work Term 3", "", "In Progress", "Computer Science HC"),
]

FINANCIAL_AID = [
    {"aid_year": "2027", "institution": "University of Waterloo",
     "description": "Financial Aid Year 2026-2027"},
    {"aid_year": "2026", "institution": "University of Waterloo",
     "description": "Financial Aid Year 2025-2026"},
]


def _sections(term: str, with_seats: bool) -> list[ClassSection]:
    dates = "01/06/2027 - 04/05/2027"
    rows = [
        ("6101", "001-LEC Regular", "Open", "MW 8:30AM - 9:50AM", "MC 2038", "Maya Okafor",
         ("120", "104", "16", "0")),
        ("6102", "002-LEC Regular", "Closed", "TTh 11:30AM - 12:50PM", "MC 2065",
         "Priya Natarajan", ("120", "120", "0", "0")),
        ("6103", "003-LEC Regular", "Wait List", "TTh 4:00PM - 5:20PM", "DC 1351",
         "Priya Natarajan", ("90", "90", "0", "7")),
        ("6201", "101-TUT Regular", "Open", "F 10:30AM - 11:20AM", "MC 4045",
         "To be Announced", ("110", "61", "49", "0")),
        ("6202", "102-TUT Regular", "Open", "F 1:30PM - 2:20PM", "MC 4045",
         "To be Announced", ("110", "88", "22", "0")),
    ]
    out = []
    for nbr, sect, status, when, room, who, seats in rows:
        s = ClassSection(nbr, sect, status, when, room, who, dates, "UW")
        if with_seats:
            s.enrollment_cap, s.enrollment_total, s.available_seats, s.waitlist_total = seats
        out.append(s)
    return out


def _course_availability(session, subject, catalog_nbr=None, *, term=None, open_only=False,
                         with_seats=False):
    if subject.upper() != "CS" or catalog_nbr not in (None, "341"):
        raise QuestError("demo mode only has CS 341")
    sections = _sections(term or "Winter 2027", with_seats)
    return [s for s in sections if s.status == "Open"] if open_only else sections


def _grades(session, term=None):
    term = term or TERMS[0]
    return GRADES.get(term.title(), [])


def _dashboard(session) -> dict:
    return {
        "program": PROGRAM.to_dict(),
        "holds": [],
        "hold_count": 0,
        "account": [a.to_dict() for a in ACCOUNT],
        "next_enrollment": ENROLLMENT_DATES[0],
        "classes_this_term": len(SCHEDULE),
        "schedule": [s.to_dict() for s in SCHEDULE],
    }


class _NoNetwork:
    """Session stand-in: any reader not stubbed here fails instead of going online."""

    def get(self, *a, **kw):
        raise QuestError("not available in demo mode")

    action = report = get

    def close(self) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        pass


def install() -> None:
    stubs = {
        "dashboard": _dashboard,
        "program": lambda s: PROGRAM,
        "account": lambda s: ACCOUNT,
        "holds": lambda s: [],
        "schedule": lambda s: SCHEDULE,
        "available_terms": lambda s: TERMS,
        "grades": _grades,
        "enrollment_dates": lambda s: ENROLLMENT_DATES,
        "milestones": lambda s: MILESTONES,
        "financial_aid": lambda s: FINANCIAL_AID,
        "course_availability": _course_availability,
    }
    for name, fn in stubs.items():
        setattr(readers, name, fn)
    cli._build_session = lambda args: _NoNetwork()


if __name__ == "__main__":
    install()
    sys.exit(cli.main(sys.argv[1:]))
