# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""A Textual terminal UI over the readers.

Thin layer: every panel calls a reader in a worker thread (so the async UI never
blocks) and the session's lock keeps requests one-at-a-time. No Quest logic lives
here.
"""
from __future__ import annotations

from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Static,
    TabbedContent,
    TabPane,
)

from .. import readers
from ..core.session import QuestSession

_STATUS_COLOR = {"Open": "green", "Closed": "red"}


def _status_markup(status: str) -> str:
    if status.startswith("Wait"):
        return f"[yellow]{status}[/]"
    return f"[{_STATUS_COLOR.get(status, 'dim')}]{status or '?'}[/]"


class QuestApp(App):
    TITLE = "Quest"
    CSS = """
    #dash_body, #holds_body { padding: 1 2; }
    .bar { height: auto; padding: 1 1 0 1; }
    .bar Input { width: 1fr; margin-right: 1; }
    .bar Button { width: auto; }
    DataTable { height: 1fr; }
    """
    BINDINGS: ClassVar = [("r", "refresh", "Refresh"), ("q", "quit", "Quit")]

    def __init__(self, session: QuestSession) -> None:
        super().__init__()
        self.session = session
        self._loaded: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="dashboard"):
            with TabPane("Dashboard", id="dashboard"):
                yield VerticalScroll(Static("Loading…", id="dash_body"))
            with TabPane("Schedule", id="schedule"):
                yield DataTable(id="sched_table")
            with TabPane("Grades", id="grades"):
                with Horizontal(classes="bar"):
                    yield Input(placeholder="Term e.g. Winter 2026", id="grades_term")
                    yield Button("Load", id="grades_load", variant="primary")
                yield DataTable(id="grades_table")
            with TabPane("Account", id="account"):
                yield DataTable(id="account_table")
            with TabPane("Holds", id="holds"):
                yield VerticalScroll(Static("Loading…", id="holds_body"))
            with TabPane("Classes", id="classes"):
                with Horizontal(classes="bar"):
                    yield Input(placeholder="Subject (MATH)", id="cls_subject")
                    yield Input(placeholder="Number (135)", id="cls_catalog")
                    yield Input(placeholder="Term (blank = default)", id="cls_term")
                    yield Button("Search", id="cls_search", variant="primary")
                yield DataTable(id="classes_table")
        yield Footer()

    _LOADERS = ("schedule", "account", "holds")  # tabs that auto-load when opened

    def on_mount(self) -> None:
        self.load_dashboard()
        self._loaded.add("dashboard")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        active = self.query_one(TabbedContent).active
        if active in self._loaded or active not in self._LOADERS:
            return
        self._loaded.add(active)
        getattr(self, f"load_{active}")()

    def action_refresh(self) -> None:
        active = self.query_one(TabbedContent).active
        self._loaded = {"dashboard"}
        self.load_dashboard()
        if active in self._LOADERS:
            self._loaded.add(active)
            getattr(self, f"load_{active}")()

    # -- helpers run on the UI thread --------------------------------------
    def _set_text(self, selector: str, text: str) -> None:
        # All DOM access must run on the UI thread, inside the callback.
        def do() -> None:
            self.query_one(selector, Static).update(text)
        self.call_from_thread(do)

    def _fill_table(self, selector: str, columns: list[str], rows: list[list]) -> None:
        def do() -> None:
            table = self.query_one(selector, DataTable)
            table.clear(columns=True)
            table.add_columns(*columns)
            for row in rows:
                table.add_row(*row)
        self.call_from_thread(do)

    # -- workers (run in threads; session lock serialises requests) --------
    @work(thread=True, group="io")
    def load_dashboard(self) -> None:
        self._set_text("#dash_body", "Loading…")
        try:
            d = readers.dashboard(self.session)
        except Exception as e:  # noqa: BLE001 -- show any failure in the panel, never hang
            self._set_text("#dash_body", f"[red]{e}[/]")
            return
        p = d["program"]
        ne = d.get("next_enrollment") or {}
        lines = [
            f"[b]Program[/b]   {p.get('plan', '')}",
            f"[b]Load[/b]      {p.get('academic_load', '')}    [b]Campus[/b] {p.get('campus', '')}",
            "",
            f"[b]Holds[/b]     {d['hold_count']}",
            f"[b]Classes[/b]   {d['classes_this_term']} this term",
            f"[b]Next enrollment[/b]  {ne.get('session', '-')}  {ne.get('begins_on', '')}",
            "",
            "[b]Account[/b]",
        ]
        for a in d["account"][:6]:
            lines.append(f"  {a['term']:<16} {a['registered_status']:<16} {a['balance']}")
        self._set_text("#dash_body", "\n".join(lines))

    @work(thread=True, group="io")
    def load_schedule(self) -> None:
        self._fill_table("#sched_table", ["status"], [["Loading…"]])
        try:
            classes = readers.schedule(self.session)
        except Exception as e:  # noqa: BLE001 -- show any failure in the panel, never hang
            self._fill_table("#sched_table", ["error"], [[str(e)]])
            return
        rows = []
        for c in classes:
            m = c.meetings[0] if c.meetings else None
            rows.append([
                c.course, c.status, c.units,
                m.section if m else "", m.component if m else "",
                m.days_times if m else "", m.room if m else "", m.instructor if m else "",
            ])
        self._fill_table(
            "#sched_table",
            ["Course", "Status", "Units", "Sect", "Comp", "Days/Times", "Room", "Instructor"],
            rows,
        )

    @work(thread=True, group="io")
    def load_account(self) -> None:
        self._fill_table("#account_table", ["status"], [["Loading…"]])
        try:
            terms = readers.account(self.session)
        except Exception as e:  # noqa: BLE001 -- show any failure in the panel, never hang
            self._fill_table("#account_table", ["error"], [[str(e)]])
            return
        self._fill_table(
            "#account_table",
            ["Term", "Registered Status", "Balance"],
            [[a.term, a.registered_status, a.balance] for a in terms],
        )

    @work(thread=True, group="io")
    def load_holds(self) -> None:
        try:
            hold_list = readers.holds(self.session)
        except Exception as e:  # noqa: BLE001 -- show any failure in the panel, never hang
            self._set_text("#holds_body", f"[red]{e}[/]")
            return
        if not hold_list:
            self._set_text("#holds_body", "[green]No holds.[/]")
            return
        self._set_text(
            "#holds_body",
            "\n".join(f"• [b]{h.reason}[/b] — {h.department} {h.detail}" for h in hold_list),
        )

    @work(thread=True, group="io", exclusive=True)
    def load_grades(self, term: str) -> None:
        self._fill_table("#grades_table", ["status"], [["Loading…"]])
        try:
            rows = readers.grades(self.session, term or None)
        except Exception as e:  # noqa: BLE001 -- show any failure in the panel, never hang
            self._fill_table("#grades_table", ["error"], [[str(e)]])
            return
        self._fill_table(
            "#grades_table",
            ["Course", "Description", "Units", "Grading", "Grade"],
            [[g.course, g.description, g.units, g.grading, g.grade] for g in rows],
        )

    @work(thread=True, group="io", exclusive=True)
    def load_classes(self, subject: str, catalog: str, term: str) -> None:
        self._fill_table("#classes_table", ["status"], [["Searching…"]])
        try:
            sections = readers.course_availability(
                self.session, subject, catalog or None, term=term or None
            )
        except Exception as e:  # noqa: BLE001 -- show any failure in the panel, never hang
            self._fill_table("#classes_table", ["error"], [[str(e)]])
            return
        from rich.text import Text

        rows = [
            [
                s.section,
                Text.from_markup(_status_markup(s.status)),
                s.days_time,
                s.room,
                s.instructor,
                s.class_nbr,
            ]
            for s in sections
        ]
        self._fill_table(
            "#classes_table",
            ["Section", "Status", "Days/Times", "Room", "Instructor", "Class#"],
            rows,
        )

    # -- events ------------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "grades_load":
            self.load_grades(self.query_one("#grades_term", Input).value.strip())
        elif event.button.id == "cls_search":
            self.load_classes(
                self.query_one("#cls_subject", Input).value.strip(),
                self.query_one("#cls_catalog", Input).value.strip(),
                self.query_one("#cls_term", Input).value.strip(),
            )


def run(session: QuestSession) -> None:
    QuestApp(session).run()
