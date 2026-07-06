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


def test_uncertain_left_null():
    # Geographic / unknown → no guess.
    assert _p31("Shimabara Sea", "島原海") is None
    assert _p31("", "") is None


def test_description_matches_type():
    _, lab, desc, conf, src = ep.classify("Gion Festival", "祇園祭")
    assert lab == "festival" and "festival" in desc and conf == "high"
