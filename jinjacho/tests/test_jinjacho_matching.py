"""Pure-logic guards for the jinjacho crawl -> P973 pipeline.

No network: these pin the two things that decide whether a P973 statement lands on
the RIGHT shrine — how a municipality is read out of a crawled address, and the
per-family HTML parsers. Both were wrong in their first version and both produced
plausible-looking wrong matches rather than errors, which is the failure mode worth
a test.
"""
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
JINJACHO = os.path.dirname(HERE)


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(JINJACHO, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


crawl = _load("crawl_jinjacho_shrines")


@pytest.fixture(scope="module")
def match():
    """Imports generate_genbu_ids, which needs `requests` but makes no call at import."""
    return _load("match_jinjacho_shrines")


# ─────────────────────── municipality parsing ───────────────────────

@pytest.mark.parametrize("address,expected", [
    ("岐阜県大垣市墨俣町墨俣264番地", "大垣市"),
    ("滋賀県大津市伊香立途中町518", "大津市"),
    ("さいたま市大宮区高鼻町3-149", "さいたま市"),
    ("東秩父村坂本1541", "東秩父村"),
    ("〒501-6112 岐阜県岐阜市柳津町北塚2丁目26の1", "岐阜市"),
    # A 郡 is a DISTRICT, not the municipality P131 points at: the 町 inside it is.
    ("岐阜県安八郡安八町西結697番地の2", "安八町"),
    ("滋賀県犬上郡多賀町大字多賀604", "多賀町"),
    ("", ""),
])
def test_municipality(match, address, expected):
    assert match.municipality(address) == expected


# ─────────────────────── the two precision guards ───────────────────────

def test_municipality_gate_rejects_a_same_name_shrine_in_another_city(match):
    """The original bug: gating on PREFECTURE matched a 天満神社 crawled in 大垣市 to
    天満神社 (高山市), because it was the only item of that name in Gifu."""
    assert match.municipality("岐阜県高山市...") != match.municipality("岐阜県大垣市墨俣町墨俣264番地")


def test_collision_guard_drops_an_item_claimed_twice():
    """Two distinct 八幡神社 in 大垣市墨俣町, one Wikidata item: both crawled rows
    resolved to Q11391073 and at most one can be right, so neither is emitted.
    This mirrors the grouping step in match_jinjacho_shrines.main()."""
    import collections
    out = [
        {"shrine": ".../Q11391073", "website": "a"},
        {"shrine": ".../Q11391073", "website": "b"},
        {"shrine": ".../Q11429413", "website": "c"},
    ]
    counts = collections.Counter(r["shrine"] for r in out)
    collided = {q for q, n in counts.items() if n > 1}
    kept = [r for r in out if r["shrine"] not in collided]
    assert [r["website"] for r in kept] == ["c"]


# ─────────────────────── per-family HTML parsers ───────────────────────

def test_gifu_parser():
    html = ("<html><body>天神神社詳細<br>天神神社 (てんじんじんじゃ)<br>"
            "主祭神 菅原道真<br>住所&nbsp;〒501-6112&nbsp;岐阜県岐阜市柳津町北塚2丁目26の1"
            "</body></html>")
    rec = crawl.parse_gifu(html)
    assert rec["shrine_name"] == "天神神社"
    assert rec["kana"] == "てんじんじんじゃ"
    assert "岐阜市" in rec["address"]


def test_saitama_parser_reads_the_title_and_rejects_the_placeholder():
    ok = "<html><head><title>加茂神社 ｜ 埼玉県の神社</title></head><body>" \
         "所在地 さいたま市北区宮原町4-8-1</body></html>"
    rec = crawl.parse_saitama(ok)
    assert rec["shrine_name"] == "加茂神社"
    assert "さいたま市" in rec["address"]
    # A listing/404 page must not become a shrine record.
    assert crawl.parse_saitama("<title>埼玉県の神社</title>") is None


def test_jinjanet_parser():
    html = ("神社名/通称 博西神社 （ふりがな） はかにしじんじゃ "
            "郵便番号 639-2135 鎮座地 奈良県葛城市寺口1170")
    rec = crawl.parse_jinjanet(html)
    assert rec["shrine_name"] == "博西神社"
    assert rec["kana"] == "はかにしじんじゃ"


def test_dead_pages_parse_to_none():
    assert crawl.parse_gifu("<html><body>お探しの神社は見つかりませんでした</body></html>") is None
    assert crawl.parse_jinjanet("<html><body>検索結果 詳細情報</body></html>") is None


# ─────────────────────── crawl politeness ───────────────────────

def test_throttle_and_miss_tolerance_are_present():
    """These are the two things that keep a wrong id range from becoming a thousand
    requests against a volunteer-run prefectural site."""
    assert crawl.THROTTLE >= 1.0
    assert 0 < crawl.MISS_TOLERANCE <= 200


def test_every_family_is_integer_enumerable():
    """UUID- and slug-keyed sites cannot be swept by id and must not be added to
    FAMILIES; they belong in INDEX_FAMILIES (Aichi now is)."""
    for key, fam in crawl.FAMILIES.items():
        assert "{n}" in fam["url"], key
        assert fam["start"] < fam["stop"], key
        assert callable(fam["parser"]), key


# ─────────────────────── index-harvest families ───────────────────────

def test_index_and_sweep_families_are_disjoint():
    """A site in both would be fetched twice and duplicate its rows."""
    assert not (set(crawl.FAMILIES) & set(crawl.INDEX_FAMILIES))


def test_aichi_detail_url_matches_the_shipped_sample_format():
    """The URL is the P973 VALUE, so its shape is the whole point: if it does not
    match what shrines_and_websites.csv already uses, the harvest would emit a second,
    differently-formatted URL for shrines that already have one."""
    import csv as _csv
    sample = os.path.join(JINJACHO, "shrines_and_websites.csv")
    aichi = [r["website"] for r in _csv.DictReader(open(sample, encoding="utf-8"))
             if "aichi-jinjacho" in r["website"]]
    assert aichi, "sample CSV should contain Aichi rows"
    built = crawl.AICHI_DETAIL % "bb10f2cc-3e65-4e3f-aad0-e4259400d028"
    assert built == ("https://www.aichi-jinjacho.or.jp/search_detail.html"
                     "?id=bb10f2cc-3e65-4e3f-aad0-e4259400d028")
    # every shipped Aichi URL uses the same path + id= parameter
    for u in aichi:
        assert "search_detail.html?id=" in u, u


def test_index_families_are_callables():
    for key, fn in crawl.INDEX_FAMILIES.items():
        assert callable(fn), key
