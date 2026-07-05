"""Unit tests for the pure ill-parsing / matching logic of crossref_deleted_labels.

The fandom I/O (search_pages/fetch_content/history) is exercised against the live
wiki at run time; these tests cover the deterministic parsing that decides which
ill matches a label and what content it yields.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import crossref_deleted_labels as cx


def test_parse_ill_langlinks_and_real_qid():
    got = cx.parse_ill("Atsuta Shrine|ja|熱田神宮|fr|Atsuta-jingū|qid=Q482065|lt=Atsuta Jingū")
    assert got["label"] == "Atsuta Jingū"           # lt= overrides positional[0]
    assert got["langlinks"] == {"ja": "熱田神宮", "fr": "Atsuta-jingū"}
    assert got["qid"] == "Q482065"


def test_parse_ill_deleted_qid_is_not_a_qid():
    got = cx.parse_ill("Niwa-tsume no Mikoto|ja|庭津女命|qid=DELETED_QID")
    assert got["label"] == "Niwa-tsume no Mikoto"
    assert got["langlinks"] == {"ja": "庭津女命"}
    assert got["qid"] == ""                          # DELETED_QID is ignored


def test_parse_ill_dd_param_recovers_qid():
    got = cx.parse_ill("Agata Shrine (Izumo)|ja|縣神社 (出雲市)|qid=DELETED_QID|dd=Q135500707")
    assert got["qid"] == "Q135500707"                # dd= holds the preserved QID


def test_ill_matches_label():
    assert cx.ill_matches_label("Mori-no-Kami|ja|森之神", "Mori-no-Kami")
    assert not cx.ill_matches_label("Other Kami|ja|X", "Mori-no-Kami")
    # lt= display override still matches on the target positional
    assert cx.ill_matches_label("Shikinaisha|zh|式內社|lt=Shikinaisha", "Shikinaisha")


def test_find_ill_picks_the_right_one_among_many():
    text = (
        "Intro {{ill|Some Other|ja|X|qid=Q1}} middle "
        "{{ill|Niwa-tsume no Mikoto|ja|庭津女命|qid=DELETED_QID}} end"
    )
    got = cx.find_ill(text, "Niwa-tsume no Mikoto")
    assert got is not None
    assert got["langlinks"] == {"ja": "庭津女命"}
    assert cx.find_ill(text, "Nonexistent") is None


def test_page_wikidata_qid():
    assert cx.page_wikidata_qid("foo {{wikidata link|Q123}} bar") == "Q123"
    assert cx.page_wikidata_qid("no link here") is None


def test_page_signals():
    text = (
        "{{wikidata link|Q42}}\n[[ja:天神社]]\n"
        "[[Category:Shinto shrines in Gunma Prefecture]]\n"
        "[[Category:Buildings and structures in Gunma Prefecture]]\n"
    )
    s = cx.page_signals(text)
    assert s["page_wikidata_qid"] == "Q42"
    assert s["ja_sitelink"] == "天神社"
    assert len(s["categories"]) == 2
    empty = cx.page_signals("")
    assert empty == {"page_wikidata_qid": None, "ja_sitelink": None, "categories": []}


def test_md_cell_escapes_pipe():
    assert cx.md_cell("a|b") == "a\\|b"
    assert cx.md_cell(None) == ""


def test_render_smoke():
    results = [{
        "qid": "Q135579706", "label": "Niwa-tsume no Mikoto", "size": 311, "bucket": "empty-item",
        "fandom_page": "Takeminakata Shrine", "host_pages": ["Takeminakata Shrine"],
        "langlinks": {"ja": "庭津女命"}, "current_ill_qid": "", "recovered_qid": "Q135579706",
        "qid_source": "history(2026-05-14)", "page_wikidata_qid": None, "ja_sitelink": "諏訪",
        "categories": ["Kami"], "matched": True, "qid_matches_rag": True,
    }]
    out = cx.render(results)
    assert "Niwa-tsume no Mikoto" in out and "matches the RAG" in out and "✓" in out
