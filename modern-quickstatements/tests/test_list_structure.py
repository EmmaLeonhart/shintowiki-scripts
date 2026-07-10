"""Structural sweep of the 69 Engishiki list items (report only).

The Awa defect was found because the Kokugakuin id sequence skipped 181734 while an entry
item held it and no list named it. These pin the five detectors that generalise that shape.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import report_list_structure as st  # noqa: E402


# ─────────────────────── contested ordinals ───────────────────────

def test_two_entries_at_one_ordinal_are_reported_with_both():
    """Live: Izumo, ordinal 29 — 同社坐韓国伊大弖神社 and 筑陽神社."""
    got = st.contested_ordinals([("Qa", "29"), ("Qb", "29"), ("Qc", "30")])
    assert got == {"29": {"Qa", "Qb"}}


def test_one_entry_named_twice_at_one_ordinal_is_not_contested():
    assert st.contested_ordinals([("Qa", "1"), ("Qa", "1")]) == {}


def test_a_clean_list_has_no_contested_ordinal():
    assert st.contested_ordinals([("Qa", "1"), ("Qb", "2")]) == {}


# ─────────────────────── entries at several ordinals ───────────────────────

def test_an_entry_at_two_ordinals_is_reported_with_both():
    got = st.entries_at_several_ordinals([("Qa", "3"), ("Qa", "5"), ("Qb", "4")])
    assert got == {"Qa": {"3", "5"}}


def test_an_entry_at_one_ordinal_is_not_reported():
    assert st.entries_at_several_ordinals([("Qa", "3"), ("Qb", "4")]) == {}


# ─────────────────────── holes ───────────────────────

def test_a_missing_ordinal_is_found():
    """Live: Inaba is missing 7, Izumo is missing 39."""
    assert st.ordinal_holes([("Qa", "1"), ("Qb", "2"), ("Qc", "4")]) == [3]


def test_several_holes_come_back_sorted():
    assert st.ordinal_holes([("Qa", "1"), ("Qb", "5")]) == [2, 3, 4]


def test_a_contiguous_list_has_no_holes():
    assert st.ordinal_holes([("Qa", "1"), ("Qb", "2"), ("Qc", "3")]) == []


def test_holes_are_measured_to_the_maximum_not_beyond():
    assert st.ordinal_holes([("Qa", "1"), ("Qb", "2")]) == []


def test_a_non_numeric_ordinal_makes_holes_unknowable_rather_than_wrong():
    assert st.ordinal_holes([("Qa", "1"), ("Qb", "x")]) == []


def test_an_empty_list_has_no_holes():
    assert st.ordinal_holes([]) == []


# ─────────────────────── entry items nothing points at ───────────────────────

NAMED = {"Qnamed"}


def test_an_item_sharing_its_id_with_a_named_entry_is_a_duplicate_not_a_hole():
    """That is the orphan report's business, not this one."""
    kok = {"Qnamed": ["100"], "Qdup": ["100"]}
    assert st.unlinked_entry_items(NAMED, kok) == []


def test_an_item_holding_an_id_no_named_entry_holds_is_reported():
    """Live: Q137041912 天神社 holds 181734, which the Awa list skips entirely."""
    kok = {"Qnamed": ["100"], "Qhomeless": ["101"]}
    assert st.unlinked_entry_items(NAMED, kok) == ["Qhomeless"]


def test_a_named_entry_is_never_reported_as_homeless():
    assert st.unlinked_entry_items(NAMED, {"Qnamed": ["100"]}) == []


def test_an_item_with_no_kokugakuin_id_is_not_reported():
    """Without an id there is no evidence it is a register entry at all."""
    assert st.unlinked_entry_items(NAMED, {"Qnothing": []}) == []


def test_an_item_holding_two_ids_one_of_them_shared_is_a_duplicate():
    kok = {"Qnamed": ["100"], "Qboth": ["100", "101"]}
    assert st.unlinked_entry_items(NAMED, kok) == []


def test_the_result_is_sorted_for_a_stable_report():
    kok = {"Qb": ["2"], "Qa": ["1"]}
    assert st.unlinked_entry_items(set(), kok) == ["Qa", "Qb"]


# ─────────────────────── the class items are not entries ───────────────────────

def test_the_three_class_count_items_are_known():
    """A has-part naming one of these with a quantity is a count, not a missing ordinal."""
    assert "Q134917286" in st.CLASS_COUNTS and len(st.CLASS_COUNTS) == 3
