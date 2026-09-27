"""The deity residue report sorts unplaced 祭神 names into red link / linked without an
item / plain text, with how many shrines name each (Emma 2026-09-27: candidates for new
deity items). It reads what the generator already computed and edits nothing."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("WIKIDATA_EMAIL", "test@example.org")
os.environ.setdefault("MIRAHEZE_EMAIL", "test@example.org")

import generate_saijin_deity_research as g  # noqa: E402


def test_residue_is_split_by_kind_and_counted_by_shrine():
    shrine_deities = {
        ("A神社", "Q1"): {"天照大神": {}, "赤神": {}, "無名神": {}},
        ("B神社", "Q2"): {"赤神": {}, "無名神": {}, "頁神": {}},
    }
    all_links = {"天照大神", "赤神", "頁神"}
    all_plain = {"無名神"}
    rep = g.unresolved_report(shrine_deities, all_links, all_plain,
                              resolved={"天照大神": "Q30"}, matched={},
                              missing_links={"赤神"})
    assert rep["red_link"] == {"赤神": 2}
    assert rep["linked_no_item"] == {"頁神": 1}
    assert rep["plain_no_match"] == {"無名神": 2}
