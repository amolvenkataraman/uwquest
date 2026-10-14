# uwquest

A read-first command-line tool and Python client for **UWaterloo Quest**
(the university's PeopleSoft student self-service system).

> [!WARNING]
> **Provided AS IS, with no warranty and no liability. Written with AI assistance.**
> Unofficial and not affiliated with the University of Waterloo. Use only on your
> own account, at a modest request rate, and check UW's acceptable-use policy for
> automated access. Read [DISCLAIMER.md](DISCLAIMER.md) before use.

It logs in with a browser cookie session (Quest uses SSO + Duo, which you do once
in your browser) and reads your own records into plain data — no enrolling, no
payments, and Personal-Information pages are blocked in code.

## Install

```bash
git clone https://github.com/amolvenkataraman/uwquest && cd uwquest
uv tool install .                 # base (file-based cookies)
uv tool install '.[browser]'      # also read cookies live from the browser
```

## Cookies

Log into Quest in your browser, then either:

- **Export** the `pecs.uwaterloo.ca` cookies to JSON and point the tool at it
  (`--cookies-file path.json`, or put it at `~/.config/quest/cookies.json`), or
- **Read them live** from the browser: `quest --browser brave holds`.

The session slides while you use it, so repeated commands keep it alive until
UW's SSO cap; when it expires the tool tells you to log in again.

## Usage

```bash
quest status                      # one-screen summary: program, balance, holds, next enrollment
quest schedule                    # enrolled classes this term
quest grades --term "Winter 2026" # grades (defaults to the latest term)
quest terms                       # term labels available for grades
quest account                     # per-term registration status and balance
quest holds                       # service indicators
quest milestones                  # requirements, scholarships
quest program                     # plan, academic load, campus
quest enrollment-dates            # when enrollment opens
quest financial-aid               # aid years on record
quest classes MATH 135            # course availability (status per section, no enrolling)
quest classes CS 486 --seats      # also fetch seat counts (slower)
quest classes PMATH --open-only   # whole subject, open sections only
quest transcript -o transcript.pdf  # download the unofficial transcript PDF
quest --json schedule             # machine-readable, on any command
quest tui                         # interactive terminal UI (needs the 'tui' extra)
```

The transcript PDF is only *fetched* here; parsing it (GPA, averages, standing)
is a separate service. `academic-requirements` is experimental (UW renders that
report dynamically).

## Terminal UI

`quest tui` opens a tabbed interface — Dashboard, Schedule, Grades (type a term),
Account, Holds, and a Classes browser with coloured Open/Closed/Waitlist status.
Install it with the `tui` extra.

## Status

Working: the session layer (file + browser cookies, the PeopleSoft request state
machine, keep-alive, a Personal-Information blocklist) and readers for status,
schedule, grades, account, holds, milestones, program, enrollment dates, financial
aid, course availability (with seat counts), and the transcript PDF, plus a
Textual TUI. All read-only; writes (enrollment) are intentionally not implemented.

## Development

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/pytest
```

## License

MIT © 2026 Amol Venkataraman. Provided WITHOUT ANY WARRANTY — see [LICENSE](LICENSE)
and [DISCLAIMER.md](DISCLAIMER.md). Not affiliated with or endorsed by the
University of Waterloo or Oracle. "Quest" and "PeopleSoft" are used only to
describe compatibility.
