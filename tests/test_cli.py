# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""CLI output tests with stubbed readers (synthetic data, no network)."""
import json

import pytest

from quest import cli, readers
from quest.core.models import ClassSection, Meeting, ScheduleClass

SCHEDULE = [
    ScheduleClass("CS 341 - Algorithms", "Enrolled", "0.50", "Numeric Grading Basis", "", [
        Meeting("1234", "001", "LEC", "TTh 11:30AM - 12:50PM", "MC 2065", "A. Instructor"),
        Meeting("1235", "101", "TST", "Th 7:00PM - 8:50PM", "TBA", "A. Instructor"),
    ]),
]
SECTIONS = [
    ClassSection("1234", "001-LEC Regular", "Open", "TTh 11:30AM - 12:50PM", "MC 2065",
                 "A Very Long Instructor Name Indeed", "01/06/2027 - 04/05/2027", "UW",
                 "120", "100", "20", "0"),
]


class _Session:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


@pytest.fixture(autouse=True)
def stubbed(monkeypatch):
    monkeypatch.setattr(cli, "_build_session", lambda args: _Session())
    monkeypatch.setattr(readers, "schedule", lambda s: SCHEDULE)
    monkeypatch.setattr(readers, "course_availability", lambda s, *a, **kw: SECTIONS)
    monkeypatch.setattr(readers, "available_terms", lambda s: ["Fall 2026", "Winter 2026"])
    monkeypatch.setattr(readers, "dashboard", lambda s: {
        "program": {"plan": "Computer Science", "academic_load": "Full-Time", "campus": "UW"},
        "holds": [], "hold_count": 0,
        "account": [{"term": "Fall 2026", "registered_status": "Fees Arranged",
                     "balance": "0.00"}],
        "next_enrollment": {"session": "Regular", "begins_on": "July 1, 2026"},
        "classes_this_term": 1, "schedule": [c.to_dict() for c in SCHEDULE],
    })


def run(capsys, *argv) -> str:
    assert cli.main(list(argv)) == 0
    return capsys.readouterr().out


def test_status_is_a_human_summary(capsys):
    out = run(capsys, "status")
    assert "Program          Computer Science" in out
    assert "Holds            none" in out
    assert "CS 341" in out and "{" not in out


def test_schedule_renders_each_meeting_without_dict_text(capsys):
    out = run(capsys, "schedule")
    assert "{" not in out and "'" not in out
    assert "LEC 001" in out and "TST 101" in out
    assert max(len(line) for line in out.splitlines()) <= 100


def test_classes_truncates_long_cells_and_shows_seats(capsys):
    out = run(capsys, "classes", "CS", "341", "--seats")
    assert "100/120" in out
    assert "A Very Long In…" in out
    assert max(len(line) for line in out.splitlines()) <= 100


def test_terms_prints_one_per_line(capsys):
    assert run(capsys, "terms").splitlines() == ["Fall 2026", "Winter 2026"]


@pytest.mark.parametrize("argv", [["--json", "status"], ["status", "--json"]])
def test_json_before_or_after_the_subcommand(capsys, argv):
    data = json.loads(run(capsys, *argv))
    assert data["program"]["plan"] == "Computer Science"


def test_json_schedule_keeps_nested_meetings(capsys):
    data = json.loads(run(capsys, "schedule", "--json"))
    assert data[0]["meetings"][1]["component"] == "TST"
