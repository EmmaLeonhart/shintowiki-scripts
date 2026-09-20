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


# --------------------------------------------------------------------------
# ⛔ The second round, and what the hand review caught (2026-09-20)
# --------------------------------------------------------------------------
def test_the_swedish_all_saints_day_is_not_a_dedicatee():
    """The script ACCEPTED `諸聖人 -> Q10405623` — one candidate, right class —
    and its own Wikidata description says "Swedish Christian festival, distinct
    from the more common" one. 56 churches would have been dedicated to a Swedish
    national holiday. This is the case that justifies reading every line."""
    assert "諸聖人" not in sq.QID_BY_RENDERING
    assert sq.qid_for_match(m.match_dedication("Allerheiligenkapelle")) is None


def test_the_guessed_replacement_was_not_installed_either():
    """⚠ Q18378, reached for as the general All Saints' Day, is an Italian
    comune. A guess made while correcting a guess."""
    assert "Q18378" not in sq.QID_BY_RENDERING.values()
    assert "Q18378" not in sq.SAINT_QIDS.values()


def test_a_query_that_finds_nothing_looks_like_a_concept_that_does_not_exist():
    """⚠ `Mary mother of Jesus` returned ZERO hits and was reported as a blocker
    for 489 items. wbsearchentities is not a sentence parser — and `Our Lady` was
    already in the term map all along, so 聖母 was never unresolved at all."""
    assert sq._index()["聖母"] == "Q345"
    assert sq.SAINT_QIDS["Our Lady"] == "Q345"


def test_the_hand_resolutions_are_recorded_with_their_reason():
    """The script refuses when more than one candidate survives. A human may
    still decide — and must write down which and why."""
    src = open(os.path.join(HERE, "saint_qids.py"), encoding="utf-8").read()
    assert sq.QID_BY_RENDERING["キリスト"] == "Q302"
    assert sq.QID_BY_RENDERING["無原罪の御宿り"] == "Q185606"
    assert "American Internet personality" in src
    assert "A judgement, not an identity" in src


def test_the_genuinely_ambiguous_are_still_refused():
    """A bare `Johannes` on a German church is the Evangelist or John of Patmos
    and the label does not say. `Our Lady of Peace` has two candidates. Neither
    was hand-resolved, because neither is an identity."""
    assert "ヨハネ" not in sq.QID_BY_RENDERING
    assert "平和" not in sq.QID_BY_RENDERING


def test_the_unclassified_stay_unclassified():
    """`True Cross` and `Feast of the Cross` carry no P31 at all — 357 slots
    between them, and no amount of wanting them changes what can be verified."""
    for ja in ("聖十字架", "十字架挙栄"):
        assert ja not in sq.QID_BY_RENDERING, ja
