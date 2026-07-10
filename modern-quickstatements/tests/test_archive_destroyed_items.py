"""Preservation of items ブルーノ・プラス damaged (Emma 2026-07-10).

The load-bearing properties:

  * only *removals* count as destructive — additions and description rewrites don't;
  * the archived revision is the one immediately before their FIRST destructive edit,
    and is never overwritten by a later, already-damaged state;
  * a revision by the watched user themselves is never taken as the "undamaged" one.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import archive_destroyed_items as ar  # noqa: E402


def edit(title, ts, comment):
    return {"title": title, "timestamp": ts, "comment": comment}


# ─────────────────────── what counts as destructive ───────────────────────

@pytest.mark.parametrize("comment", [
    "/* wbremoveclaims-remove:1| */ [[Property:P825]]: [[Q461258]]",
    "/* wbsetlabel-remove:1|en */ Kikuna Shrine",
    "/* wbsetdescription-remove:1|ja */ 横浜市港北区に所在する神社",
    "/* wbsetaliases-remove:1|ja */ 八幡神社",
    "/* wbsetsitelink-remove:1|jawiki */ 菊名神社",
])
def test_removals_are_destructive(comment):
    assert ar.is_destructive(comment)


@pytest.mark.parametrize("comment", [
    "/* wbsetclaim-create:2||1 */ [[Property:P625]]: 35°N",
    "/* wbsetdescription-set:1|ja */ 神奈川県小田原市にある神社",
    "/* wbsetdescription-add:1|ja */ …",
    "/* wbsetlabel-add:1|ja */ 大美和神社",
    "/* wbsetsitelink-add:1|jawiki */ 大美和神社",
    "/* wbeditentity-create:2|ja */ 琵琶島神社",
    "",
    None,
])
def test_additions_and_rewrites_are_not_destructive(comment):
    assert not ar.is_destructive(comment)


def test_description_set_is_not_a_removal_even_though_it_overwrites():
    """They rewrote 141 descriptions. That is not what we archive for."""
    assert not ar.is_destructive("/* wbsetdescription-set:1|ja */ x")


# ─────────────────────── grouping ───────────────────────

def test_only_item_pages_are_considered():
    edits = [edit("Q1", "2026-07-09T06:25:00Z", "/* wbremoveclaims-remove:1| */ x"),
             edit("Wikidata:Project chat", "2026-07-09T07:00:00Z",
                  "/* wbremoveclaims-remove:1| */ x"),
             edit("Talk:Q5", "2026-07-09T07:00:00Z", "/* wbremoveclaims-remove:1| */ x")]
    assert sorted(ar.destructive_by_item(edits)) == ["Q1"]


def test_items_with_only_additions_are_not_archived():
    edits = [edit("Q1", "2026-07-09T06:25:00Z", "/* wbsetclaim-create:2||1 */ x")]
    assert ar.destructive_by_item(edits) == {}


def test_edits_are_ordered_oldest_first():
    edits = [edit("Q1", "2026-07-10T02:00:00Z", "/* wbremoveclaims-remove:1| */ b"),
             edit("Q1", "2026-07-09T06:25:00Z", "/* wbremoveclaims-remove:1| */ a")]
    got = ar.destructive_by_item(edits)["Q1"]
    assert [e["timestamp"] for e in got] == \
        ["2026-07-09T06:25:00Z", "2026-07-10T02:00:00Z"]


def test_first_destructive_timestamp_is_the_earliest():
    edits = [edit("Q1", "2026-07-10T02:00:00Z", "/* wbremoveclaims-remove:1| */ b"),
             edit("Q1", "2026-07-09T06:25:00Z", "/* wbremoveclaims-remove:1| */ a")]
    item = ar.destructive_by_item(edits)["Q1"]
    assert ar.first_destructive_timestamp(item) == "2026-07-09T06:25:00Z"


def test_a_later_destructive_edit_does_not_move_the_capture_point():
    """The ORIGINAL state is the point — not the state after the first round."""
    early = edit("Q1", "2026-07-09T06:25:00Z", "/* wbremoveclaims-remove:1| */ a")
    late = edit("Q1", "2026-08-01T00:00:00Z", "/* wbremoveclaims-remove:1| */ b")
    item = ar.destructive_by_item([late, early])["Q1"]
    assert ar.first_destructive_timestamp(item) == early["timestamp"]


# ─────────────────────── removal summaries ───────────────────────

def test_removed_properties_are_listed():
    item = [edit("Q1", "t1", "/* wbremoveclaims-remove:1| */ [[Property:P825]]: [[Q1]]"),
            edit("Q1", "t2", "/* wbremoveclaims-remove:1| */ [[Property:P18]]: x")]
    props, terms = ar.summarize_removals(item)
    assert props == ["P825", "P18"]
    assert terms == []


def test_removed_terms_are_listed_with_their_language():
    item = [edit("Q1", "t1", "/* wbsetlabel-remove:1|en */ Kikuna Shrine"),
            edit("Q1", "t2", "/* wbsetdescription-remove:1|ja */ x")]
    props, terms = ar.summarize_removals(item)
    assert props == []
    assert terms == ["label:en", "description:ja"]


def test_a_property_named_in_an_addition_is_not_counted_as_removed():
    item = [edit("Q1", "t1", "/* wbsetclaim-create:2||1 */ [[Property:P625]]: x")]
    props, _ = ar.summarize_removals(item)
    assert props == []


# ─────────────────────── the archived snapshot ───────────────────────

ENTITY = {
    "labels": {"en": {"value": "Kikuna Shrine"}, "ja": {"value": "菊名神社"}},
    "claims": {"P825": [{}, {}, {}, {}, {}], "P18": [{}], "P31": [{}]},
    "sitelinks": {},
}


def test_entity_summary_counts_statements_not_properties():
    s = ar.entity_summary(ENTITY)
    assert s["properties"] == ["P18", "P31", "P825"]
    assert s["statement_count"] == 7
    assert s["en_label"] == "Kikuna Shrine"


def test_entity_summary_survives_an_empty_entity():
    s = ar.entity_summary({})
    assert s["statement_count"] == 0 and s["labels"] == 0


def test_entity_summary_handles_sitelinks_serialized_as_a_list():
    """An item with no sitelinks serializes them as [] , not {}."""
    s = ar.entity_summary({"labels": {}, "claims": {}, "sitelinks": []})
    assert s["sitelinks"] == []


def test_archive_path_is_per_item():
    assert ar.archive_path("Q42").endswith(os.path.join("destroyed_items", "Q42.json"))


# ─────────────── the parent-revision anchor (an off-by-one that bit) ───────────────

def test_pre_damage_revid_is_the_parent_of_the_first_destructive_edit():
    """`rvstart` is INCLUSIVE. Anchoring on the timestamp captured the blanking
    itself for the seven items they created — Q140476265 was archived with 0 labels."""
    item = [{"timestamp": "2026-07-10T00:35:34Z", "revid": 2515714838,
             "parentid": 2515714306, "comment": "/* wbsetlabel-remove:1|ja */ x"},
            {"timestamp": "2026-07-10T00:35:35Z", "revid": 2515714900,
             "parentid": 2515714838, "comment": "/* wbsetdescription-remove:1|ja */ x"}]
    assert ar.pre_damage_revid(item) == 2515714306


def test_pre_damage_revid_never_returns_the_destructive_revision_itself():
    item = [{"timestamp": "t", "revid": 99, "parentid": 98, "comment": "x"}]
    assert ar.pre_damage_revid(item) != 99


def test_an_item_created_by_the_destructive_edit_has_no_parent():
    item = [{"timestamp": "t", "revid": 99, "parentid": 0, "comment": "x"}]
    assert ar.pre_damage_revid(item) is None


def test_is_own_creation_flags_their_own_pre_damage_revision():
    assert ar.is_own_creation([], {"user": ar.WATCHED_USER})
    assert not ar.is_own_creation([], {"user": "Higa4"})
    assert not ar.is_own_creation([], None)
