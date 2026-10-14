# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Headless smoke test: the TUI mounts and renders with stubbed readers."""
import pytest

pytest.importorskip("textual")

from quest.core.models import AccountTerm, Meeting, ScheduleClass
from quest.tui.app import QuestApp


class _StubSession:
    """Stands in for QuestSession; readers are patched so it's never used."""


@pytest.fixture
def patched(monkeypatch):
    from quest import readers

    monkeypatch.setattr(readers, "dashboard", lambda s: {
        "program": {"plan": "Computer Science", "academic_load": "Full", "campus": "UW"},
        "holds": [], "hold_count": 0,
        "account": [{"term": "Fall 2026", "registered_status": "Registered", "balance": "0.00"}],
        "next_enrollment": {"session": "Regular", "begins_on": "July 1"},
        "classes_this_term": 1, "schedule": [],
    })
    monkeypatch.setattr(readers, "schedule", lambda s: [
        ScheduleClass(course="CS 341", status="Enrolled", units="0.50",
                      meetings=[Meeting(section="001", component="LEC", room="MC 4020")]),
    ])
    acct = [AccountTerm("Fall 2026", "Registered", "0.00")]
    monkeypatch.setattr(readers, "account", lambda s: acct)
    monkeypatch.setattr(readers, "holds", lambda s: [])


async def test_app_mounts_and_loads(patched):
    app = QuestApp(_StubSession())
    async with app.run_test() as pilot:
        await pilot.pause()
        await app.workers.wait_for_complete()
        await pilot.pause()
        from textual.widgets import Static

        body = app.query_one("#dash_body", Static)
        assert "Computer Science" in str(body.render())
