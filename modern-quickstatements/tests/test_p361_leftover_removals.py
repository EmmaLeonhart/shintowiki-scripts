"""The ordinal-less `part of` leftover removals.

What these pin is the one thing the executor cannot check for itself: a
value-matched `-Q|P361|Qlist` removes the FIRST matching claim, so the line is
correct only when the leftover is that first claim. Every exclusion below exists
because emitting the line anyway would remove the membership instead of the
residue.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import generate_p361_leftover_removals as gen  # noqa: E402


def claim(list_qid, ords=(), refs=0):
    c = {"mainsnak": {"snaktype": "value",
                      "datavalue": {"value": {"id": list_qid}}}}
    if ords:
        c["qualifiers"] = {"P1545": [{"datavalue": {"value": o}} for o in ords]}
    if refs:
        c["references"] = [{}] * refs
    return c


def row(item="Q1", lst="Qlist", says=("5",)):
    return {"item": item, "list": lst, "ja": "テスト", "list_says": list(says)}


# ─────────────────────── what gets emitted ───────────────────────

def test_blank_first_ordinalled_second_emits():
    stmts = [claim("Qlist"), claim("Qlist", ["5"])]
    line, why = gen.classify("blank_leftover", row(), stmts, None)
    assert line == "-Q1|P361|Qlist"
    assert "first claim" in why


def test_a_reference_on_the_blank_does_not_stop_it():
    """Q11487792's leftover carries a reference. A sourced statement that says
    nothing is still the residue; the ordinalled one is the membership."""
    stmts = [claim("Qlist", refs=1), claim("Qlist", ["5"])]
    line, _ = gen.classify("blank_leftover", row(), stmts, None)
    assert line == "-Q1|P361|Qlist"


# ─────────────────────── what gets excluded, and why ───────────────────────

def test_ordinalled_first_is_refused():
    """The removal would reach the membership, not the leftover — Q107306769."""
    stmts = [claim("Qlist", ["5"], refs=2), claim("Qlist", ["5"])]
    line, why = gen.classify("blank_leftover", row(), stmts, None)
    assert line is None
    assert "would take the membership" in why


def test_a_pair_already_dripping_elsewhere_is_refused():
    stmts = [claim("Qlist"), claim("Qlist", ["5"])]
    line, why = gen.classify("blank_leftover", row(), stmts,
                             {"orphan_membership_removals.txt"})
    assert line is None
    assert "already staged" in why


def test_the_true_duplicate_class_is_refused():
    stmts = [claim("Qlist", ["5"]), claim("Qlist", ["5"])]
    line, why = gen.classify("true_duplicate", row(), stmts, None)
    assert line is None
    assert "true_duplicate" in why


def test_a_single_statement_is_nothing_to_de_duplicate():
    line, why = gen.classify("blank_leftover", row(), [claim("Qlist", ["5"])], None)
    assert line is None
    assert "nothing to de-duplicate" in why


def test_no_ordinalled_survivor_is_refused():
    """Two blanks: the removal leaves a statement that says nothing, and the
    membership was never there to preserve."""
    line, why = gen.classify("blank_leftover", row(), [claim("Qlist"), claim("Qlist")], None)
    assert line is None
    assert "no ordinalled statement survives" in why


def test_a_survivor_the_list_does_not_name_is_refused():
    stmts = [claim("Qlist"), claim("Qlist", ["9"])]
    line, why = gen.classify("blank_leftover", row(says=("5",)), stmts, None)
    assert line is None
    assert "not the ['5'] the list names" in why


# ─────────────────────── reading live state ───────────────────────

def test_statements_into_keeps_order_and_ignores_other_targets():
    claims = [claim("Qother"), claim("Qlist"), claim("Qlist", ["5"])]
    got = gen.statements_into(claims, "Qlist")
    assert len(got) == 2
    assert gen.ordinals(got[0]) == []
    assert gen.ordinals(got[1]) == ["5"]


def test_somevalue_mainsnaks_are_not_matched():
    claims = [{"mainsnak": {"snaktype": "somevalue"}}, claim("Qlist")]
    assert len(gen.statements_into(claims, "Qlist")) == 1


def test_load_staged_reads_the_registered_removal_files(tmp_path):
    (tmp_path / "list_membership_removals.txt").write_text(
        "-Q1|P361|Qlist\nQ2|P31|Q3\n-Q4|P1448|ja:\"x\"\n", encoding="utf-8")
    staged = gen.load_staged(str(tmp_path))
    assert staged == {("Q1", "Qlist"): {"list_membership_removals.txt"}}


def test_the_population_is_the_audit_plus_only_confirmed_leftovers():
    pop = gen.load_population()
    classes = {c for c, _ in pop}
    assert classes == {"true_duplicate", "blank_leftover"}
    for cls, r in pop:
        if cls == "blank_leftover":
            assert r["list_says"], r
