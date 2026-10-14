# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Exception types, each with a plain-language message."""
from __future__ import annotations


class QuestError(Exception):
    """Base class for everything this package raises."""


class SessionExpired(QuestError):
    """The cookie session is no longer valid (Quest redirected to login)."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            message
            or "Quest session expired. Log in again in your browser and re-export "
            "(or re-read) the cookies, then retry."
        )


class NotAuthorized(QuestError):
    """Quest served the page but refused access to it."""


class BlockedComponent(QuestError):
    """A component on the personal-information blocklist was requested."""


class ParseError(QuestError):
    """A page loaded but did not have the structure the parser expected."""


class ReportError(QuestError):
    """A report (PDF) could not be generated or retrieved."""
