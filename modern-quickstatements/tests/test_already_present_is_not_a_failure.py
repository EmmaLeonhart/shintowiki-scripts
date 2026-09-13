"""Wikidata refusing an already-present qualifier is not a failure of the drip.

`wbsetqualifier` and `wbsetreference` return an ERROR when the qualifier or
reference is already on the statement. For a drip that samples 500 lines a day
out of ~117,000, that is not a failure: the line's work is done, and the same
line will be drawn again and "fail" again, forever.

Measured on the 2026-09-12 run — 501 attempts, 26 reported failures, and **23 of
the 26** were "The statement has already a qualifier with hash …". Three were
real. A run that reports 26 failures when it has 3 teaches everyone to ignore the
number.

Matched on the message, not the error code: `modification-failed` covers
genuinely different refusals, and only this text means "already there".
"""

import os
import sys

import pytest

MQ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MQ)

from direct_daily_edits import is_already_present  # noqa: E402


@pytest.mark.parametrize("info", [
    "The statement has already a qualifier with hash 3b2f32c96d0b02a0aa0a67aeb7fa4d1",
    "The statement has already a reference with hash e0e0fc0dcfce9c6bf0db4b8b58d24",
    "the statement has ALREADY A QUALIFIER WITH HASH abc",
])
def test_already_present_refusals_are_recognised(info):
    assert is_already_present(info)


@pytest.mark.parametrize("info", [
    "The save has failed.",
    "Invalid snak value",
    "You do not have permission to edit this page",
    "The statement has already been removed",
    "",
])
def test_real_failures_are_still_failures(info):
    """The point of matching the text rather than the error code. Anything that
    is not specifically 'already there' must keep reporting failure — including
    'already been removed', which is a different situation."""
    assert not is_already_present(info)


def test_none_is_not_a_success():
    assert not is_already_present(None)


def test_both_call_sites_consult_it():
    """A predicate nothing calls is decoration."""
    src = open(os.path.join(MQ, "direct_daily_edits.py"), encoding="utf-8").read()
    assert src.count("if is_already_present(info):") == 2, (
        "expected the qualifier and reference paths both to use it")
    for phrase in ('return True, "Qualifier already present"',
                   'return True, "Reference already present"'):
        assert phrase in src
