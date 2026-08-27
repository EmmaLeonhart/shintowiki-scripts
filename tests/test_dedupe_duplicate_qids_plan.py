"""The duplicate-QID planner must decide from Wikidata, not from title shape.

Emma, 2026-08-26: *"if one redirects into another on wikidata then that's clear
evidence you can just redirect it on the shintowiki too."*

The title heuristics this replaced were wrong in both directions. Of the 43 groups
resolvable from the repo on 2026-08-26, 29 stubs were filed under a QID other than
the one in their own title, and 8 pairs carried visibly different shrine names --
the historical Engishiki name beside the modern shrine name -- five of them tagged
as *disputed* identifications. Shape alone cannot tell a real duplicate from a
contested one; a Wikidata redirect can, because the merge already happened there.

These tests are pure: they pass a pre-resolved QID map and never touch the network.
"""
import os
import sys

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "shinto_miraheze")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shinto_miraheze.dedupe_duplicate_qids import (  # noqa: E402
    build_move_plan,
    pick_canonical,
    title_qid,
)


def _reasons(groups):
    return {g["reason"] for g in groups}


def test_title_qid_extracts_only_a_parenthesised_qid():
    assert title_qid("Achiko Shrine (Q135270277)") == "Q135270277"
    assert title_qid("Omiya Shrine") is None
    # A QID in the middle of a name is not a stub marker.
    assert title_qid("Kasano Shrine (Kaga Province)") is None


def test_wikidata_redirect_drives_the_move():
    """The real 2026-08-26 case: stub filed under a QID unlike its own title."""
    state = {
        "Achiko Shrine (Q135270277)": "Q131925939",
        "Omiya Shrine": "Q131925939",
    }
    resolved = {"Q135270277": "Q131925939", "Q131925939": "Q131925939"}
    moves, ambiguous = build_move_plan(state, resolved)
    assert ambiguous == []
    assert len(moves) == 1
    assert moves[0]["from"] == "Achiko Shrine (Q135270277)"
    assert moves[0]["to"] == "Omiya Shrine"
    assert moves[0]["reason"] == "Wikidata redirect → same item"


def test_differing_shrine_names_do_not_block_a_proven_redirect():
    """左内神社 / 阿米都瀬気多知命神社 -- different names, one Wikidata item.

    The old heuristics would still have moved this one, but for the wrong reason
    (stub-shape). What matters is that the evidence, not the name, decides.
    """
    state = {
        "Ametsuseno- Shrine (Q135270422)": "Q134926924",
        "Sanai Shrine": "Q134926924",
    }
    resolved = {"Q135270422": "Q134926924", "Q134926924": "Q134926924"}
    moves, ambiguous = build_move_plan(state, resolved)
    assert [m["from"] for m in moves] == ["Ametsuseno- Shrine (Q135270422)"]
    assert ambiguous == []


def test_stub_without_a_redirect_is_never_auto_moved():
    """THE regression guard.

    A QID-stub title beside a real name is exactly the shape the old rule moved on
    sight. With no Wikidata redirect backing it, the two pages are not known to be
    one entity and merging them would silently pick a side of an open question.
    """
    state = {
        "Some Shrine (Q999001)": "Q999002",
        "Some Shrine": "Q999002",
    }
    resolved = {"Q999001": "Q999001", "Q999002": "Q999002"}  # no redirect
    moves, ambiguous = build_move_plan(state, resolved)
    assert moves == []
    assert _reasons(ambiguous) == {"QID stub with no Wikidata redirect into the group QID"}


def test_both_titles_carry_a_qid_canonical_is_the_one_that_owns_it():
    """The case the old heuristics gave up on as 'both QID stubs'."""
    state = {
        "Hachiman Shrine (Q135187123)": "Q135187123",
        "Hachiman Shrine (Q135190015)": "Q135187123",
    }
    resolved = {"Q135190015": "Q135187123", "Q135187123": "Q135187123"}
    moves, ambiguous = build_move_plan(state, resolved)
    assert ambiguous == []
    assert len(moves) == 1
    assert moves[0]["from"] == "Hachiman Shrine (Q135190015)"
    assert moves[0]["to"] == "Hachiman Shrine (Q135187123)"


def test_template_doc_pair_is_never_a_duplicate():
    """A /doc subpage inherits its parent's {{wikidata link}}.

    21 of the 177 groups were this. The fix is stripping the template from the
    subpage; merging a template into its own documentation would be nonsense.
    """
    state = {
        "Template:When": "Q9002097",
        "Template:When/doc": "Q9002097",
    }
    moves, ambiguous = build_move_plan(state, {"Q9002097": "Q9002097"})
    assert moves == []
    assert _reasons(ambiguous) == {"template/doc pair"}


def test_japanese_script_fallback_still_applies_when_no_qid_is_in_the_title():
    """Nothing for Wikidata to resolve, so the shape heuristic is all there is."""
    state = {"尾張氏": "Q11465311", "Owari clan": "Q11465311"}
    moves, ambiguous = build_move_plan(state, {"Q11465311": "Q11465311"})
    assert ambiguous == []
    assert len(moves) == 1
    assert moves[0]["from"] == "尾張氏"
    assert moves[0]["to"] == "Owari clan"
    assert moves[0]["reason"] == "JP-script → ASCII/rōmaji"


def test_three_page_group_with_two_real_names_is_ambiguous():
    """Q18235752 in the live report. Two plausible canonicals; do not guess."""
    state = {
        "Mononobe Shrine (Higashi-ku, Nagoya)": "Q18235752",
        "Mononobe Shrine (Nagoya)": "Q18235752",
        "Mononoheno Shrine (Q135270316)": "Q18235752",
    }
    resolved = {"Q135270316": "Q18235752", "Q18235752": "Q18235752"}
    moves, ambiguous = build_move_plan(state, resolved)
    assert moves == []
    assert ambiguous and ambiguous[0]["qid"] == "Q18235752"


def test_pick_canonical_returns_none_when_nothing_wins_outright():
    assert pick_canonical("Q1", ["A Shrine", "B Shrine"]) is None
    assert pick_canonical("Q1", ["A (Q2)", "B (Q3)"]) is None
    assert pick_canonical("Q1", ["A (Q1)", "B Shrine"]) == "A (Q1)"
    assert pick_canonical("Q1", ["A (Q2)", "B Shrine"]) == "B Shrine"


def test_resolved_none_falls_back_to_heuristics_only():
    """Offline use must not silently auto-move QID stubs on shape alone."""
    state = {
        "Some Shrine (Q999001)": "Q999002",
        "Some Shrine": "Q999002",
    }
    moves, ambiguous = build_move_plan(state, None)
    assert moves == []
    assert ambiguous


def test_singleton_qids_produce_no_plan():
    state = {"Only Shrine": "Q1", "Other Shrine": "Q2"}
    moves, ambiguous = build_move_plan(state, {})
    assert moves == []
    assert ambiguous == []
