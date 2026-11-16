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


def _norm(x):
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        return dataclasses.asdict(x)
    return x


def _cut(text: str, width: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


def _table(headers: list[str], rows: list[list], max_widths: list[int] | None = None) -> str:
    """Plain aligned columns; cells longer than their max width are cut with '…'."""
    max_widths = max_widths or [10_000] * len(headers)
    cells = [[_cut(v, m) for v, m in zip(r, max_widths, strict=True)] for r in rows]
    widths = [max(len(h), *(len(r[i]) for r in cells)) for i, h in enumerate(headers)]
    lines = ["  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)),
             "  ".join("-" * w for w in widths)]
    lines += ["  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)) for r in cells]
    return "\n".join(line.rstrip() for line in lines)


def _split_course(course: str) -> tuple[str, str]:
    code, _, title = course.partition(" - ")
    return code.strip(), title.strip()


def _format_status(d: dict) -> str:
    p = d.get("program") or {}
    ne = d.get("next_enrollment") or {}
    holds = d.get("holds") or []
    load = ", ".join(x for x in (p.get("academic_load"), p.get("campus")) if x)
    hold_text = "none" if not holds else f"{len(holds)}: " + "; ".join(
        h.get("reason", "") for h in holds
    )
    nxt = ", ".join(x for x in (ne.get("session"), ne.get("begins_on")) if x) or "-"
    lines = [
        f"{'Program':<17}{p.get('plan', '')}",
        f"{'Load':<17}{load}",
        f"{'Holds':<17}{hold_text}",
        f"{'Next enrollment':<17}{nxt}",
        "",
        f"This term: {d.get('classes_this_term', 0)} classes",
    ]
    for c in d.get("schedule") or []:
        code, title = _split_course(c.get("course", ""))
        lines.append(f"  {code:<10} {_cut(title, 40):<40} {c.get('status', '')}")
    lines += ["", "Account (latest terms)"]
    for a in (d.get("account") or [])[:4]:
        lines.append(f"  {a['term']:<14} {a['registered_status']:<18} {a['balance']:>10}")
    return "\n".join(lines)


def _format_schedule(classes: list[dict]) -> str:
    rows = []
    for c in classes:
        code, title = _split_course(c.get("course", ""))
        for n, m in enumerate(c.get("meetings") or [{}]):
            first = n == 0
            rows.append([
                code if first else "", title if first else "",
                f"{m.get('component', '')} {m.get('section', '')}".strip(),
                m.get("days_times", ""), m.get("room", ""), m.get("instructor", ""),
                c.get("status", "") if first else "",
            ])
    return _table(
        ["Course", "Title", "Class", "Days/Times", "Room", "Instructor", "Status"],
        rows, [9, 15, 7, 21, 13, 15, 9],
    )


def _format_classes(sections: list[dict]) -> str:
    seats = any(s.get("enrollment_cap") for s in sections)
    headers = ["Class", "Section", "Status", "Days/Times", "Room", "Instructor"]
    widths = [5, 15, 9, 21, 9, 18]
    if seats:
        headers += ["Enrl", "Wait"]
        widths = [5, 15, 9, 21, 9, 15, 7, 4]
    rows = []
    for s in sections:
        row = [s.get("class_nbr", ""), s.get("section", ""), s.get("status", ""),
               s.get("days_time", ""), s.get("room", ""), s.get("instructor", "")]
        if seats:
            enrl = f"{s.get('enrollment_total', '')}/{s.get('enrollment_cap', '')}"
            row += [enrl if enrl != "/" else "", s.get("waitlist_total", "")]
        rows.append(row)
    return _table(headers, rows, widths)


_FORMATTERS = {"status": _format_status, "schedule": _format_schedule,
               "classes": _format_classes}


def _emit(data, as_json: bool, cmd: str = "") -> None:
    rows = [_norm(x) for x in data] if isinstance(data, list) else _norm(data)
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print("(nothing to show)")
        return
    if cmd in _FORMATTERS:
        print(_FORMATTERS[cmd](rows))
    elif isinstance(rows, list) and isinstance(rows[0], dict):
        cols = list(rows[0].keys())
        print(_table(cols, [[r.get(c, "") for c in cols] for r in rows]))
    elif isinstance(rows, list):
        print("\n".join(str(r) for r in rows))
    else:
        print(json.dumps(rows, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quest", description="Read-first client for UWaterloo Quest.")
    p.add_argument("--version", action="version", version=f"quest {__version__}")
    p.add_argument("--cookies-file", help=f"exported cookies JSON (default {DEFAULT_COOKIES})")
    p.add_argument("--browser", help="read the live session from this browser instead (e.g. brave)")
    p.add_argument("--base", default="https://quest.pecs.uwaterloo.ca", help="Quest base URL")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    # --json also works after the subcommand; SUPPRESS keeps it from resetting the global one.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="machine-readable output")
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
        sub.add_parser(name, help=help_text, parents=[common])
    g = sub.add_parser(
        "grades", help="grades for a term (defaults to most recent)", parents=[common]
    )
    g.add_argument("--term", help="e.g. 'Winter 2026' (see `quest terms`)")
    cs = sub.add_parser(
        "classes", help="course availability / class search (no enrollment)", parents=[common]
    )
    cs.add_argument("subject", help="subject code, e.g. MATH")
    cs.add_argument("catalog_nbr", nargs="?", help="course number, e.g. 135")
    cs.add_argument("--term", help="e.g. 'Fall 2026' (defaults to the first offered)")
    cs.add_argument("--open-only", action="store_true", help="only sections with seats open")
    cs.add_argument("--seats", action="store_true", help="also fetch seat counts (slower)")
    tr = sub.add_parser(
        "transcript", help="download the unofficial transcript PDF", parents=[common]
    )
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
                if args.json:
                    print(json.dumps({"path": args.output, "bytes": len(pdf)}))
                else:
                    print(f"wrote {len(pdf)} bytes to {args.output}")
                return 0
            else:
                data = reader(session)
    except QuestError as e:
        sys.exit(f"error: {e}")
    _emit(data, args.json, name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
