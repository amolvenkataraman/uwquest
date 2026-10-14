# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Command-line interface. Read-only; prints tables or JSON."""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys

from . import __version__, readers
from .core.session import BrowserCookieSource, FileCookieSource, QuestSession
from .errors import QuestError

DEFAULT_COOKIES = os.path.expanduser(
    os.environ.get("QUEST_COOKIES", "~/.config/quest/cookies.json")
)


def _build_session(args) -> QuestSession:
    if args.browser:
        source = BrowserCookieSource(args.browser)
    else:
        path = args.cookies_file or DEFAULT_COOKIES
        if not os.path.exists(path):
            sys.exit(
                f"error: no cookies file at {path}. Export Quest cookies there, pass "
                "--cookies-file PATH, or use --browser brave to read them live."
            )
        source = FileCookieSource(path)
    return QuestSession(source, base=args.base)


def _emit(data, as_json: bool) -> None:
    def norm(x):
        if dataclasses.is_dataclass(x) and not isinstance(x, type):
            return dataclasses.asdict(x)
        return x

    rows = [norm(x) for x in data] if isinstance(data, list) else norm(data)
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print("(nothing to show)")
        return
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        cols = list(rows[0].keys())
        widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
        print("  ".join(c.ljust(widths[c]) for c in cols))
        print("  ".join("-" * widths[c] for c in cols))
        for r in rows:
            print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))
    else:
        print(json.dumps(rows, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quest", description="Read-first client for UWaterloo Quest.")
    p.add_argument("--version", action="version", version=f"quest {__version__}")
    p.add_argument("--cookies-file", help=f"exported cookies JSON (default {DEFAULT_COOKIES})")
    p.add_argument("--browser", help="read the live session from this browser instead (e.g. brave)")
    p.add_argument("--base", default="https://quest.pecs.uwaterloo.ca", help="Quest base URL")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, help_text in [
        ("status", "one-screen summary (program, balance, holds, next enrollment)"),
        ("holds", "holds / service indicators"),
        ("account", "per-term registration status and balance"),
        ("schedule", "enrolled classes for the current term"),
        ("milestones", "milestones (requirements, scholarships)"),
        ("program", "plan, academic load, campus"),
        ("enrollment-dates", "when enrollment opens"),
        ("financial-aid", "financial aid years on record"),
        ("academic-requirements", "advisement report (experimental)"),
        ("terms", "term labels available for grades"),
    ]:
        sub.add_parser(name, help=help_text)
    g = sub.add_parser("grades", help="grades for a term (defaults to most recent)")
    g.add_argument("--term", help="e.g. 'Winter 2026' (see `quest terms`)")
    cs = sub.add_parser("classes", help="course availability / class search (no enrollment)")
    cs.add_argument("subject", help="subject code, e.g. MATH")
    cs.add_argument("catalog_nbr", nargs="?", help="course number, e.g. 135")
    cs.add_argument("--term", help="e.g. 'Fall 2026' (defaults to the first offered)")
    cs.add_argument("--open-only", action="store_true", help="only sections with seats open")
    cs.add_argument("--seats", action="store_true", help="also fetch seat counts (slower)")
    tr = sub.add_parser("transcript", help="download the unofficial transcript PDF")
    tr.add_argument("-o", "--output", required=True, help="write the PDF to this path")
    tr.add_argument("--type", default="Undergrad Unofficial", help="report type")
    sub.add_parser("tui", help="launch the terminal UI (needs the 'tui' extra)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    name = args.cmd.replace("-", "_")
    reader_name = {
        "terms": "available_terms",
        "classes": "course_availability",
        "status": "dashboard",
        "transcript": "transcript_pdf",
    }.get(name, name)
    if name == "tui":
        try:
            from .tui import run
        except ImportError:
            sys.exit("error: the TUI needs the 'tui' extra: pip install 'uwquest[tui]'")
        run(_build_session(args))
        return 0
    reader = getattr(readers, reader_name)
    try:
        with _build_session(args) as session:
            if name == "grades":
                data = reader(session, args.term)
            elif name == "classes":
                data = reader(
                    session, args.subject, args.catalog_nbr,
                    term=args.term, open_only=args.open_only, with_seats=args.seats,
                )
            elif name == "transcript":
                pdf = reader(session, args.type)
                with open(args.output, "wb") as f:
                    f.write(pdf)
                print(f"wrote {len(pdf)} bytes to {args.output}")
                return 0
            else:
                data = reader(session)
    except QuestError as e:
        sys.exit(f"error: {e}")
    _emit(data, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
