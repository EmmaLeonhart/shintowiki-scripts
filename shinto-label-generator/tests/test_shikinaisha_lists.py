"""Shikinaisha-list label generator: the parsing/classification/rendering logic
that had the real bug (four provinces whose English label doesn't end in
' Province' — Awa (Chiba), Awa (Tokushima), Iki Island, Tsushima — were being
mis-classified as the Imperial Palace). Kind is driven by the Japanese label;
the romaji province name is parsed from the irregular English label. All offline
— no network."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_shikinaisha_list_quickstatements import (  # noqa: E402
    _classify, _parse_en_province, _render_prov, build_alpha, build_ko,
    build_zh_map, PARENT_QID,
)
from generate_multilang_quickstatements import cyrillicize  # noqa: E402


# ── classification is Japanese-label driven ────────────────────

def test_parent_is_parent():
    it = _classify(PARENT_QID, "延喜式神名帳", "Engishiki Jinmyōchō", {"ja", "en"})
    assert it["kind"] == "parent"


def test_plain_province():
    it = _classify("Q1", "山城国の式内社一覧", "List of Shikinaisha in Yamashiro Province", set())
    assert it["kind"] == "province"
    assert it["prov_core"] == "Yamashiro"
    assert it["prov_disambig"] is None
    assert it["ja_core"] == "山城国"


def test_palace_only_from_japanese_core():
    it = _classify("Q2", "宮中・京中の式内社一覧", "List of Shikinaisha in the Imperial Palace", set())
    assert it["kind"] == "palace"


def test_disambiguated_provinces_are_not_palace():
    # The exact four items that used to be mis-read as the Imperial Palace.
    chiba = _classify("Q3", "安房国の式内社一覧", "List of Shikinaisha in Awa Province (Chiba)", set())
    toku = _classify("Q4", "阿波国の式内社一覧", "List of Shikinaisha in Awa Province (Tokushima)", set())
    iki = _classify("Q5", "壱岐国の式内社一覧", "List of Shikinaisha in Iki Island", set())
    tsu = _classify("Q6", "対馬国の式内社一覧", "List of Shikinaisha in Tsushima", set())
    for it in (chiba, toku, iki, tsu):
        assert it["kind"] == "province"
    assert (chiba["prov_core"], chiba["prov_disambig"]) == ("Awa", "Chiba")
    assert (toku["prov_core"], toku["prov_disambig"]) == ("Awa", "Tokushima")
    assert (iki["prov_core"], iki["prov_disambig"]) == ("Iki", None)
    assert (tsu["prov_core"], tsu["prov_disambig"]) == ("Tsushima", None)
    # distinct kanji cores keep the two Awa apart for CJK
    assert chiba["ja_core"] != toku["ja_core"]


# ── English province parsing ───────────────────────────────────

def test_parse_en_variants():
    assert _parse_en_province("List of Shikinaisha in Yamashiro Province") == ("Yamashiro", None)
    assert _parse_en_province("List of Shikinaisha in Awa Province (Chiba)") == ("Awa", "Chiba")
    assert _parse_en_province("List of Shikinaisha in Iki Island") == ("Iki", None)
    assert _parse_en_province("List of Shikinaisha in Tsushima") == ("Tsushima", None)


# ── province rendering keeps the disambiguator ─────────────────

def test_render_prov_latin_keeps_romaji_and_disambig():
    assert _render_prov(None, "Yamashiro", None) == "Yamashiro"
    assert _render_prov(None, "Awa", "Chiba") == "Awa (Chiba)"


def test_render_prov_translit_handles_parens_separately():
    # transliterated core and disambiguator, parens preserved
    assert _render_prov(lambda n: cyrillicize(n, "ru"), "Awa", "Chiba") == "Ава (Тиба)"


# ── whole-label building ───────────────────────────────────────

def test_build_alpha_frames():
    yamashiro = _classify("Q1", "山城国の式内社一覧", "List of Shikinaisha in Yamashiro Province", set())
    palace = _classify("Q2", "宮中・京中の式内社一覧", "List of Shikinaisha in the Imperial Palace", set())
    parent = _classify(PARENT_QID, "延喜式神名帳", "Engishiki Jinmyōchō", set())
    assert build_alpha("de", yamashiro) == "Liste der Shikinaisha in der Provinz Yamashiro"
    assert build_alpha("de", palace) == "Liste der Shikinaisha im Kaiserpalast"
    assert build_alpha("de", parent) == "Engishiki Jinmyōchō"
    assert build_alpha("fr", yamashiro) == "liste des Shikinaisha dans la province de Yamashiro"


def test_build_zh_from_kanji_core():
    yamashiro = _classify("Q1", "山城国の式内社一覧", "List of Shikinaisha in Yamashiro Province", set())
    palace = _classify("Q2", "宮中・京中の式内社一覧", "List of Shikinaisha in the Imperial Palace", set())
    zh = build_zh_map(yamashiro)
    assert zh["zh"] == "山城国式内社列表"
    assert zh["zh-hant"] == "山城國式內社列表"      # traditional 國/內
    # the ・ separator becomes 及 in the palace core
    assert build_zh_map(palace)["zh"] == "宫中及京中式内社列表"


def test_build_zh_skips_parent():
    parent = _classify(PARENT_QID, "延喜式神名帳", "Engishiki Jinmyōchō", set())
    assert build_zh_map(parent) == {}


def test_build_ko_disambig_at_end():
    chiba = _classify("Q3", "安房国の式内社一覧", "List of Shikinaisha in Awa Province (Chiba)", set())
    toku = _classify("Q4", "阿波国の式内社一覧", "List of Shikinaisha in Awa Province (Tokushima)", set())
    a, b = build_ko(chiba), build_ko(toku)
    assert a.startswith("아와국의 식내사 목록")
    assert a != b            # disambiguated, no collision
    assert build_ko(_classify("Q2", "宮中・京中の式内社一覧", "x", set())) == "궁중의 식내사 목록"
