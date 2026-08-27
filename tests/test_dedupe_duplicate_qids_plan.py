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
    assert pick_canonical("Q1", ["A (Q2)", "B Shrine"]) == "B Shrine"


def test_a_real_name_beats_a_qid_stub_even_when_the_stub_owns_the_qid():
    """This assertion used to say the opposite, and the opposite was the bug.

    A title like ``Takanono Shrine (Q135040588)`` is a generator PLACEHOLDER. When
    the group is ``X`` plus ``X (Qnnn)`` and the stub's own QID happens to BE the
    group's, preferring the stub made it canonical — then nothing was left to prove,
    because the real-named page carries no QID in its title to resolve. The whole
    group fell into the ambiguous bucket.

    Measured 2026-08-27: 16 of the 18 groups filed as "QID stub with no Wikidata
    redirect" were this, i.e. nearly the entire unexplained residue of the report.
    """
    assert pick_canonical("Q1", ["A (Q1)", "B Shrine"]) == "B Shrine"


def test_qid_ownership_still_decides_between_two_stubs():
    """With no real name to prefer, owning the group QID is the tiebreak."""
    assert pick_canonical("Q1", ["A (Q1)", "B (Q2)"]) == "A (Q1)"
    assert pick_canonical("Q1", ["A (Q2)", "B (Q1)"]) == "B (Q1)"


def test_two_real_names_are_never_guessed_between():
    assert pick_canonical("Q1", ["A Shrine", "B Shrine", "C (Q1)"]) is None


def test_the_stub_owning_the_qid_becomes_a_provable_move_not_an_ambiguity():
    """The end-to-end shape of the 16: it should now plan, not fall through."""
    state = {"Hijiri Shrine (Q11611103)": "Q11611103",
             "Hijiri Shrine (Izumi, Osaka)": "Q11611103"}
    moves, ambiguous = build_move_plan(state, {"Q11611103": "Q11611103"})
    assert ambiguous == []
    assert len(moves) == 1
    assert moves[0]["from"] == "Hijiri Shrine (Q11611103)"
    assert moves[0]["to"] == "Hijiri Shrine (Izumi, Osaka)"


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


# ── property dumps are not real names ─────────────────────────────────────
#
# `pick_canonical` reads titles, and a Wikidata property dump -- an infobox plus
# `== instance of (P31) ==` sections -- carries no `(Qnnn)` suffix, so it looks
# exactly like an article. Every dump opposite a real article became a decision
# handed to a human: 12 of the 25 such groups measured on 2026-08-27.

DUMP = 94        # measured: dumps land at 90-174 bytes of prose
ARTICLE = 1812   # measured: real articles at 587-11,419


def test_a_property_dump_does_not_count_as_a_real_name():
    state = {"Mononobe Shrine (Higashi-ku, Nagoya)": "Q18235752",
             "Mononobe Shrine (Nagoya)": "Q18235752"}
    prose = {"Mononobe Shrine (Higashi-ku, Nagoya)": ARTICLE,
             "Mononobe Shrine (Nagoya)": DUMP}
    moves, ambiguous = build_move_plan(state, {"Q18235752": "Q18235752"}, prose)
    assert ambiguous == []
    assert len(moves) == 1
    assert moves[0]["from"] == "Mononobe Shrine (Nagoya)"
    assert moves[0]["to"] == "Mononobe Shrine (Higashi-ku, Nagoya)"
    assert moves[0]["reason"] == "property dump → article (same QID)"


def test_two_real_articles_are_still_a_human_call():
    state = {"Benzaiten": "Q818468", "Benzaiten shrines": "Q818468"}
    prose = {"Benzaiten": 11419, "Benzaiten shrines": 588}
    moves, ambiguous = build_move_plan(state, {"Q818468": "Q818468"}, prose)
    assert moves == []
    assert ambiguous and "real names" in ambiguous[0]["reason"]


def test_two_dumps_are_not_ranked_against_each_other():
    """Nothing to prefer; picking one would be a guess dressed as a rule."""
    state = {"Shioe Shrine": "Q135187121", "Shionoe Shrine": "Q135187121"}
    prose = {"Shioe Shrine": 32, "Shionoe Shrine": 32}
    moves, ambiguous = build_move_plan(state, {"Q135187121": "Q135187121"}, prose)
    assert moves == []
    assert ambiguous


