"""Unit tests for match_new_qids.choose_hit — the exact-ja matching rule.

Emma's rule (2026-07-06): the Japanese labels were never changed after creation, so a
single item under the exact ja label is our recreated item regardless of its P31 (she
re-types items afterward — Izumo 講社 → shrine-church, P279 subclasses have empty P31).
Only a genuine multi-item ja collision needs P31/fresh-range disambiguation.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from match_new_qids import FRESH_MIN, choose_hit  # noqa: E402


def test_no_candidates_returns_none():
    assert choose_hit([], "Q845945", {}) is None


def test_singleton_accepted_regardless_of_p31():
    # the Izumo shrine-church case: our P31 was Q845945 (shrine); Emma re-typed the live
    # item to Q135437254 (shrine-church). Singleton exact-ja → still ours.
    assert choose_hit(["Q140446130"], "Q845945", {}) == "Q140446130"


def test_singleton_accepted_with_empty_live_p31():
    # 和鏡 / 暦師: P279 subclasses, live P31 empty. Singleton → ours.
    assert choose_hit(["Q140446073"], "Q1041984", {"Q140446073": []}) == "Q140446073"


def test_multi_candidate_disambiguated_by_our_p31():
    p31s = {"Q108702052": ["Q860861"], "Q140446200": ["Q11388990"]}
    # our assigned type picks our item out of a real ja-label collision
    assert choose_hit(["Q108702052", "Q140446200"], "Q11388990", p31s) == "Q140446200"


def test_multi_candidate_no_p31_match_falls_back_to_single_fresh():
    # neither carries our P31, but exactly one is in the fresh recreation-batch range
    p31s = {"Q73729880": ["Q1667921"], "Q140446210": []}
    assert choose_hit(["Q73729880", "Q140446210"], "Q999999", p31s) == "Q140446210"


def test_multi_candidate_ambiguous_returns_none():
    # two fresh-range items, neither matching our P31 → genuinely ambiguous, leave it
    p31s = {"Q140446210": ["Q1"], "Q140446211": ["Q2"]}
    assert choose_hit(["Q140446210", "Q140446211"], "Q999999", p31s) is None


def test_fresh_min_floor_excludes_old_deleted_qids():
    # a pre-existing/old item (below the batch floor) is never picked by the fresh fallback
    assert int("Q135579265"[1:]) < FRESH_MIN
    assert int("Q140445965"[1:]) >= FRESH_MIN
