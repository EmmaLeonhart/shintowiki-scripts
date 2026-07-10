"""Script 2: drop Takano Shrine's two old addresses, but only after the merge lands.

The hazard this guards against is ordering. The daily batch runs its lines in random
order, so an add and a remove in one file can fire remove-first and leave the shrine
with no address at all. Script 2 therefore emits nothing until it can *see* the merged
address live. Pinned here: the gate, the remove-only invariant, and the fact that this
batch is NOT registered — a registered removal batch would reintroduce the ordering.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_ronsha_address_merge_removals as rm  # noqa: E402
import generate_miscellaneous_edits as misc  # noqa: E402
import direct_daily_edits as dde  # noqa: E402


BOTH_OLD = set(rm.SUPERSEDED)
LANDED = BOTH_OLD | {rm.MERGED}


# ─────────────────────── the gate ───────────────────────

def test_nothing_is_emitted_before_the_merge_lands():
    lines, why = rm.needed_lines(BOTH_OLD)
    assert lines == []
    assert "not on the item yet" in why


def test_both_old_forms_go_once_the_merge_is_live():
    lines, _why = rm.needed_lines(LANDED)
    assert sorted(lines) == sorted(rm.removal_line(rm.QID, a) for a in rm.SUPERSEDED)


def test_only_the_forms_still_present_are_removed():
    """Somebody else dropped one by hand; do not ask to remove it twice."""
    lines, _why = rm.needed_lines({rm.MERGED, rm.SUPERSEDED[0]})
    assert lines == [rm.removal_line(rm.QID, rm.SUPERSEDED[0])]


def test_a_finished_merge_emits_nothing():
    lines, why = rm.needed_lines({rm.MERGED})
    assert lines == [] and "already gone" in why


def test_an_empty_item_emits_nothing_rather_than_crashing():
    lines, _why = rm.needed_lines(set())
    assert lines == []


# ─────────────────────── what gets removed, exactly ───────────────────────

def test_the_merged_address_carries_everything_the_old_two_did():
    postcode, prefecture, block = "〒708-0013", "岡山県", "601"
    assert postcode in rm.MERGED and prefecture in rm.MERGED and block in rm.MERGED
    # …which is precisely why neither old form could simply be kept
    assert prefecture not in rm.SUPERSEDED[0]
    assert postcode not in rm.SUPERSEDED[1] and block not in rm.SUPERSEDED[1]


def test_the_merged_address_is_never_itself_removed():
    assert rm.MERGED not in rm.SUPERSEDED
    lines, _ = rm.needed_lines(LANDED)
    assert not any(rm.MERGED in l for l in lines)


def test_the_removals_are_remove_only():
    lines, _ = rm.needed_lines(LANDED)
    rm.assert_remove_only(lines)
    assert lines and all(l.startswith("-") for l in lines)


def test_assert_remove_only_rejects_an_add():
    with pytest.raises(RuntimeError, match="REMOVE-ONLY"):
        rm.assert_remove_only(["-Q1|P6375|ja:\"x\"", "Q1|P6375|ja:\"y\""])


# ─────────────────────── the two halves agree ───────────────────────

def test_script_one_adds_exactly_the_address_script_two_waits_for():
    add = [e for e in misc.STATIC_EDITS if e[0] == rm.QID]
    assert len(add) == 1
    _qid, prop, value, _why = add[0]
    assert prop == rm.P_ADDRESS
    assert value == 'ja:"{}"'.format(rm.MERGED)


def test_the_misc_queue_never_removes_this_item():
    """The removals must live here, behind the SPARQL gate — not in the drip."""
    assert not any(q == rm.QID for q, _d, _k, _w in misc.ADDRESS_REMOVALS)


def test_the_misc_queue_would_reject_these_removals():
    with pytest.raises(RuntimeError, match="STATIC_REMOVALS"):
        misc.assert_removals_enumerated(rm.needed_lines(LANDED)[0])


# ─────────────────────── it is not wired into the drip ───────────────────────

def test_this_batch_is_deliberately_not_registered():
    """Registering it would put an add and a remove in one randomly-ordered run."""
    assert rm.OUTPUT_FILE not in dde.ATOMIC_FILES


def test_the_daily_editor_could_still_parse_the_lines_if_run_by_hand():
    for line in rm.needed_lines(LANDED)[0]:
        p = dde.parse_qs_line(line)
        assert p["is_removal"] and p["entity"] == rm.QID
        assert p["value"]["type"] == "monolingualtext"
        assert p["value"]["value"]["language"] == "ja"
