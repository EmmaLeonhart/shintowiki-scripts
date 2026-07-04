"""Tests for the revived update_shikinaisha_lists generator (2026-07-04) —
offline via the module's entity cache: the Address column (P6375, ja
preferred, 同上 refused) and its placement in both row shapes."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shinto_miraheze import update_shikinaisha_lists as u  # noqa: E402


def _seed(qid, claims=None, labels=None):
    u._ENT_CACHE[qid] = {
        "claims": claims or {},
        "labels": labels or {"en": {"value": f"Shrine {qid}"}},
        "sitelinks": {},
    }


def _p6375(text, lang):
    return {"mainsnak": {"datavalue": {"value": {"text": text, "language": lang}}}}


def setup_function(_fn):
    u._ENT_CACHE.clear()


def test_address_cell_prefers_ja():
    _seed("Q1", {"P6375": [_p6375("Some St 5", "en"), _p6375("島根県松江市X1", "ja")]})
    assert u.address_cell("Q1") == "{{lang|ja|島根県松江市X1}}"


def test_address_cell_skips_doujou():
    _seed("Q2", {"P6375": [_p6375("同上", "ja")]})
    assert u.address_cell("Q2") == "—"


def test_address_cell_missing():
    _seed("Q3")
    assert u.address_cell("Q3") == "—"


def test_table_has_address_column_between_notes_and_coords():
    _seed("Q10", {"P6375": [_p6375("島根県A1", "ja")]})
    rows = [(1, "1", "", "Test Shrine", "", "", "Q10")]
    tbl = u.build_shiki_table(rows)
    hdr = tbl.splitlines()[1]
    assert "!! Notes !! Address !! Co-ords" in hdr
    assert "{{lang|ja|島根県A1}}" in tbl


def test_candidate_rows_carry_their_own_address():
    _seed("Q20", {"P460": [
        {"mainsnak": {"datavalue": {"value": {"id": "Q21"}}}},
        {"mainsnak": {"datavalue": {"value": {"id": "Q22"}}}},
    ]})
    _seed("Q21", {"P6375": [_p6375("島根県B1", "ja")]})
    _seed("Q22")
    rows = [(1, "1", "", "Parent Entry", "", "", "Q20")]
    tbl = u.build_shiki_table(rows)
    assert "{{lang|ja|島根県B1}}" in tbl
    # both candidate rows render (second one with the missing-address dash)
    assert tbl.count("|-") == 2
