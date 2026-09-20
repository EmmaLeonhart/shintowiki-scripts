"""Resolving dedication concepts to QIDs, and the allow-list learning (2026-09-20).

The 101-row seed was 52% wrong, so the second lookup is a script that states its
query, filters on `ALLOWED_CLASSES`, and accepts only when **exactly one**
candidate survives — then gets read by hand.

⭐ The refusals are the evidence it works. `Sacred Heart` returned a university
and a Dio album above the devotion; `Saints Peter and Paul` returned three
paintings; `Exaltation of the Holy Cross` returned a painting and a church in
Jelenia Góra. A first-hit lookup takes those.

⛔ And the allow-list itself was wrong, in the direction the seed made likely:
drawn from a people-heavy sample, it had no class for a DEVOTION, a CHRISTIAN
DOGMA or a FEAST, so it refused `Holy Trinity`, `Sacred Heart` and `Intercession
of the Theotokos` — each of them the correct answer. Widened from the measured
P31 of those three items, not from intuition.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import religious_building_morphemes as m  # noqa: E402
import saint_qids as sq  # noqa: E402
import resolve_dedication_qids as r  # noqa: E402


# --------------------------------------------------------------------------
# The concept map
# --------------------------------------------------------------------------
@pytest.mark.parametrize("label,qid", [
    ("Dreifaltigkeitskirche", "Q37090"),      # Holy Trinity
    ("San Martino", "Q133704"),               # Martin of Tours
    ("St. Laurentius", "Q17590"),             # Lawrence of Rome
    ("Sacred Heart", "Q408284"),
    ("San Rocco", "Q152457"),                 # Saint Roch
])
def test_a_matched_label_resolves_to_its_dedicatee(label, qid):
    assert sq.qid_for_match(m.match_dedication(label)) == qid


def test_the_unit_is_the_concept_not_the_table_key():
    """`martin` and `martino` are one saint; `assunta`, `asunción` and
    `mariä himmelfahrt` are one Assumption. Two table entries that render to the
    same Japanese string are the same thing."""
    assert (sq.qid_for_match(m.match_dedication("San Martino"))
            == sq.qid_for_match(m.match_dedication("Martinskirche")))
    for label in ("Mariä Himmelfahrt", "Asunción", "Assunta"):
        assert sq.qid_for_match(m.match_dedication(label)) == "Q162691", label


def test_an_unmatched_label_has_no_qid():
    assert sq.qid_for_match(m.match_dedication("St. Fictitious")) is None
    assert sq.qid_for_match(None) is None


def test_a_two_saint_dedication_returns_nothing():
    """⛔ `Santi Martino e Giorgio` needs TWO P825 statements. Emitting one of
    them silently asserts the label names a single dedicatee, so the caller
    decides whether to emit a pair — this file does not."""
    hit = m.match_dedication("Santi Martino e Giorgio")
    assert hit[0] == "names" and len(hit[1]) == 2
    assert sq.qid_for_match(hit) is None


# --------------------------------------------------------------------------
# ⛔ The allow-list, and what it learned
# --------------------------------------------------------------------------
@pytest.mark.parametrize("qid,cls", [
    ("Q3045134", "Christian dogma"),
    ("Q2634521", "title of Jesus"),
    ("Q1445650", "holiday"),
])
def test_the_concept_classes_the_people_heavy_sample_missed(qid, cls):
    """Each of these refused a CORRECT answer until it was added, and each was
    added from the measured P31 of the item it was refusing."""
    assert sq.ALLOWED_CLASSES[qid] == cls


def test_titles_of_jesus_parallels_titles_of_mary():
    assert "Q1509831" in sq.ALLOWED_CLASSES      # titles of Mary
    assert "Q2634521" in sq.ALLOWED_CLASSES      # title of Jesus


def test_the_allow_list_is_still_a_list_not_a_policy():
    assert len(sq.ALLOWED_CLASSES) < 32, (
        "it enumerates what a dedicatee may BE; past a page it has stopped "
        "being an allow-list and become a way of saying yes")


# --------------------------------------------------------------------------
# The resolver's acceptance rule
# --------------------------------------------------------------------------
def test_exactly_one_survivor_or_refuse(monkeypatch):
    """⛔ Zero survivors is a refusal; two or more is a refusal. Choosing between
    two plausible candidates is the judgement this file exists to avoid — `John`
    really is ambiguous between the Evangelist and John of Patmos."""
    monkeypatch.setattr(r, "search", lambda q, limit=8: [
        ("Q1", "A", ""), ("Q2", "B", "")])
    monkeypatch.setattr(r, "classes", lambda qs: {"Q1": ["Q5"], "Q2": ["Q5"]})
    qid, why = r.resolve("x", "x")
    assert qid is None and "candidates survive" in why

    monkeypatch.setattr(r, "classes", lambda qs: {"Q1": ["Q5"], "Q2": ["Q11424"]})
    qid, why = r.resolve("x", "x")
    assert qid == "Q1"

    monkeypatch.setattr(r, "classes", lambda qs: {"Q1": ["Q11424"], "Q2": ["Q11424"]})
    qid, why = r.resolve("x", "x")
    assert qid is None and "no candidate is a dedicatee class" in why


def test_an_unclassified_item_is_refused(monkeypatch):
    """⚠ `True Cross` and `Feast of the Cross` carry NO P31 at all, so the class
    filter cannot clear them. Unlisted means refuse, and so does unclassified —
    they are correct answers this method cannot verify, not wrong ones."""
    monkeypatch.setattr(r, "search", lambda q, limit=8: [("Q380356", "True Cross", "")])
    monkeypatch.setattr(r, "classes", lambda qs: {"Q380356": []})
    qid, why = r.resolve("x", "x")
    assert qid is None


def test_the_script_proposes_and_does_not_install():
    """It writes a report and a JSON; nothing reaches SAINT_QIDS without a human
    reading the line."""
    src = open(r.__file__, encoding="utf-8").read()
    assert "It proposes; it does not install" in src
    assert "SAINT_QIDS[" not in src


# --------------------------------------------------------------------------
# Shape
# --------------------------------------------------------------------------
def test_every_concept_maps_to_a_real_rendering():
    renderings = ({v["ja"] for v in m.NAMES.values()}
                  | {v["ja"] for v in m.DEDICATIONS.values()}
                  | {v["ja"] for v in m.NAME_PHRASES.values()})
    for ja in sq.QID_BY_RENDERING:
        assert ja in renderings, ja


def test_no_concept_contradicts_the_term_map():
    """The two maps were built from different lookups; where both cover the same
    dedicatee they must agree."""
    assert sq.QID_BY_RENDERING.get("聖母被昇天") == sq.SAINT_QIDS.get("the Assumption")
    assert sq.QID_BY_RENDERING.get("恩寵の聖母") == sq.SAINT_QIDS.get("Our Lady of Grace")
