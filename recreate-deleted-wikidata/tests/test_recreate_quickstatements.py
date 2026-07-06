"""Unit tests for the pure logic in generate_recreate_quickstatements.

The wiki/Wikidata fetchers are network; here we test the ill parser, the QS
string sanitiser, and the CREATE-block renderer against real on-wiki examples.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_recreate_quickstatements as g  # noqa: E402


def test_parse_simple_target():
    t = g.parse_deleted_ill("Abe Yasukichi|ja|安倍泰吉|qid=DELETED_QID")
    assert t["label"] == "Abe Yasukichi"
    assert t["langlinks"] == [("ja", "安倍泰吉")]
    assert t["deleted_qid"] == ""
    assert t["ja_invalid"] is False


def test_parse_target_with_dd_and_invalid_ja():
    inner = ("Agata Shrine (Yokkaichi)|ja|縣神社 (四日市市)|12=simple|"
             "13=User:Immanuelle/Agata Shrine (Yokkaichi)|"
             "ja_comment=jawiki link invalid|qid=DELETED_QID|dd=Q135500704")
    t = g.parse_deleted_ill(inner)
    assert t["label"] == "Agata Shrine (Yokkaichi)"
    assert t["langlinks"] == [("ja", "縣神社 (四日市市)")]
    assert t["deleted_qid"] == "Q135500704"   # original QID recovered from dd=
    assert t["ja_invalid"] is True            # ja_comment marks it invalid


def test_parse_qid_written_into_label_slot_is_recovered():
    # The earlier bug wrote the deleted QID into the link-title slot, destroying
    # the English name. positional[0] being a bare QID must be recovered as the
    # deleted_qid, NOT emitted as a label; other-language labels survive.
    t = g.parse_deleted_ill("Q135491453|de|One Day Spa|ja|ワンデイ・スパ|qid=DELETED_QID")
    assert t["label"] == ""
    assert t["deleted_qid"] == "Q135491453"
    assert ("de", "One Day Spa") in t["langlinks"]
    lines = g.render_create_block(t, "1-day onsen facility")
    assert "was Q135491453" in lines[0]           # recovered QID in provenance
    assert not any(ln == 'LAST\tLen\t"Q135491453"' for ln in lines)  # no bogus label


def test_parse_multiple_langlinks():
    t = g.parse_deleted_ill("Foo|ja|フー|en|Foo bar|qid=DELETED_QID")
    assert t["langlinks"] == [("ja", "フー"), ("en", "Foo bar")]


def test_qs_str_sanitises():
    assert g._qs_str('a "quoted" | name') == '"a \'quoted\' / name"'


def test_render_create_block_with_valid_sitelink():
    t = g.parse_deleted_ill("Abe Yasukichi|ja|安倍泰吉|qid=DELETED_QID")
    lines = g.render_create_block(t, "Abe no Ariyo")
    assert lines[0].startswith("# recreate deleted ill target (original QID lost)")
    assert "CREATE" in lines
    assert 'LAST\tLen\t"Abe Yasukichi"' in lines
    assert 'LAST\tLja\t"安倍泰吉"' in lines
    # valid ja link → jawiki sitelink emitted (notability anchor)
    assert 'LAST\tSjawiki\t"安倍泰吉"' in lines


def test_render_create_block_invalid_ja_no_sitelink():
    inner = ("Agata Shrine (Yokkaichi)|ja|縣神社 (四日市市)|"
             "ja_comment=jawiki link invalid|qid=DELETED_QID|dd=Q135500704")
    t = g.parse_deleted_ill(inner)
    lines = g.render_create_block(t, "Agata Shrine")
    # provenance comment carries the recovered original QID
    assert "was Q135500704" in lines[0]
    # invalid ja link → NO sitelink line
    assert not any(ln.startswith("LAST\tSjawiki") for ln in lines)
    assert 'LAST\tLja\t"縣神社 (四日市市)"' in lines


# ─── step 1: consolidated JSON (all linking articles + labels) ──────────────
def test_labels_for_consolidates_en_and_langlinks():
    t = g.parse_deleted_ill("Abe Yasukichi|ja|安倍泰吉|de|Abe Yasukichi|qid=DELETED_QID")
    labels = g.labels_for(t)
    assert labels["en"] == "Abe Yasukichi"
    assert labels["ja"] == "安倍泰吉"
    assert labels["de"] == "Abe Yasukichi"


def test_labels_for_en_lost_keeps_other_languages():
    # en name destroyed by the QID-in-title bug → no "en", other labels survive.
    t = g.parse_deleted_ill("Q135491453|de|One Day Spa|ja|ワンデイ・スパ|qid=DELETED_QID")
    labels = g.labels_for(t)
    assert "en" not in labels
    assert labels["de"] == "One Day Spa"
    assert labels["ja"] == "ワンデイ・スパ"


def test_target_record_carries_all_source_pages_and_flags():
    t = g.parse_deleted_ill("Abe Yasukichi|ja|安倍泰吉|qid=DELETED_QID|dd=Q1")
    rec = g.target_record(t, ["Page B", "Page A"], existing_qid="Q42",
                          ja_article_exists=True)
    assert rec["deleted_qid"] == "Q1"
    assert rec["source_pages"] == ["Page A", "Page B"]   # sorted, both kept
    assert rec["labels"]["en"] == "Abe Yasukichi"
    assert rec["existing_wikidata_qid"] == "Q42"         # probable duplicate → relink
    assert rec["ja_article_exists"] is True


def test_target_record_lost_qid_is_none():
    t = g.parse_deleted_ill("Abe Arimori|ja|安倍有盛|qid=DELETED_QID")
    rec = g.target_record(t, ["Abe no Ariyo"])
    assert rec["deleted_qid"] is None
    assert rec["existing_wikidata_qid"] is None
