"""The per-item freshness gate.

The person-specific caution gate around ブルーノ・プラス was removed 2026-07-21
(Emma: "he's not the threat that we think he is … I thought we did, but we
didn't"), and its tests went with it. What remains is the general rule: never
edit an item another human touched inside the quiet window.

The property pinned hardest: the gate must never block on OUR own edits, or the
drip deadlocks itself after its first edit to any item.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import conflict_gate as cg  # noqa: E402

D = datetime.date
TODAY = D(2026, 7, 10)


# ─────────────────────── per-item freshness ───────────────────────

def test_item_touched_by_another_user_yesterday_is_blocked():
    assert not cg.is_item_fresh_enough([("SomeEditor", D(2026, 7, 9))], TODAY)


def test_item_touched_by_another_user_eight_days_ago_is_allowed():
    assert cg.is_item_fresh_enough([("SomeEditor", D(2026, 7, 2))], TODAY)


def test_our_own_recent_edits_never_block_us():
    """Otherwise the drip deadlocks itself the day after its first edit."""
    revs = [("Immanuelle", TODAY), ("EmmaBot", TODAY)]
    assert cg.is_item_fresh_enough(revs, TODAY)


def test_our_edit_does_not_mask_a_foreign_one():
    revs = [("Immanuelle", TODAY), ("SomeoneElse", D(2026, 7, 8))]
    assert not cg.is_item_fresh_enough(revs, TODAY)


def test_exactly_seven_days_ago_is_outside_the_window():
    revs = [("Someone", TODAY - datetime.timedelta(days=7))]
    assert cg.is_item_fresh_enough(revs, TODAY)


def test_six_days_ago_is_inside_the_window():
    revs = [("Someone", TODAY - datetime.timedelta(days=6))]
    assert not cg.is_item_fresh_enough(revs, TODAY)


def test_item_with_no_revisions_is_fresh():
    assert cg.is_item_fresh_enough([], TODAY)


def test_blocking_editor_names_the_most_recent_foreigner():
    revs = [("Immanuelle", TODAY), ("A", D(2026, 7, 5)), ("B", D(2026, 7, 8))]
    user, when = cg.blocking_editor(revs, TODAY)
    assert user == "B" and when == D(2026, 7, 8)


def test_blocking_editor_is_none_when_fresh():
    assert cg.blocking_editor([("Immanuelle", TODAY)], TODAY) is None


# ─────────────────────── policy constants ───────────────────────

def test_policy_constants_match_emmas_instruction():
    assert cg.QUIET_DAYS == 7
    assert cg.OUR_ACCOUNTS == {"Immanuelle", "EmmaBot"}


def test_the_person_specific_gate_is_gone():
    """Regression guard: the global pause must not creep back in silently."""
    for removed in ("WATCHED_USER", "MIN_PAUSE_UNTIL", "HARD_RESUME",
                    "should_run", "pause_reason", "resume_date",
                    "ATTENTION_PAUSE_DAYS"):
        assert not hasattr(cg, removed), removed
