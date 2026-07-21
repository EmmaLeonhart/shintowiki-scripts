"""The caution gate around ブルーノ・プラス (Emma 2026-07-10).

Two properties matter most and are pinned hardest:

  * while the watched editor keeps editing, the pause keeps extending;
  * but the HARD CAP still opens the drip on 2026-08-08, because otherwise an
    editor who never stops would hold a permanent veto over our pipeline.

And the per-item gate must never block on OUR own edits, or the drip deadlocks
itself after its first edit to any item.
"""
import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import conflict_gate as cg  # noqa: E402

D = datetime.date


# ─────────────────────── global pause ───────────────────────

def test_hard_cap_opens_the_gate_even_if_they_never_stop():
    """The load-bearing one: no editor gets a permanent veto.

    Emma moved HARD_RESUME to 2026-07-01 on 2026-07-21 ("he did one edit …
    he's not the threat that we think he is"), so the cap is now in the past
    and the routine edit-rate pause no longer binds at all.
    """
    assert cg.resume_date(D(2026, 8, 7)) == cg.HARD_RESUME
    assert cg.resume_date(D(2026, 9, 1)) == cg.HARD_RESUME
    assert cg.should_run(cg.HARD_RESUME, D(2026, 8, 7))
    assert cg.should_run(D(2026, 8, 8), D(2026, 8, 8))    # editing that very day


def test_resume_date_never_exceeds_the_hard_cap():
    for offset in range(0, 400, 17):
        last = D(2026, 7, 10) + datetime.timedelta(days=offset)
        assert cg.resume_date(last) <= cg.HARD_RESUME


def test_the_edit_rate_pause_no_longer_binds():
    """With the cap in the past, editing every day does not hold the drip."""
    for day in range(10, 31):                     # 2026-07-10 … 2026-07-30
        today = D(2026, 7, day)
        assert cg.should_run(today, today), today


def test_no_edits_at_all_means_just_the_floor():
    assert cg.resume_date(None) == cg.MIN_PAUSE_UNTIL


def test_pause_reason_is_none_when_nothing_binds():
    assert cg.pause_reason(D(2026, 8, 8), D(2026, 8, 8)) is None
    assert cg.pause_reason(D(2026, 7, 10), D(2026, 7, 10)) is None


# ─────────────────────── per-item freshness ───────────────────────

TODAY = D(2026, 7, 10)


def test_item_touched_by_another_user_yesterday_is_blocked():
    revs = [("ブルーノ・プラス", D(2026, 7, 9))]
    assert not cg.is_item_fresh_enough(revs, TODAY)


def test_item_touched_by_another_user_eight_days_ago_is_allowed():
    revs = [("ブルーノ・プラス", D(2026, 7, 2))]
    assert cg.is_item_fresh_enough(revs, TODAY)


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
    assert cg.MIN_PAUSE_UNTIL == D(2026, 7, 17)   # a one-week pause from 2026-07-10
    # Was 2026-08-08 ("a week into August"); Emma moved it to 2026-07-01 on
    # 2026-07-21 — in the past, so the edit-rate pause no longer binds.
    assert cg.HARD_RESUME == D(2026, 7, 1)
    assert cg.ATTENTION_PAUSE_DAYS == 30          # "a month-long pause"
    assert cg.WATCHED_USER == "ブルーノ・プラス"


# ─────────────────────── attention: the three signals ───────────────────────

def test_talk_page_activity_triggers_a_month_long_pause():
    """'If there has been any activity within a month on their talk page, then
    there will be a month of no edits.'"""
    assert cg.resume_date(D(2026, 7, 10), talk_activity=D(2026, 7, 10)) == D(2026, 8, 9)
    assert not cg.should_run(D(2026, 8, 8), D(2026, 7, 10), talk_activity=D(2026, 7, 10))
    assert cg.should_run(D(2026, 8, 9), D(2026, 7, 10), talk_activity=D(2026, 7, 10))


