"""Script 2: take the list link away from the Ronsha no list names.

Emma: *"Ronshas should not even have list membership."* The hazard is that QuickStatements
removes by value, not by statement id — so a removal aimed at an item's junk membership
would happily take a clean one instead. Pinned here: the named-part guard (twice, once in
the builder and once as a check over the finished lines), the duplicate-statement count,
and the fact that this batch is NOT registered.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_list_membership_removals as rm  # noqa: E402
import generate_list_membership_rebuild as rb  # noqa: E402
import direct_daily_edits as dde  # noqa: E402


PARTS = {"Qlist": {"Qnamed"}}


# ─────────────────────── who loses the link ───────────────────────

def test_an_item_the_list_does_not_name_loses_it():
    lines, kept, _d = rm.removal_lines({("Qjunk", "Qlist"): 1}, PARTS)
    assert lines == ["-Qjunk|P361|Qlist"] and kept == []


def test_an_item_the_list_names_keeps_it():
    lines, kept, _d = rm.removal_lines({("Qnamed", "Qlist"): 1}, PARTS)
    assert lines == [] and kept == [("Qnamed", "Qlist")]


def test_membership_is_judged_per_list_not_per_item():
    """Named by one list, junk on another: only the junk goes."""
    claims = {("Qnamed", "Qlist"): 1, ("Qnamed", "Qother"): 1}
    lines, kept, _d = rm.removal_lines(claims, PARTS)
    assert lines == ["-Qnamed|P361|Qother"]
    assert kept == [("Qnamed", "Qlist")]


def test_a_list_with_no_named_parts_at_all_does_not_crash():
    lines, _k, _d = rm.removal_lines({("Qjunk", "Qempty"): 1}, PARTS)
    assert lines == ["-Qjunk|P361|Qempty"]


# ─────────────────────── duplicate statements ───────────────────────

def test_each_duplicate_statement_gets_its_own_line():
    """One QuickStatements line removes one statement. Three statements, three lines."""
    lines, _k, dupes = rm.removal_lines({("Qjunk", "Qlist"): 3}, PARTS)
    assert lines == ["-Qjunk|P361|Qlist"] * 3
    assert dupes == 1


def test_a_single_statement_is_not_counted_as_a_duplicate():
    _l, _k, dupes = rm.removal_lines({("Qjunk", "Qlist"): 1}, PARTS)
    assert dupes == 0


def test_duplicates_on_a_named_part_are_still_never_removed():
    lines, kept, dupes = rm.removal_lines({("Qnamed", "Qlist"): 4}, PARTS)
    assert lines == [] and kept and dupes == 0


# ─────────────────────── the guards ───────────────────────

def test_the_named_part_guard_catches_a_line_that_should_not_exist():
    with pytest.raises(RuntimeError, match="the list NAMES"):
        rm.assert_never_touches_a_named_part(["-Qnamed|P361|Qlist"], PARTS)


def test_the_named_part_guard_passes_a_legitimate_removal():
    rm.assert_never_touches_a_named_part(["-Qjunk|P361|Qlist"], PARTS)


def test_the_guard_runs_over_the_lines_not_the_inputs():
    """It must catch a bug in removal_lines(), so it re-parses what was emitted."""
    lines, _k, _d = rm.removal_lines({("Qnamed", "Qlist"): 1}, PARTS)
    rm.assert_never_touches_a_named_part(lines, PARTS)


def test_remove_only_rejects_an_add():
    with pytest.raises(RuntimeError, match="REMOVE-ONLY"):
        rm.assert_remove_only(["-Q1|P361|Q2", "Q1|P361|Q3"])


def test_every_emitted_line_is_a_removal():
    lines, _k, _d = rm.removal_lines({("Qa", "Ql"): 1, ("Qb", "Ql"): 2}, PARTS)
    rm.assert_remove_only(lines)
    assert lines and all(l.startswith("-") for l in lines)


# ─────────────────────── it does not fight script 1 ───────────────────────

def test_the_two_scripts_disagree_about_no_item():
    """Script 1 adds to the named; script 2 removes from the rest. Disjoint by construction."""
    claims = {("Qnamed", "Qlist"): 1, ("Qjunk", "Qlist"): 1}
    lines, kept, _d = rm.removal_lines(claims, PARTS)
    removed = {l[1:].split("|")[0] for l in lines}
    assert removed.isdisjoint({i for i, _l in kept})


def test_script_one_is_add_only_and_script_two_is_remove_only():
    rb.assert_add_only(["Qnamed|P361|Qlist"])
    rm.assert_remove_only(["-Qjunk|P361|Qlist"])
    with pytest.raises(RuntimeError):
        rb.assert_add_only(["-Qjunk|P361|Qlist"])


def test_the_two_scripts_write_different_files():
    assert rm.OUTPUT_FILE != rb.OUTPUT_FILE


# ─────────────────────── wiring ───────────────────────

def test_this_batch_is_deliberately_not_registered():
    """A registered removal batch would run interleaved with script 1's adds."""
    assert rm.OUTPUT_FILE not in dde.ATOMIC_FILES


def test_script_one_is_registered():
    assert rb.OUTPUT_FILE in dde.ATOMIC_FILES


def test_the_daily_editor_parses_a_removal_line():
    p = dde.parse_qs_line(rm.removal_line("Q42", "Q11361380"))
    assert p["is_removal"] and p["entity"] == "Q42" and p["property"] == "P361"
    assert p["value"]["value"]["id"] == "Q11361380"


def test_the_ronsha_class_is_the_disputed_one_not_the_confirmed_one():
    """Q134917286 is confirmed Shikinaisha; removing ITS list links would be wrong."""
    assert rm.RONSHA == "Q135022904"
