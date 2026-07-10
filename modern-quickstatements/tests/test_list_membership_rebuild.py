"""Script 1: rebuild each Engishiki list entry's own "part of" statement.

The list item is the source of truth. Its has-part statements are deduplicated; the
shrine items' own statements are not. Neighbours are DERIVED from the list's ordering
rather than copied, so the list stays the only place the order is stated.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_list_membership_rebuild as rb  # noqa: E402
import direct_daily_edits as dde  # noqa: E402


def part(qid, ordinal=None, quantity=False):
    st = {"mainsnak": {"datavalue": {"type": "wikibase-entityid",
                                     "value": {"id": qid}}}, "qualifiers": {}}
    if ordinal is not None:
        st["qualifiers"]["P1545"] = [{"datavalue": {"value": ordinal}}]
    if quantity:
        st["qualifiers"]["P1114"] = [{"datavalue": {"value": "11"}}]
    return st


# ─────────────────────── reading the list ───────────────────────

def test_a_has_part_without_an_ordinal_is_a_class_count_not_an_entry():
    """`List of Shikinaisha in Shimotsuke Province` has three such: Shikinaisha,
    Taisha, Shōsha, qualified by quantity."""
    claims = {"P527": [part("Q134917286", quantity=True), part("Q135039969", "1")]}
    assert rb.list_members(claims) == [("Q135039969", "1")]


def test_members_come_back_in_ordinal_order():
    claims = {"P527": [part("Qc", "3"), part("Qa", "1"), part("Qb", "2")]}
    assert [q for q, _ in rb.list_members(claims)] == ["Qa", "Qb", "Qc"]


def test_ordinals_sort_numerically_not_lexically():
    claims = {"P527": [part("Qb", "10"), part("Qa", "9")]}
    assert [q for q, _ in rb.list_members(claims)] == ["Qa", "Qb"]


def test_a_non_numeric_ordinal_sorts_last_without_crashing():
    claims = {"P527": [part("Qb", "x"), part("Qa", "1")]}
    assert [q for q, _ in rb.list_members(claims)] == ["Qa", "Qb"]


# ─────────────────── an entry the list names twice is not emittable ───────────────────

def test_an_entry_named_at_two_ordinals_is_ambiguous():
    """Live: the Izumo list names Q135040786 at 28 and 29, Awa names Q11361262 at 3 and 5."""
    members = [("Qa", "1"), ("Qdup", "3"), ("Qb", "4"), ("Qdup", "5")]
    assert rb.ambiguous_entries(members) == {"Qdup"}


def test_an_entry_named_once_is_not_ambiguous():
    assert rb.ambiguous_entries([("Qa", "1"), ("Qb", "2")]) == set()


def test_the_same_entry_at_the_same_ordinal_twice_is_not_ambiguous():
    """A duplicated has-part statement says one thing twice. Only rival ordinals are fatal."""
    assert rb.ambiguous_entries([("Qa", "1"), ("Qa", "1")]) == set()


def test_an_empty_list_has_no_ambiguity():
    assert rb.ambiguous_entries([]) == set()


def test_contradictory_ordinals_would_land_on_one_statement():
    """Why this matters: both head lines carry the same value, so QuickStatements finds the
    SAME statement and hangs two rival ordinals on it."""
    a = rb.needed_lines("Qdup", "Qlist", "3", "Qp", "Qn", "1", URL, {})[0]
    b = rb.needed_lines("Qdup", "Qlist", "5", "Qp", "Qn", "1", URL, {})[0]
    assert a.startswith("Qdup|P361|Qlist") and b.startswith("Qdup|P361|Qlist")
    assert '|P1545|"3"' in a and '|P1545|"5"' in b


def test_neighbours_of_a_duplicated_entry_come_from_its_last_position():
    """Documented, not desirable — it is why such entries must be excluded, not emitted."""
    members = [("Qa", "1"), ("Qdup", "3"), ("Qb", "4"), ("Qdup", "5")]
    assert rb.neighbours(members)["Qdup"] == ("Qb", None)


def test_the_neighbours_of_other_entries_are_unaffected_by_a_duplicate():
    members = [("Qa", "1"), ("Qdup", "3"), ("Qb", "4"), ("Qdup", "5")]
    nb = rb.neighbours(members)
    assert nb["Qa"] == (None, "Qdup")
    assert nb["Qb"] == ("Qdup", "Qdup")


# ─────────────────────── neighbours derived from the list ───────────────────────

def test_neighbours_come_from_the_lists_own_order():
    members = [("Qa", "1"), ("Qb", "2"), ("Qc", "3")]
    nb = rb.neighbours(members)
    assert nb["Qa"] == (None, "Qb")
    assert nb["Qb"] == ("Qa", "Qc")
    assert nb["Qc"] == ("Qb", None)


def test_a_single_member_has_no_neighbours():
    assert rb.neighbours([("Qa", "1")])["Qa"] == (None, None)


# ─────────────────────── what a statement still needs ───────────────────────

URL = "https://ja.wikipedia.org/wiki/%E4%B8%8B%E9%87%8E%E5%9B%BD"


def statement(ordinal=None, prev=None, nxt=None, refs=()):
    st = {"mainsnak": {"datavalue": {"type": "wikibase-entityid",
                                     "value": {"id": "Qlist"}}},
          "qualifiers": {}, "references": []}
    if ordinal:
        st["qualifiers"]["P1545"] = [{"datavalue": {"value": ordinal}}]
    if prev:
        st["qualifiers"]["P155"] = [{"datavalue": {"value": {"id": prev}}}]
    if nxt:
        st["qualifiers"]["P156"] = [{"datavalue": {"value": {"id": nxt}}}]
    for p in refs:
        st["references"].append({"snaks": {p: [{}]}})
    return {"P361": [st]}


def test_a_bare_statement_needs_everything():
    lines = rb.needed_lines("Qe", "Qlist", "4", "Qp", "Qn", "182030", URL, statement())
    assert len(lines) == 2
    assert lines[0].startswith('Qe|P361|Qlist|P1545|"4"|P155|Qp|P156|Qn|S248|Q135159299|S13677|"182030"')
    assert lines[1] == 'Qe|P361|Qlist|S4656|"%s"' % URL


def test_a_complete_statement_needs_nothing():
    claims = statement("4", "Qp", "Qn", refs=("P248", "P4656"))
    assert rb.needed_lines("Qe", "Qlist", "4", "Qp", "Qn", "182030", URL, claims) == []


def test_only_the_missing_url_reference_is_emitted():
    claims = statement("4", "Qp", "Qn", refs=("P248",))
    lines = rb.needed_lines("Qe", "Qlist", "4", "Qp", "Qn", "182030", URL, claims)
    assert lines == ['Qe|P361|Qlist|S4656|"%s"' % URL]


def test_a_wrong_ordinal_is_corrected():
    claims = statement("9", "Qp", "Qn", refs=("P248", "P4656"))
    lines = rb.needed_lines("Qe", "Qlist", "4", "Qp", "Qn", "182030", URL, claims)
    assert lines and '|P1545|"4"' in lines[0]


def test_the_first_entry_emits_no_follows():
    lines = rb.needed_lines("Qe", "Qlist", "1", None, "Qn", "182030", URL, statement())
    assert "|P155|" not in lines[0] and "|P156|Qn" in lines[0]


def test_the_last_entry_emits_no_followed_by():
    lines = rb.needed_lines("Qe", "Qlist", "9", "Qp", None, "182030", URL, statement())
    assert "|P156|" not in lines[0] and "|P155|Qp" in lines[0]


def test_no_kokugakuin_id_means_no_database_reference():
    """Several ids on one entry -> we cannot say which, so no reference is claimed."""
    lines = rb.needed_lines("Qe", "Qlist", "4", None, None, None, URL, statement())
    assert "S248" not in lines[0] and "S13677" not in lines[0]


def test_an_entry_with_no_kokugakuin_id_stops_emitting_once_correct():
    """Otherwise the head line is re-emitted for ever, waiting on a reference this
    script will never add."""
    claims = statement("4", refs=("P4656",))
    assert rb.needed_lines("Qe", "Qlist", "4", None, None, None, URL, claims) == []


def test_a_missing_statement_entirely_is_created():
    lines = rb.needed_lines("Qe", "Qlist", "4", None, None, "182030", URL, {})
    assert lines[0].startswith('Qe|P361|Qlist|P1545|"4"')


# ─────────────────────── invariants ───────────────────────

def test_no_line_is_a_removal():
    lines = rb.needed_lines("Qe", "Qlist", "4", "Qp", "Qn", "182030", URL, statement())
    rb.assert_add_only(lines)
    assert all(not l.startswith("-") for l in lines)


def test_assert_add_only_rejects_a_dash_line():
    with pytest.raises(RuntimeError, match="ADD-ONLY"):
        rb.assert_add_only(["Qe|P361|Qlist", "-Qe|P361|Qlist"])


def test_the_reference_item_is_the_verified_one():
    assert rb.KOKUGAKUIN_DB == "Q135159299"     # Kokugakuin University Shrine database


# ─────────────────────── the daily editor can execute it ───────────────────────

def test_the_daily_editor_parses_the_qualifier_line():
    """`Qlist` is not a numeric QID, and the real parser rejects it — use real ids."""
    line = rb.needed_lines("Q42", "Q11361380", "4", "Q1", "Q2", "182030", URL, {})[0]
    p = dde.parse_qs_line(line)
    assert p["entity"] == "Q42" and p["property"] == "P361"
    assert p["value"]["value"]["id"] == "Q11361380"
    quals = dict((k, v) for k, v in p["qualifiers"])
    assert quals["P1545"]["value"] == "4"
    assert quals["P155"]["value"]["id"] == "Q1"
    refs = dict((k, v) for k, v in p["references"])
    assert refs["P248"]["value"]["id"] == "Q135159299"
    assert refs["P13677"]["value"] == "182030"
    assert not p["is_removal"]


def test_the_daily_editor_parses_the_url_reference_line():
    claims = {"P361": [{"mainsnak": {"datavalue": {"type": "wikibase-entityid",
                                                   "value": {"id": "Q11361380"}}},
                        "qualifiers": {"P1545": [{"datavalue": {"value": "4"}}]},
                        "references": [{"snaks": {"P248": [{}]}}]}]}
    lines = rb.needed_lines("Q42", "Q11361380", "4", None, None, "182030", URL, claims)
    line, = lines
    p = dde.parse_qs_line(line)
    (rprop, rval), = p["references"]
    assert rprop == "P4656" and rval["value"] == URL


def test_output_file_is_registered_in_atomic_files():
    assert rb.OUTPUT_FILE in dde.ATOMIC_FILES
