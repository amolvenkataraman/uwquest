# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Plain, JSON-serialisable data the readers return."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Hold:
    reason: str
    department: str = ""
    detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AccountTerm:
    term: str
    registered_status: str = ""
    balance: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Meeting:
    class_nbr: str = ""
    section: str = ""
    component: str = ""
    days_times: str = ""
    room: str = ""
    instructor: str = ""
    start_end: str = ""


@dataclass
class ScheduleClass:
    course: str = ""
    status: str = ""
    units: str = ""
    grading: str = ""
    grade: str = ""
    meetings: list[Meeting] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CourseGrade:
    course: str = ""
    description: str = ""
    units: str = ""
    grading: str = ""
    grade: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Milestone:
    milestone: str = ""
    level: str = ""
    status: str = ""
    program: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Program:
    plan: str = ""
    academic_load: str = ""
    campus: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClassSection:
    class_nbr: str = ""
    section: str = ""
    status: str = ""
    days_time: str = ""
    room: str = ""
    instructor: str = ""
    dates: str = ""
    campus: str = ""
    # populated only when seat counts are requested (a per-section drill):
    enrollment_cap: str = ""
    enrollment_total: str = ""
    available_seats: str = ""
    waitlist_total: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Row:
    """A generic parsed grid row, when no typed model applies yet."""

    cells: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dict(self.cells)
