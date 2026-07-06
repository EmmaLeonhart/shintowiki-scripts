"""Tests for enrich_p31.classify — name-based Shinto P31 assignment."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import enrich_p31 as ep


def _p31(en, ja):
    return ep.classify(en, ja)[0]


def test_kami_by_mikoto_and_kami_suffix():
    assert _p31("Niwa-tsume no Mikoto", "庭津女命") == "Q524158"
    assert _p31("Amanomikemunushi no Kami", "天御食持神") == "Q524158"


def test_shrine_wins_over_bare_kami_char():
    # 神社 ends in 社 → shrine, not kami (the 神 is not the final char).
    assert _p31("Ōmiya Isuzu Shrine", "大宮五十鈴神社") == "Q845945"


def test_bath_additive_products():
    # Emma 2026-07-06 research: 入浴剤 brands → Q11388990 bath additive.
    assert _p31("Bath Roman", "バスロマン") == "Q11388990"
    assert _p31("Young Venus", "ヤングビーナス") == "Q11388990"
    # A confirmed person still resolves to human, not a product.
    assert _p31("Adachi Kagemura", "安達景村") == "Q5"


def test_izumo_branch_church_is_shrine_church():
    # Emma 2026-07-06: Izumo-taisha branch churches (教会) → Q135437254 Shrine Church.
    assert _p31("Izumo-taisha Karatsu Church", "出雲大社唐津教会") == "Q135437254"
    assert ep.classify("Izumo-taisha Misanjin Church", "出雲大社三神教会")[1] == "shrine church"
    # ...but a plain 神社 shrine must still be a Shinto shrine, not a church.
    assert _p31("Ōmiya Isuzu Shrine", "大宮五十鈴神社") == "Q845945"


def test_festival():
    assert _p31("Fuyumatsuri", "鞴祭") == "Q132241"
    assert _p31("Gion Festival", "祇園祭") == "Q132241"


def test_human_clan_patronymic_and_kabane():
    assert _p31("Abe no Masafumi", "安倍政文") == "Q5"
    assert _p31("Nakatomi no Ōshima", "藤原大嶋") == "Q5"
    assert _p31("Some Muraji", "某連") == "Q5"


def test_dance_and_text():
    assert _p31("Wago Nembutsu Odori", "和合の念仏踊") == "Q11639"
    assert _p31("Chikugo no Kuni Fudoki", "筑後国風土記") == "Q571"


def test_paren_disambiguator_stripped_reveals_shrine():
    assert _p31("Akagi Shrine (Niisato Itabashi Town)", "赤城神社 (桐生市新里町板橋)") == "Q845945"
    assert _p31("Agata Shrine (Yokkaichi)", "縣神社 (四日市市)") == "Q845945"


def test_buddhist_temple():
    assert _p31("Kisshō-ji (Gifu)", "吉祥寺 (岐阜市)") == "Q5393308"
    assert _p31("Konomine-dera", "國軸山金峯山寺") == "Q5393308"


def test_kofun():
    assert _p31("Moriyama Hyōtan-yama Kofun", "守山瓢箪山古墳") == "Q1141225"


def test_izumo_priest_clan():
    assert _p31("Sengetakamochi", "千家尊有") == "Q5"


def test_uncertain_left_null():
    # Geographic / unknown → no guess.
    assert _p31("Shimabara Sea", "島原海") is None
    assert _p31("", "") is None


def test_description_matches_type():
    _, lab, desc, conf, src = ep.classify("Gion Festival", "祇園祭")
    assert lab == "festival" and "festival" in desc and conf == "high"