def test_an_unmeasured_page_is_treated_as_an_article():
    """Unknown must never demote something real — the safe direction."""
    state = {"Measured Shrine": "Q1", "Unmeasured Shrine": "Q1"}
    prose = {"Measured Shrine": ARTICLE}          # the other was never fetched
    moves, ambiguous = build_move_plan(state, {"Q1": "Q1"}, prose)
    assert moves == []
    assert ambiguous


def test_omitting_prose_lengths_keeps_the_old_behaviour():
    state = {"Mononobe Shrine (Higashi-ku, Nagoya)": "Q18235752",
             "Mononobe Shrine (Nagoya)": "Q18235752"}
    moves, ambiguous = build_move_plan(state, {"Q18235752": "Q18235752"})
    assert moves == []
    assert ambiguous


def test_a_dump_beside_a_stub_and_an_article_resolves_to_the_article():
    """The three-page Mononobe group as it actually is on the wiki."""
    state = {"Mononobe Shrine (Higashi-ku, Nagoya)": "Q18235752",
             "Mononobe Shrine (Nagoya)": "Q18235752",
             "Mononoheno Shrine (Q135270316)": "Q18235752"}
    prose = {"Mononobe Shrine (Higashi-ku, Nagoya)": ARTICLE,
             "Mononobe Shrine (Nagoya)": DUMP}
    resolved = {"Q135270316": "Q18235752", "Q18235752": "Q18235752"}
    moves, ambiguous = build_move_plan(state, resolved, prose)
    assert ambiguous == []
    assert {m["from"] for m in moves} == {"Mononobe Shrine (Nagoya)",
                                         "Mononoheno Shrine (Q135270316)"}
    assert {m["to"] for m in moves} == {"Mononobe Shrine (Higashi-ku, Nagoya)"}
    assert {m["reason"] for m in moves} == {"property dump → article (same QID)",
                                           "Wikidata redirect → same item"}


def test_the_dump_rule_does_not_apply_to_templates():
    """Prose length says nothing about a template.

    Templates carry little prose by nature, so the dump test marks almost any of
    them a dump and the tie-break then picks whichever has more words. Measured
    2026-08-27, that proposed Template:Topic category -> Template:テーマカテゴリ
    and Template:Japanese year -> Template:和暦 — pointing English at Japanese and
    inverting this wiki's own convention.
    """
    state = {"Template:Topic category": "Q13413959",
             "Template:テーマカテゴリ": "Q13413959"}
    prose = {"Template:Topic category": 40, "Template:テーマカテゴリ": 300}
    moves, ambiguous = build_move_plan(state, {"Q13413959": "Q13413959"}, prose)
    assert not any(m["reason"].startswith("property dump") for m in moves)


def test_a_malformed_title_is_never_made_canonical():
    """`Mishima Shrine (Minamiizu )` has a trailing space in its disambiguator.

    Redirecting a well-formed page into it would make the typo the canonical name.
    """
    state = {"Mishima Shrine (Iruma)": "Q134930713",
             "Mishima Shrine (Minamiizu )": "Q134930713"}
    prose = {"Mishima Shrine (Iruma)": DUMP,
             "Mishima Shrine (Minamiizu )": ARTICLE}
    moves, ambiguous = build_move_plan(state, {"Q134930713": "Q134930713"}, prose)
    assert moves == []
    assert ambiguous


def test_a_lone_real_name_stays_canonical_even_when_it_is_a_dump():
    """The regression I shipped and caught by measuring.

    A dump is a page that needs CONTENT, not one with the wrong title. Treating it
    as disqualified pushed resolvable groups into the ambiguous bucket — the whole
    plan went 131 -> 103 moves and 46 -> 75 ambiguous before this was scoped to
    multi-real-name groups only.
    """
    state = {"Some Shrine (Q900001)": "Q900001", "Some Shrine": "Q900001"}
    prose = {"Some Shrine": DUMP}
    moves, ambiguous = build_move_plan(state, {"Q900001": "Q900001"}, prose)
    assert ambiguous == []
    assert len(moves) == 1
    assert moves[0]["to"] == "Some Shrine"


# ── Wikidata's own naming, applied strictly ───────────────────────────────
#
# Exactly one page must EQUAL the item's English label and every other
# real-named page must be a registered English alias. Wikidata then already says
# these are other names for one thing. The strictness is the whole point.

def test_variant_romanisations_resolve_via_label_and_alias():
    state = {"Shioe Shrine": "Q135187121", "Shionoe Shrine": "Q135187121"}
    labels = {"Q135187121": ("Shioe Shrine", {"Shionoe Shrine"})}
    moves, ambiguous = build_move_plan(state, {"Q135187121": "Q135187121"},
                                       None, labels)
    assert ambiguous == []
    assert len(moves) == 1
    assert moves[0]["from"] == "Shionoe Shrine"
    assert moves[0]["to"] == "Shioe Shrine"
    assert moves[0]["reason"] == "Wikidata alias → label title (same item)"


