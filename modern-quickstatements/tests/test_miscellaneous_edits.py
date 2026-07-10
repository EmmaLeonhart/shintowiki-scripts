"""The miscellaneous-edits queue (Emma 2026-07-10).

Small, safe, non-urgent fixes that wait behind `conflict_gate` and then drip.

Pinned here: the queue never emits a removal; the Kikuna restoration targets OUR
item (`Q134926804`, which holds the jawiki sitelink) and never the husk
(`Q28069431`, which would recreate a duplicate); the batch shrinks as values land,
so somebody else adding a deity is as good as us adding it; and the file is
registered in `ATOMIC_FILES`, without which it would silently never run.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_miscellaneous_edits as misc  # noqa: E402
import direct_daily_edits as dde  # noqa: E402


def _entity_claim(qid):
    return {"mainsnak": {"datavalue": {"type": "wikibase-entityid",
                                       "value": {"id": qid}}}}


def _string_claim(s):
    return {"mainsnak": {"datavalue": {"type": "string", "value": s}}}


def _ent(claims):
    return {"claims": claims}


def _full_kikuna():
    claims = {}
    for p, v in misc.KIKUNA_STATEMENTS:
        claims.setdefault(p, []).append(
            _string_claim(v.strip('"')) if v.startswith('"') else _entity_claim(v))
    return _ent(claims)


# ─────────────────────── the static fix ───────────────────────

def test_the_shinmei_gu_label_fix_is_queued():
    qid, prop, value, _why = misc.STATIC_EDITS[0]
    assert qid == "Q138565446"
    assert prop == "Len"
    assert value == '"Shinmei-gū (Kanagawa-ku, Yokohama)"'


def test_the_label_fix_drops_the_category_prefix():
    _q, _p, value, _w = misc.STATIC_EDITS[0]
    assert not value.startswith('"Category:')


def test_every_static_edit_records_why_it_is_here():
    for entry in misc.STATIC_EDITS:
        assert len(entry) == 4 and entry[3].strip()


# ─────────────────────── Kikuna targeting ───────────────────────

def test_restoration_targets_our_item_not_the_husk():
    assert misc.KIKUNA_TARGET == "Q134926804"
    assert misc.KIKUNA_HUSK == "Q28069431"


def test_no_line_ever_touches_the_husk():
    lines, _ = misc.build(_ent({}))
    assert not any(misc.KIKUNA_HUSK in l for l in lines)


def test_all_five_deities_are_recorded():
    deities = [v for p, v in misc.KIKUNA_STATEMENTS if p == "P825"]
    assert deities == ["Q317997", "Q455602", "Q461258", "Q1781862", "Q1073668"]


def test_the_full_stripped_property_set_is_recorded():
    props = {p for p, _ in misc.KIKUNA_STATEMENTS}
    assert props == {"P17", "P31", "P131", "P18", "P825", "P856", "P1329", "P2900"}


# ─────────────────────── live-state diffing ───────────────────────

def test_an_empty_target_needs_every_statement():
    lines, _ = misc.build(_ent({}))
    kikuna = [l for l in lines if l.startswith(misc.KIKUNA_TARGET)]
    assert len(kikuna) == len(misc.KIKUNA_STATEMENTS)


def test_a_complete_target_emits_no_restoration_lines():
    lines, _ = misc.build(_full_kikuna())
    assert not any(l.startswith(misc.KIKUNA_TARGET) for l in lines)
    # the static fix still stands
    assert any(l.startswith("Q138565446") for l in lines)


def test_only_absent_deities_are_emitted():
    ent = _ent({"P825": [_entity_claim("Q317997"), _entity_claim("Q455602")]})
    missing = misc.missing_statements(ent, misc.KIKUNA_STATEMENTS)
    assert [v for p, v in missing if p == "P825"] == \
        ["Q461258", "Q1781862", "Q1073668"]


def test_a_string_value_already_present_is_not_re_emitted():
    ent = _ent({"P856": [_string_claim("http://www.kikunajinja.jp/profile/")]})
    missing = misc.missing_statements(ent, misc.KIKUNA_STATEMENTS)
    assert not any(p == "P856" for p, _ in missing)


def test_someone_else_adding_a_deity_shrinks_the_batch():
    """Emma: 'ideally we would want other people to do it.'"""
    before, _ = misc.build(_ent({}))
    after, _ = misc.build(_ent({"P825": [_entity_claim("Q461258")]}))
    assert len(after) == len(before) - 1


def test_a_deleted_target_refuses_rather_than_creating():
    lines, notes = misc.build(None)
    assert not any(l.startswith(misc.KIKUNA_TARGET) for l in lines)
    assert any("CREATION" in n for n in notes)


# ─────────────────────── address removals ───────────────────────

def _addr_claim(text, lang="ja"):
    return {"mainsnak": {"datavalue": {"type": "monolingualtext",
                                       "value": {"text": text, "language": lang}}}}


def _live(*addresses, qid=None):
    qid = qid or misc.ADDRESS_REMOVALS[0][0]
    return {qid: set(addresses)}


def test_seventeen_removals_were_decided():
    assert len(misc.ADDRESS_REMOVALS) == 17


def test_no_removal_drops_the_address_it_means_to_keep():
    for qid, drop, keep, _why in misc.ADDRESS_REMOVALS:
        assert drop != keep, qid


def test_no_two_removals_target_the_same_item():
    qids = [q for q, _d, _k, _w in misc.ADDRESS_REMOVALS]
    assert len(qids) == len(set(qids))


def test_every_removal_records_why_it_is_here():
    for entry in misc.ADDRESS_REMOVALS:
        assert len(entry) == 4 and entry[3].strip()


def test_no_address_contains_a_quote_that_would_break_the_line():
    for _q, drop, keep, _w in misc.ADDRESS_REMOVALS:
        assert '"' not in drop and '"' not in keep


def test_the_removal_line_is_a_monolingual_japanese_value():
    assert misc.removal_line("Q1", "東京都") == '-Q1|P6375|ja:"東京都"'


def _why(skipped, qid):
    return dict(skipped)[qid]


def test_a_removal_is_emitted_when_both_addresses_are_live():
    qid, drop, keep, _w = misc.ADDRESS_REMOVALS[0]
    lines, skipped = misc.address_removal_lines(_live(drop, keep))
    assert lines == [misc.removal_line(qid, drop)]
    assert qid not in dict(skipped)


def test_a_removal_is_skipped_once_it_has_landed():
    qid, _drop, keep, _w = misc.ADDRESS_REMOVALS[0]
    lines, skipped = misc.address_removal_lines(_live(keep))
    assert not lines and _why(skipped, qid) == "already removed"


def test_a_removal_is_refused_when_it_would_leave_no_address():
    """Somebody else deleted the good address; dropping the bad one leaves none."""
    qid, drop, _keep, _w = misc.ADDRESS_REMOVALS[0]
    lines, skipped = misc.address_removal_lines(_live(drop))
    assert not lines
    assert "refusing to drop the last one" in _why(skipped, qid)


def test_a_removal_is_refused_when_the_item_is_gone():
    lines, skipped = misc.address_removal_lines({})
    assert not lines and len(skipped) == len(misc.ADDRESS_REMOVALS)
    assert all(why == "item is gone" for _q, why in skipped)


def test_addresses_are_read_off_the_item_in_japanese_only():
    claims = {"P6375": [_addr_claim("東京都"), _addr_claim("Tokyo", lang="en")]}
    assert misc.address_values(claims) == {"東京都"}


def test_a_novalue_address_does_not_crash_the_reader():
    claims = {"P6375": [{"mainsnak": {"snaktype": "novalue"}}, _addr_claim("東京都")]}
    assert misc.address_values(claims) == {"東京都"}


def test_build_emits_the_removals_and_they_pass_the_invariant():
    qid, drop, keep, _w = misc.ADDRESS_REMOVALS[0]
    lines, _notes = misc.build(_ent({}), _live(drop, keep))
    assert misc.removal_line(qid, drop) in lines


def test_build_without_live_state_emits_no_removal():
    """Calling build() with no live addresses must never guess."""
    lines, _ = misc.build(_ent({}))
    assert not any(l.startswith("-") for l in lines)


def test_the_daily_editor_parses_every_removal_line():
    for qid, drop, _keep, _w in misc.ADDRESS_REMOVALS:
        p = dde.parse_qs_line(misc.removal_line(qid, drop))
        assert p["is_removal"] and p["entity"] == qid
        assert p["property"] == "P6375"
        assert p["value"]["type"] == "monolingualtext"
        assert p["value"]["value"] == {"text": drop, "language": "ja"}


# ─────────────────────── invariants ───────────────────────

def test_the_queue_emits_no_removal_it_was_not_asked_for():
    lines, _ = misc.build(_ent({}))
    assert lines and all(not l.startswith("-") for l in lines)


def test_an_unlisted_removal_is_rejected():
    with pytest.raises(RuntimeError, match="STATIC_REMOVALS"):
        misc.assert_removals_enumerated(["Q1|P31|Q2", "-Q1|P31|Q3"])


def test_a_listed_removal_is_allowed():
    qid, drop, _keep, _why = misc.ADDRESS_REMOVALS[0]
    misc.assert_removals_enumerated([misc.removal_line(qid, drop)])


def test_a_listed_removal_of_a_different_address_is_still_rejected():
    """The enumeration is by line, not by item — one typo must not open the item up."""
    qid, drop, _keep, _why = misc.ADDRESS_REMOVALS[0]
    with pytest.raises(RuntimeError, match="STATIC_REMOVALS"):
        misc.assert_removals_enumerated([misc.removal_line(qid, drop + "1")])


def test_the_repurposed_item_is_never_touched():
    """Q123044569 is on hold: actively edited and actively misleading."""
    lines, _ = misc.build(_ent({}))
    assert not any("Q123044569" in l for l in lines)


def test_output_file_is_registered_in_atomic_files():
    """An unregistered batch is never executed — the 2026-07-09 lesson."""
    assert misc.OUTPUT_FILE in dde.ATOMIC_FILES


def test_the_retired_kikuna_batch_is_no_longer_registered():
    assert "kikuna_restoration.txt" not in dde.ATOMIC_FILES


def test_line_shape():
    assert misc.qs_line("Q1", "P825", "Q2") == "Q1|P825|Q2"
    assert misc.qs_line("Q1", "Len", '"X"') == 'Q1|Len|"X"'
