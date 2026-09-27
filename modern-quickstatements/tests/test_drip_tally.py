"""The drip's per-file tally separates real landings from lines that were already there.

2026-09-26: the run logged 36 "succeeded" and the account made zero edits; every one
was a skip of something already present. The tally must not count those as landed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("WIKIDATA_EMAIL", "test@example.org")
os.environ.setdefault("MIRAHEZE_EMAIL", "test@example.org")

import direct_daily_edits as d  # noqa: E402


def test_real_landings_count_as_landed():
    for msg in ("Created", "Done", "Removed", "Qualifier added", "Reference added", "wbsetlabel en='X'"):
        assert d.tally_outcome(True, msg) == "landed", msg


def test_already_there_is_not_a_landing():
    for msg in ("Skipped (already exists)", "Qualifier already present", "Reference already present"):
        assert d.tally_outcome(True, msg) == "already", msg
    assert d.tally_outcome(False, d.CLAIM_ABSENT_MSG) == "already"


def test_errors_are_failures():
    assert d.tally_outcome(False, "API error: The save has failed. [failed-save]") == "failed"