def test_a_different_subject_sharing_a_qid_is_not_an_alias_and_must_not_resolve():
    """`Benzaiten shrines` is a class of shrines, not another name for the deity.

    This is the case the rule exists to decline. Q818468's only English alias is
    "Benten"; a looser label-wins rule would have merged a 588-byte article into
    an 11,419-byte one on the strength of a shared QID that is itself the defect.
    """
    state = {"Benzaiten": "Q818468", "Benzaiten shrines": "Q818468"}
    labels = {"Q818468": ("Benzaiten", {"Benten"})}
    moves, ambiguous = build_move_plan(state, {"Q818468": "Q818468"}, None, labels)
    assert moves == []
    assert ambiguous


def test_a_label_with_no_aliases_gives_no_verdict():
    """Amatsu Shrine / Amatsu Shrine (Itoigawa): label matches one, no aliases."""
    state = {"Amatsu Shrine": "Q172253", "Amatsu Shrine (Itoigawa)": "Q172253"}
    labels = {"Q172253": ("Amatsu Shrine", set())}
    moves, ambiguous = build_move_plan(state, {"Q172253": "Q172253"}, None, labels)
    assert moves == []
    assert ambiguous


def test_no_page_matching_the_label_gives_no_verdict():
    """Both Achi titles are disambiguated; neither equals the bare label."""
    state = {"Achi Shrine (Achi Village)": "Q11657447",
             "Achi Shrine (Achi)": "Q11657447"}
    labels = {"Q11657447": ("Achi Shrine", {"Achino shrine (Ronsha 1)"})}
    moves, ambiguous = build_move_plan(state, {"Q11657447": "Q11657447"}, None, labels)
    assert moves == []
    assert ambiguous


def test_the_label_rule_outranks_the_prose_tie_break():
    """Two dumps with a label/alias pair must resolve, not fall to `no articles`.

    Ordering bug caught by measuring: the prose branch returned None for two dumps
    before the label rule was reached, so Shioe/Shionoe stayed ambiguous and the
    whole rule produced zero moves.
    """
    state = {"Shioe Shrine": "Q135187121", "Shionoe Shrine": "Q135187121"}
    prose = {"Shioe Shrine": 32, "Shionoe Shrine": 32}   # both property dumps
    labels = {"Q135187121": ("Shioe Shrine", {"Shionoe Shrine"})}
    moves, ambiguous = build_move_plan(state, {"Q135187121": "Q135187121"},
                                       prose, labels)
    assert ambiguous == []
    assert [m["from"] for m in moves] == ["Shionoe Shrine"]


def test_a_template_beside_a_mainspace_article_is_a_wrong_link_not_a_merge():
    """A navbox is not the concept it navigates.

    Q1656379 is "Shinto shrine with the highest rank in a province"; the article
    `Ichinomiya` is that concept and `Template:Ichinomiya` is a navigation box that
    merely carries the same {{wikidata link}}. Merging would delete a navbox into
    an article. The fix belongs on the template's link.
    """
    state = {"Ichinomiya": "Q1656379", "Template:Ichinomiya": "Q1656379"}
    moves, ambiguous = build_move_plan(state, {"Q1656379": "Q1656379"})
    assert moves == []
    assert len(ambiguous) == 1
    assert "wrong {{wikidata link}}" in ambiguous[0]["reason"]


def test_two_templates_are_still_a_normal_cross_language_duplicate():
    """Template:警告 beside Template:Warning IS a merge — the rule must not eat it."""
    state = {"Template:Warning": "Q5528794", "Template:警告": "Q5528794"}
    moves, ambiguous = build_move_plan(state, {"Q5528794": "Q5528794"})
    assert not any("wrong {{wikidata link}}" in g["reason"] for g in ambiguous)
    assert moves and moves[0]["from"] == "Template:警告"
    assert moves[0]["to"] == "Template:Warning"


def test_a_category_beside_a_mainspace_page_is_also_a_wrong_link():
    state = {"Asia": "Q999", "Category:Asia templates": "Q999"}
    moves, ambiguous = build_move_plan(state, {"Q999": "Q999"})
    assert moves == []
    assert "wrong {{wikidata link}}" in ambiguous[0]["reason"]
