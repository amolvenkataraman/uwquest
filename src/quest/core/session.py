# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""The one door to Quest: cookie sources + the PeopleSoft request state machine.

A `QuestSession` loads a cookie session (from a file, or straight from the
browser) and exposes `get`, `action` and `report`. It carries the hidden
`ICStateNum`/`ICSID` form state per component, detects the login redirect, and
refuses any Personal-Information component outright.
"""
from __future__ import annotations

import re
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests

from ..errors import BlockedComponent, QuestError, ReportError, SessionExpired

DEFAULT_BASE = "https://quest.pecs.uwaterloo.ca"
SITE_PATH = "/psc/SS/ACADEMIC/SA"
DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
QUEST_DOMAIN = "pecs.uwaterloo.ca"

# Personal-information components are refused here so nothing downstream can reach
# them, however it is called.
_BLOCKED = re.compile(r"PERSONAL|ADDR|PHONE|EMAIL|EMERG|DISABILITY|ETHNIC|GENDER|DEMOGRAPH", re.I)

_HIDDEN = re.compile(r"<input type='hidden' name='([^']+)' id='[^']*' value='([^']*)'")
_LOGIN_MARKERS = ('name="userid"', "name='userid'", 'name="pwd"', "PT_LOGIN", "PeopleSoft Sign")
_LOGIN_TITLE = re.compile(r"sign\s*-?\s*in|signon", re.I)
_TITLE = re.compile(r"<title>(.*?)</title>", re.I | re.S)


# --------------------------------------------------------------------------
# Cookie sources
# --------------------------------------------------------------------------
class CookieSource(ABC):
    """Produces the cookies for a Quest session as a list of cookie dicts."""

    @abstractmethod
    def load(self) -> list[dict]:
        ...


class FileCookieSource(CookieSource):
    """Cookies exported from the browser to a JSON array (name/value/domain/path)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()

    def load(self) -> list[dict]:
        import json

        with open(self.path) as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"{self.path} is not a JSON array of cookies")
        return data


class BrowserCookieSource(CookieSource):
    """Reads the live Quest session straight from the browser's cookie store.

    No export step: log into Quest in the browser, and this reads its cookies.
    Requires the optional `browser` extra (`pip install uwquest[browser]`).
    """

    def __init__(self, browser: str = "brave", domain: str = QUEST_DOMAIN) -> None:
        self.browser = browser
        self.domain = domain

    def load(self) -> list[dict]:
        try:
            import browser_cookie3
        except ImportError as e:
            raise RuntimeError(
                "reading cookies from the browser needs the 'browser' extra: "
                "pip install uwquest[browser]"
            ) from e
        getter = getattr(browser_cookie3, self.browser, None)
        if getter is None:
            raise ValueError(f"unknown browser {self.browser!r} for browser_cookie3")
        jar = getter(domain_name=self.domain)
        return [
            {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
            for c in jar
        ]


# --------------------------------------------------------------------------
# Session
# --------------------------------------------------------------------------
class QuestSession:
    def __init__(
        self,
        source: CookieSource,
        *,
        base: str = DEFAULT_BASE,
        timeout: float = 30.0,
        min_delay: float = 0.5,
        user_agent: str = DEFAULT_UA,
    ) -> None:
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.min_delay = min_delay
        self._http = requests.Session()
        self._http.headers["User-Agent"] = user_agent
        for c in source.load():
            self._http.cookies.set(
                c["name"], c["value"],
                domain=(c.get("domain") or "").lstrip("."),
                path=c.get("path", "/"),
            )
        self._state: dict[str, dict[str, str]] = {}
        self._last_request = 0.0
        self._lock = threading.RLock()  # serialise requests (one session, one at a time)

    # -- convenience constructors ------------------------------------------
    @classmethod
    def from_file(cls, path: str | Path, **kw) -> QuestSession:
        return cls(FileCookieSource(path), **kw)

    @classmethod
    def from_browser(cls, browser: str = "brave", **kw) -> QuestSession:
        return cls(BrowserCookieSource(browser), **kw)

    # -- low-level ----------------------------------------------------------
    def _component_url(self, component: str) -> str:
        return f"{self.base}{SITE_PATH}/c/{component}"

    def _throttle(self) -> None:
        wait = self.min_delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    @staticmethod
    def _authed(resp: requests.Response) -> bool:
        if "cmd=login" in resp.url or "/signon" in resp.url.lower():
            return False
        title = _TITLE.search(resp.text[:3000])
        if title and _LOGIN_TITLE.search(title.group(1)):
            return False
        return not any(m in resp.text[:6000] for m in _LOGIN_MARKERS)

    def _store_state(self, component: str, html: str) -> None:
        fields = dict(_HIDDEN.findall(html))
        if "ICStateNum" in fields:
            self._state[component] = fields

    def _guard(self, component: str) -> None:
        if _BLOCKED.search(component):
            raise BlockedComponent(
                f"{component} is a Personal-Information component and is blocked."
            )

    # -- public requests ----------------------------------------------------
    def get(self, component: str, query: str = "") -> str:
        """GET a component page; refresh its form state; return HTML."""
        self._guard(component)
        with self._lock:
            self._throttle()
            url = self._component_url(component) + (f"?{query}" if query else "")
            try:
                resp = self._http.get(url, timeout=self.timeout)
            except requests.RequestException as e:
                raise QuestError(f"network error contacting Quest: {e}") from e
            if not self._authed(resp):
                raise SessionExpired()
            self._store_state(component, resp.text)
            return resp.text

    def action(self, component: str, icaction: str, fields: dict | None = None) -> str:
        """POST an ICAction against the component, carrying its stored form state."""
        self._guard(component)
        with self._lock:
            state = self._state.get(component)
            if state is None:
                self.get(component)
                state = self._state.get(component, {})
            form = dict(state)
            form.update(fields or {})
            form["ICAction"] = icaction
            self._throttle()
            try:
                resp = self._http.post(
                    self._component_url(component), data=form, timeout=self.timeout
                )
            except requests.RequestException as e:
                raise QuestError(f"network error contacting Quest: {e}") from e
            if not self._authed(resp):
                raise SessionExpired()
            self._store_state(component, resp.text)
            return resp.text

    def report(
        self, component: str, setup: list[tuple[str, dict]], final: tuple[str, dict]
    ) -> bytes:
        """Run a report-generation sequence and download the resulting PDF bytes."""
        with self._lock:
            self.get(component)
            for icaction, fields in setup:
                self.action(component, icaction, fields)
            html = self.action(component, final[0], final[1])
            m = re.search(r"https://[^'\"\s]+/psc/[^'\"\s]+/view/[^'\"\s]+", html)
            if not m:
                raise ReportError("report generated but no download link was found")
            self._throttle()
            resp = self._http.get(m.group(0), timeout=max(self.timeout, 60))
            if resp.content[:4] != b"%PDF":
                raise ReportError("report link did not return a PDF")
            return resp.content

    # -- lifecycle ----------------------------------------------------------
    def heartbeat(self) -> bool:
        """Touch a cheap page to slide the session's expiry. Returns True if alive."""
        try:
            self.get("NUI_FRAMEWORK.PT_LANDINGPAGE.GBL", "page=PT_LANDINGPAGE")
            return True
        except SessionExpired:
            return False

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> QuestSession:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
