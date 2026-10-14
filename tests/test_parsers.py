# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Parser tests on synthetic PeopleSoft-style grids (no real records)."""
from quest.core.parsers import find_message, first_grid_rows, page_title
from quest.core.session import _BLOCKED

GRID = """
<html><head><title>Account Summary</title></head><body>
<table class="PSLEVEL1GRIDWBO">
  <tr><th class="PSLEVEL1GRIDCOLUMNHDR">Term</th>
      <th class="PSLEVEL1GRIDCOLUMNHDR">Registered Status</th>
      <th class="PSLEVEL1GRIDCOLUMNHDR">Term Balance</th></tr>
  <tr><td><span>Fall 2026</span></td><td><span>Registered</span></td>
      <td><span>0.00</span></td></tr>
  <tr><td><span>Winter 2026</span></td><td><span>Registered</span></td>
      <td><span>123.45</span></td></tr>
</table></body></html>
"""

EMPTY_HOLDS = "<html><body><span>There are no current holds.</span></body></html>"


def test_page_title():
    assert page_title(GRID) == "Account Summary"


def test_parse_grid_headers_to_rows():
    rows = first_grid_rows(GRID)
    assert len(rows) == 2
    assert rows[0] == {
        "Term": "Fall 2026", "Registered Status": "Registered", "Term Balance": "0.00",
    }
    assert rows[1]["Term Balance"] == "123.45"


def test_find_empty_message():
    assert find_message(EMPTY_HOLDS, [r"There are no (?:current )?holds[^<.]*"])
    assert find_message(GRID, [r"There are no holds"]) is None


def test_personal_info_blocklist():
    assert _BLOCKED.search("SA_LEARNER_SERVICES.SCC_SS_PERSONAL.GBL")
    assert _BLOCKED.search("UW_SS_EMERG_CNTCT.GBL")
    assert not _BLOCKED.search("CC_PORTFOLIO.SS_CC_HOLDS.GBL")
