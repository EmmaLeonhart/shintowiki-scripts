"""The NTA kana generator must never emit an uncited, katakana, or guessed reading.

Three properties, each of which was a live hazard rather than a hypothetical:

  * **Cited.** Emma's 2026-08-24 ruling (docs/kana_name_mate_rulings.md) is that a
    reading cited to houjin-bangou.nta.go.jp is PRESERVED even when it looks like a
    typo, and an uncited one is CORRECTED. So a reading emitted without its reference
    would be undone by the next pass — the near miss generate_lost_shrine_creates.py
    records on 近殿神社's ちかどのじんしゃ.
  * **Hiragana.** collect_name_in_kana.py rejects katakana outright, because katakana in
    a top-level P1814 is the signature of the ancient-Engishiki-reading error the
    kana-qualifier cleanup exists to undo. The registry files katakana, so conversion is
    not optional.
  * **Not guessed.** The registry often files the stem alone — 淺間神社 → センゲン. 神社
    has one reading and is completed; 寺 is じ or でら and 宮 is ぐう or みや, so those are
    skipped. This is the same line drawn against web-search readings, applied to our own
    output.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QS_DIR = os.path.dirname(HERE)
if QS_DIR not in sys.path:
    sys.path.insert(0, QS_DIR)

import direct_daily_edits as dde  # noqa: E402
import generate_nta_kana as gen  # noqa: E402

KATAKANA = re.compile(r"[ァ-ヶ]")


def idx(entries):
    """{(city, name): [(kana, houjin)]} built the way load_index would."""
    import collections
    by = collections.defaultdict(list)
    for city, name, kana, houjin in entries:
        for ck in gen.city_keys(city):
            by[(ck, name)].append((kana, houjin))
    return by


def test_katakana_becomes_hiragana():
    assert gen.to_hiragana("セントクジ") == "せんとくじ"
    assert gen.to_hiragana("ジョウゴンジ") == "じょうごんじ"


def test_the_long_vowel_mark_survives_conversion():
    """ー is not in the katakana block and must not be shifted into a stray codepoint."""
    assert gen.to_hiragana("コーヤ") == "こーや"


def test_municipality_spellings_are_normalised():
    """NTA writes 郡+町 and 市+区; Wikidata labels the bare unit. 87 of 350 first-pass
    misses were this alone."""
    assert "吉備中央町" in gen.city_keys("加賀郡吉備中央町")
    assert "右京区" in gen.city_keys("京都市右京区")
    assert gen.city_keys("甲府市") == {"甲府市"}


def test_a_stem_only_shrine_reading_is_completed():
    assert gen.complete("淺間神社", "センゲン")[0] == "センゲンジンジャ"
    assert gen.complete("三ッ宮神社", "ミツミヤ")[0] == "ミツミヤジンジャ"


def test_a_complete_shrine_reading_is_left_alone():
    assert gen.complete("船形神社", "フナカタジンジャ")[0] == "フナカタジンジャ"


def test_an_ambiguous_tail_is_skipped_not_guessed():
    """寺 is じ or でら; picking one is inventing a reading."""
    full, why = gen.complete("長谷寺", "ハセ")
    assert full is None and "ambiguous" in why
    full, why = gen.complete("若宮", "ワカ")
    assert full is None


def test_a_temple_reading_that_carries_its_own_tail_is_kept():
    assert gen.complete("多田寺", "タダジ")[0] == "タダジ"
    assert gen.complete("清水寺", "キヨミズデラ")[0] == "キヨミズデラ"


def test_a_match_in_a_different_municipality_is_not_used():
    """遠妙寺 exists in 中央市 and 笛吹市; 長谷寺 in 徳島市 reads チョウコクジ."""
    index = idx([("山梨県中央市", "遠妙寺", "オンミョウジ", "1")])
    lines, stats = gen.build([("Q1", "遠妙寺", "笛吹市")], index)
    assert lines == []
    assert stats["no match in the registry"] == 1


def test_a_reading_with_no_corporate_number_is_refused():
    index = idx([("甲府市", "専徳寺", "セントクジ", "")])
    lines, stats = gen.build([("Q2", "専徳寺", "甲府市")], index)
    assert lines == []
    assert stats["no corporate number — would be uncited"] == 1


def test_two_corporations_of_the_same_name_in_one_municipality_are_refused():
    index = idx([("甲府市", "八幡神社", "ハチマンジンジャ", "1"),
                 ("甲府市", "八幡神社", "ヤワタジンジャ", "2")])
    lines, stats = gen.build([("Q3", "八幡神社", "甲府市")], index)
    assert lines == []
    assert stats["same name twice in one municipality"] == 1


def test_an_emitted_line_is_hiragana_and_carries_its_reference():
    index = idx([("甲府市", "船形神社", "フナカタジンジャ", "1234567890123")])
    lines, _ = gen.build([("Q4", "船形神社", "甲府市")], index)
    assert len(lines) == 1
    line = lines[0]
    assert line.startswith('Q4|P1814|"ふなかたじんじゃ"|S854|"')
    assert "selHouzinNo=1234567890123" in line
    assert not KATAKANA.search(line.split("|S854|")[0])
    parsed = dde.parse_qs_line(line)
    assert parsed["property"] == "P1814"
    assert parsed["value"] == {"type": "string", "value": "ふなかたじんじゃ"}
    assert [p for p, _ in parsed["references"]] == ["P854"]


def test_the_shipped_file_holds_no_katakana_and_every_line_is_referenced():
    path = os.path.join(QS_DIR, "nta_kana.txt")
    if not os.path.exists(path):
        return
    for n, raw in enumerate(io.open(path, encoding="utf-8"), 1):
        line = raw.strip()
        if not line:
            continue
        value = line.split("|S854|")[0]
        assert not KATAKANA.search(value), "%s:%d katakana in a P1814 value" % (path, n)
        assert "|S854|" in line, "%s:%d unreferenced reading" % (path, n)
        assert dde.parse_qs_line(line) is not None, "%s:%d does not parse" % (path, n)


def test_the_file_is_registered_in_the_drip():
    assert "nta_kana.txt" in dde.ATOMIC_FILES
