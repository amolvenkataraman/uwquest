# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Amol Venkataraman
"""Offline tests for the session guards: nothing blocked ever reaches the network."""
from importlib import import_module

import pytest

from quest.core.session import READ_ONLY_ACTIONS, CookieSource, QuestSession
from quest.errors import BlockedAction, BlockedComponent

# The reader modules (the package re-exports functions under the same names).
grades = import_module("quest.readers.grades")
course_availability = import_module("quest.readers.course_availability")
transcript = import_module("quest.readers.transcript")


class _NoCookies(CookieSource):
    def load(self) -> list[dict]:
        return []


class _NoHTTP:
    """Fails the test if any request is attempted."""

    def get(self, *a, **kw):
        raise AssertionError("a GET was sent")

    def post(self, *a, **kw):
        raise AssertionError("a POST was sent")

    def close(self) -> None:
        pass


@pytest.fixture
def session():
    s = QuestSession(_NoCookies(), min_delay=0)
    s._http = _NoHTTP()
    return s


@pytest.mark.parametrize(
    ("component", "icaction"),
    [
        (grades.COMPONENT, grades._FALLBACK_GO),
        (course_availability.COMPONENT, course_availability.SEARCH_ACTION),
        (course_availability.COMPONENT, course_availability.BACK_ACTION),
        (course_availability.COMPONENT, "MTG_CLASS_NBR$0"),
        (course_availability.COMPONENT, "MTG_CLASS_NBR$17"),
        (transcript.COMPONENT, transcript.TYPE_FIELD),
        (transcript.COMPONENT, transcript.VIEW_ACTION),
    ],
)
def test_reader_actions_are_allowlisted(component, icaction):
    QuestSession._guard_action(component, icaction)  # does not raise


@pytest.mark.parametrize(
    ("component", "icaction"),
    [
        # enrollment-style actions on an allowlisted component
        (course_availability.COMPONENT, "DERIVED_REGFRM1_LINK_ADD_ENRL$82$"),
        (course_availability.COMPONENT, "DERIVED_REGFRM1_SSR_PB_SUBMIT"),
        (course_availability.COMPONENT, "MTG_CLASS_NBR$1$ADD"),
        (grades.COMPONENT, "DERIVED_SSR_FL_SSR_DROP"),
        (transcript.COMPONENT, "GO2"),
        # a component that has no allowlist at all
        ("SA_LEARNER_SERVICES.SSR_SSENRL_CART.GBL", "DERIVED_REGFRM1_LINK_ADD_ENRL$82$"),
        ("SA_LEARNER_SERVICES.SSR_SSENRL_CART.GBL", "UW_DRVD_SSS_SCT_SSR_PB_GO"),
    ],
)
def test_other_actions_are_refused_before_any_request(session, component, icaction):
    with pytest.raises(BlockedAction):
        session.action(component, icaction)


def test_report_refuses_whole_sequence_up_front(session):
    with pytest.raises(BlockedAction):
        session.report(
            transcript.COMPONENT,
            setup=[(transcript.TYPE_FIELD, {})],
            final=("DERIVED_SSTSRPT_SUBMIT_REQUEST", {}),
        )


def test_icaction_in_get_query_is_refused(session):
    with pytest.raises(BlockedAction):
        session.get(course_availability.COMPONENT, "ICAction=DERIVED_REGFRM1_SSR_PB_SUBMIT")


def test_personal_info_component_is_refused(session):
    with pytest.raises(BlockedComponent):
        session.get("CC_PORTFOLIO.SS_CC_PERSONAL_DATA.GBL")
    with pytest.raises(BlockedComponent):
        session.action("SA_LEARNER_SERVICES.SS_CC_EMAIL_ADDR.GBL", "GO1")


def test_allowlist_covers_only_reader_components():
    assert set(READ_ONLY_ACTIONS) == {
        grades.COMPONENT,
        course_availability.COMPONENT,
        transcript.COMPONENT,
    }


def test_pers_components_are_blocked_too():
    from quest.core.session import _BLOCKED
    assert _BLOCKED.search("CC_PORTFOLIO.SS_CC_PERS_DATA_SUMM.GBL")
    assert not _BLOCKED.search("UW_SS_MENU.UW_SSR_SSENRL_GRDE.GBL")
