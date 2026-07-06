"""Unit tests for the pure logic in build_recreation_quickstatements."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import build_recreation_quickstatements as b  # noqa: E402


def test_qs_escapes():
    assert b.qs('a "quoted" | name') == '"a \'quoted\' / name"'


def test_has_cjk():
    assert b._has_cjk("安倍季弘")
    assert b._has_cjk("ヤングビーナス")   # katakana
    assert not b._has_cjk("Amanomikemunushi")


def test_valid_label_rejects_romaji_ja():
    # a romaji value in the ja slot is a malformed ill — reject as a Japanese label.
    assert not b._valid_label("ja", "Amanomikemunushi no Kami")
    assert b._valid_label("ja", "安倍季弘")
    assert not b._valid_label("zh", "Boseikyo")
    # Latin-script languages pass through.
    assert b._valid_label("de", "Abe no Kiyohiro")
    assert b._valid_label("en", "Akama Shrine")


def _rec(**enr):
    base = {"recovered_label": "Abe no Kiyohiro",
            "fandom": {"langlinks": {"ja": "安倍季弘"}, "host_pages": ["Abe no Yasuchika"]},
            "enrichment": {"description_en": "Japanese historical figure",
                           "p31": "Q5", "p31_property": "P31"}}
    base["enrichment"].update(enr)
    return base


def test_block_human_with_relations():
    rec = _rec(relations=[{"property": "P22", "target_qid": "Q11450335"},
                          {"property": "P21", "target_qid": "Q6581097"},
                          {"property": "P25", "target_qid": None}])  # None → skipped
    lines = b.block(rec, "Q135500627")
    assert "CREATE" in lines
    assert 'LAST\tLen\t"Abe no Kiyohiro"' in lines
    assert 'LAST\tLja\t"安倍季弘"' in lines
    assert 'LAST\tDen\t"Japanese historical figure"' in lines
    assert 'LAST\tP31\tQ5' in lines
    assert 'LAST\tP22\tQ11450335' in lines
    assert 'LAST\tP21\tQ6581097' in lines
    assert not any("P25" in ln for ln in lines)          # relation w/o live QID skipped
    assert lines[0].startswith("# recreate Abe no Kiyohiro (was Q135500627)")


def test_block_place_gets_p17_and_sitelink():
    rec = {"recovered_label": "Agata Shrine (Yokkaichi)",
           "fandom": {"langlinks": {"ja": "縣神社 (四日市市)"}, "host_pages": ["Agata Shrine"],
                      "ja_sitelink": "縣神社 (四日市市)"},
           "enrichment": {"description_en": "Shinto shrine in Japan", "p31": "Q845945",
                          "p31_property": "P31", "p17": "Q17"}}
    lines = b.block(rec, "Q135500704")
    assert 'LAST\tP31\tQ845945' in lines
    assert 'LAST\tP17\tQ17' in lines
    assert 'LAST\tSjawiki\t"縣神社 (四日市市)"' in lines


def test_section_anchor_sitelink_is_dropped():
    # Emma 2026-07-06: a section-anchor sitelink (contains '#') is invalid and must
    # never be emitted — it caused the bad host-page/section sitelinks she stripped.
    rec = {"recovered_label": "Ōtenma-chō Tennō Festival",
           "fandom": {"langlinks": {"ja": "大伝馬町天王祭"}, "host_pages": ["Gion and Tenno Festivals"],
                      "ja_sitelink": "祇園祭#日本全国の祇園祭"},
           "enrichment": {"description_en": "festival in Japan", "p31": "Q132241",
                          "p31_property": "P31", "p17": "Q17"}}
    lines = b.block(rec, "Q135504314")
    assert 'LAST\tP31\tQ132241' in lines
    assert not any("Sjawiki" in ln for ln in lines)


def test_block_subclass_uses_p279():
    rec = _rec(p31="Q1041984", p31_property="P279")
    lines = b.block(rec, "Q1")
    assert 'LAST\tP279\tQ1041984' in lines
    assert not any(ln.startswith("LAST\tP31") for ln in lines)


def test_block_romaji_ja_not_emitted_as_label():
    rec = {"recovered_label": "Amanomikemunushi no Kami",
           "fandom": {"langlinks": {"ja": "Amanomikemunushi no Kami"}, "host_pages": ["X"]},
           "enrichment": {"description_en": "kami (Shinto deity)", "p31": "Q524158",
                          "p31_property": "P31"}}
    lines = b.block(rec, "Q1")
    assert 'LAST\tLen\t"Amanomikemunushi no Kami"' in lines
    assert not any(ln.startswith("LAST\tLja") for ln in lines)   # romaji ja rejected
