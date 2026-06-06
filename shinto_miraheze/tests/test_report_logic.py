"""Unit tests for the pure logic of the render-once report scripts.

These don't touch the wiki — they exercise the parsing/rendering functions in
``report_double_qid_tail`` and ``report_multiple_wikidata_links`` with realistic
wikitext, so the deterministic logic is verified without wiki credentials (the
end-to-end run happens in CI where the bot creds live).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import report_double_qid_tail as rdqt  # noqa: E402
import report_multiple_wikidata_links as rmwl  # noqa: E402


# ─── report_double_qid_tail.extract_targets ──────────────────

def test_extract_targets_basic_dab_page():
    text = (
        "# [[:Category:Female Imperial Family Members before the Kofun Period]]\n"
        "# [[:Category:Female imperial family members before the Kofun period]]\n"
        "[[Category:double category qids]]\n"
        "[[Category:Pages without wikidata]]\n"
    )
    targets = rdqt.extract_targets(text)
    assert targets == [
        "Female Imperial Family Members before the Kofun Period",
        "Female imperial family members before the Kofun period",
    ]


def test_extract_targets_excludes_self_tags():
    # Only the maintenance tags present → no competing targets.
    text = "[[Category:Double category qids]]\n[[Category:Pages without wikidata]]\n"
    assert rdqt.extract_targets(text) == []


def test_extract_targets_dedupes_and_strips_pipes():
    text = "* [[:Category:Foo|Foo]]\n* [[Category:Foo]]\n* [[:Category:Bar]]\n"
    assert rdqt.extract_targets(text) == ["Foo", "Bar"]


def test_double_qid_report_empty():
    out = rdqt.build_report([])
    assert "Tail is empty" in out
    assert "[[Category:Maintenance reports]]" in out


def test_double_qid_report_renders_targets():
    entries = [{
        "title": "Q123",
        "targets": [
            {"name": "Foo", "info": {"exists": True, "count": 5, "qid": "Q123"}},
            {"name": "Bar", "info": {"exists": False, "count": 0, "qid": None}},
        ],
    }]
    out = rdqt.build_report(entries)
    assert "[[Q123]]" in out
    assert "[[:Category:Foo]] — 5 member(s), QID: Q123" in out
    assert "does not exist" in out


# ─── report_multiple_wikidata_links QID extraction ───────────

def test_wd_link_qid_re_extracts_multiple():
    text = (
        "Some article.\n"
        "{{wikidata link|Q111|en|Foo}}\n"
        "{{wikidata link|Q222}}\n"
        "{{wikidata link}}\n"  # blank — no QID, must not match
    )
    qids = [m.group(1).upper() for m in rmwl.WD_LINK_QID_RE.finditer(text)]
    assert qids == ["Q111", "Q222"]


def test_multiple_links_report_empty():
    out = rmwl.build_report({}, {})
    assert "No pages currently carry multiple wikidata links" in out
    assert "[[Category:Maintenance reports]]" in out


def test_multiple_links_report_renders_labels():
    page_qids = {"Some Shrine": ["Q111", "Q222"]}
    labels = {
        "Q111": {"label": "Shrine A", "description": "a shrine", "missing": False},
        "Q222": {"label": "", "description": "(deleted/missing item)", "missing": True},
    }
    out = rmwl.build_report(page_qids, labels)
    assert "[[Some Shrine]] (2 links)" in out
    assert "[[d:Q111|Q111]]: Shrine A — a shrine" in out
    assert "[[d:Q222|Q222]]" in out
    assert "(no English label)" in out
