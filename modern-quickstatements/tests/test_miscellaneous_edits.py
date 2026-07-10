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


# ─────────────────────── invariants ───────────────────────

def test_the_queue_never_emits_a_removal():
    lines, _ = misc.build(_ent({}))
    assert lines and all(not l.startswith("-") for l in lines)


def test_assert_no_removals_rejects_a_dash_line():
    with pytest.raises(RuntimeError, match="ADD-only"):
        misc.assert_no_removals(["Q1|P31|Q2", "-Q1|P31|Q3"])


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