def test_noticeboard_mention_triggers_a_month_long_pause():
    assert cg.resume_date(D(2026, 7, 10), noticeboard_mention=D(2026, 7, 10)) == D(2026, 8, 9)


def test_attention_overrides_the_hard_cap():
    """The cap exists to stop a busy editor vetoing us — not to force us to edit
    into a live noticeboard thread."""
    board = D(2026, 8, 1)
    assert cg.resume_date(D(2026, 8, 1), noticeboard_mention=board) == D(2026, 8, 31)
    assert cg.resume_date(D(2026, 8, 1), noticeboard_mention=board) > cg.HARD_RESUME
    assert not cg.should_run(cg.HARD_RESUME, D(2026, 8, 1), noticeboard_mention=board)


def test_the_real_april_talk_thread_no_longer_binds():
    """Their talk page last saw activity 2026-04-24; 30 days later is 2026-05-24,
    which is already past. Nothing binds — the routine cap is past too."""
    assert cg.resume_date(D(2026, 7, 10), talk_activity=D(2026, 4, 24)) == cg.HARD_RESUME
    assert cg.should_run(D(2026, 7, 21), D(2026, 7, 10), talk_activity=D(2026, 4, 24))


def test_old_attention_does_not_extend_a_later_pause():
    """max(), not sum(): attention in April is spent by July."""
    assert cg.resume_date(D(2026, 7, 20), talk_activity=D(2026, 4, 1)) == cg.HARD_RESUME


def test_the_latest_of_the_two_dated_signals_wins():
    r = cg.resume_date(D(2026, 7, 10), talk_activity=D(2026, 7, 1),
                       noticeboard_mention=D(2026, 7, 5))
    assert r == D(2026, 8, 4)


def test_no_attention_leaves_the_routine_gate_untouched():
    assert cg.resume_date(D(2026, 7, 20), None, None) == cg.resume_date(D(2026, 7, 20))


def test_attention_pause_applies_even_if_they_have_stopped_editing():
    """Attention outlives their activity — that is the whole point."""
    assert not cg.should_run(D(2026, 7, 25), D(2023, 3, 17), talk_activity=D(2026, 7, 20))


# ─────────────────────── 井戸端: indefinite hold ───────────────────────

def test_project_chat_presence_holds_indefinitely():
    """Emma: the Japanese project chat expires threads at 90 days and gets necroed,
    so presence of the name is a hold with no expiry date at all."""
    assert cg.resume_date(D(2026, 7, 10), project_chat_hold=True) is None
    assert not cg.should_run(D(2026, 7, 10), D(2026, 7, 10), project_chat_hold=True)


def test_project_chat_hold_beats_every_other_signal():
    for today in (D(2026, 8, 8), D(2027, 1, 1), D(2030, 1, 1)):
        assert not cg.should_run(today, D(2023, 3, 17), project_chat_hold=True)


def test_project_chat_hold_beats_the_hard_cap():
    assert not cg.should_run(cg.HARD_RESUME, None, project_chat_hold=True)


def test_hold_lifts_when_the_name_leaves_the_page():
    """No date expires it; the next clean scan does."""
    assert cg.resume_date(D(2023, 3, 17), project_chat_hold=True) is None
    assert cg.resume_date(D(2023, 3, 17), project_chat_hold=False) == cg.HARD_RESUME


def test_pause_reason_names_the_project_chat_hold():
    r = cg.pause_reason(D(2030, 1, 1), D(2023, 3, 17), project_chat_hold=True)
    assert "HELD INDEFINITELY" in r and "井戸端" in r


def test_pause_reason_names_the_noticeboard_when_it_binds():
    r = cg.pause_reason(D(2026, 8, 8), D(2026, 7, 10), noticeboard_mention=D(2026, 8, 1))
    assert "administrators' noticeboard" in r


def test_pause_reason_names_the_talk_page_when_it_binds():
    r = cg.pause_reason(D(2026, 8, 8), D(2026, 7, 10), talk_activity=D(2026, 8, 1))
    assert "talk page" in r
