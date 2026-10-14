# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""uwquest: a read-first client for UWaterloo Quest (PeopleSoft) self-service.

The session layer loads a browser cookie session and drives the PeopleSoft
component/ICAction state machine; readers turn pages into plain dataclasses.
Nothing here enrolls, pays, or touches Personal Information.
"""

__version__ = "0.1.0"

from .core.session import (
    BrowserCookieSource,
    FileCookieSource,
    QuestSession,
)
from .errors import (
    NotAuthorized,
    QuestError,
    SessionExpired,
)

__all__ = [
    "BrowserCookieSource",
    "FileCookieSource",
    "NotAuthorized",
    "QuestError",
    "QuestSession",
    "SessionExpired",
]
