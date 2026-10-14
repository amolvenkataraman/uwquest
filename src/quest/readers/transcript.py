# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Unofficial transcript: fetch the PDF only.

This client retrieves the PDF and hands it off; parsing it into structured data
(GPA, averages, standing, course history) is a separate microservice.
"""
from __future__ import annotations

import re

from ..core.session import QuestSession
from ..errors import ReportError

COMPONENT = "SA_LEARNER_SERVICES.SSS_TSRQST_UNOFF.GBL"
INSTITUTION_FIELD = "SA_REQUEST_HDR_INSTITUTION"
TYPE_FIELD = "DERIVED_SSTSRPT_TSCRPT_TYPE3"
VIEW_ACTION = "GO1"
DEFAULT_TYPE = "Undergrad Unofficial"


def _option_value(html: str, select_name: str, label_contains: str) -> str | None:
    sel = re.search(rf"name=['\"]{re.escape(select_name)}['\"](.*?)</select>", html, re.S)
    if not sel:
        return None
    opts = re.findall(r"<option[^>]*value=['\"]([^'\"]*)['\"][^>]*>([^<]*)</option>", sel.group(1))
    for value, label in opts:
        if label_contains.lower() in label.lower():
            return value
    return None


def transcript_pdf(session: QuestSession, report_type: str = DEFAULT_TYPE) -> bytes:
    """Generate the unofficial transcript and return the raw PDF bytes."""
    html = session.get(COMPONENT)
    institution = _option_value(html, INSTITUTION_FIELD, "Waterloo")
    type_value = _option_value(html, TYPE_FIELD, report_type)
    if institution is None or type_value is None:
        raise ReportError(
            f"could not find the institution or a {report_type!r} report type on the page"
        )
    fields = {INSTITUTION_FIELD: institution, TYPE_FIELD: type_value}
    return session.report(COMPONENT, setup=[(TYPE_FIELD, fields)], final=(VIEW_ACTION, fields))
