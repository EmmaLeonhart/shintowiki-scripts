"""Tests for reuse_labels.choose_label — Stage 2 dominant/alias rule logic.

Emma's rules (queue.md A2):
  - dominant reading (strictly highest count among same-ja-name shrines with en)
    becomes the label; ties -> pick one at random.
  - an alias is added ONLY when there is exactly one OTHER distinct reading
    (i.e. exactly 2 distinct readings total); 3+ distinct readings -> no alias.
  - random tie-break is deterministic per QID so the chosen label is stable
    across daily runs (no Wikidata label churn).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reuse_labels import choose_label  # noqa: E402


def test_no_candidates_returns_none():
    assert choose_label({}, "Q1") is None


def test_single_reading_no_alias():
    assert choose_label({"Suwa Shrine": 3}, "Q1") == ("Suwa Shrine", None)


def test_two_readings_dominant_wins_other_is_alias():
    assert choose_label({"Suwa Shrine": 5, "Suwa Jinja": 1}, "Q1") == ("Suwa Shrine", "Suwa Jinja")


def test_two_readings_tie_picks_one_label_other_alias():
    label, alias = choose_label({"A Shrine": 2, "B Shrine": 2}, "Q1")
    assert {label, alias} == {"A Shrine", "B Shrine"}
    assert label != alias


def test_three_readings_dominant_no_alias():
    assert choose_label({"A": 5, "B": 1, "C": 1}, "Q1") == ("A", None)


def test_three_readings_tie_for_max_no_alias():
    label, alias = choose_label({"A": 2, "B": 2, "C": 1}, "Q1")
    assert label in {"A", "B"}
    assert alias is None


def test_tie_break_is_stable_per_qid():
    c = {"A Shrine": 2, "B Shrine": 2}
    assert choose_label(c, "Q42") == choose_label(c, "Q42")


def test_tie_break_varies_by_qid():
    # different QIDs should be able to land on different picks (not all identical)
    c = {"A Shrine": 1, "B Shrine": 1}
    picks = {choose_label(c, f"Q{i}")[0] for i in range(50)}
    assert picks == {"A Shrine", "B Shrine"}
