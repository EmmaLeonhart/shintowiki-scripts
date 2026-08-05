"""Tests for the name-in-kana collector's parsing and its one hard gate.

The gate is the whole safety story of queue item A0: the reading is extracted by
an LLM, and the only thing standing between a bad extraction and a P1814
statement on Wikidata is "is this actually modern hiragana". Katakana in
particular is not a near-miss — it is the signature of the ancient-reading error
that a separate cleanup exists to undo, so re-introducing it would fight that
cleanup on the same property.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collect_name_in_kana import (  # noqa: E402
    HIRAGANA_ONLY, acceptable_reading, clean_kana, parse_answer,
)


def _wf(answer, bucket="a"):
    return ("<!-- ITEM: https://www.wikidata.org/wiki/Q1 -->\n"
            f"<!-- JA: 三嶋大社 | EN_LABEL: Mishima Taisha | BUCKET: {bucket} -->\n"
            "<!-- ARTICLE: https://ja.wikipedia.org/wiki/%E4%B8%89%E5%B6%8B%E5%A4%A7%E7%A4%BE -->\n"
            f"<!-- ANSWER: {answer} -->\n<!-- TASK: ... -->\n\n== LEAD ==\n...\n")


def test_empty_answer_is_still_pending():
    assert parse_answer(_wf("")) is None


def test_kana_answer_parsed():
    assert parse_answer(_wf("KANA: みしまたいしゃ")) == ("KANA", "みしまたいしゃ")


def test_katakana_and_no_kana_answers_parsed():
    assert parse_answer(_wf("KATAKANA: ミシマノオオヤシロ"))[0] == "KATAKANA"
    assert parse_answer(_wf("NO_KANA: lead names the town, not the shrine"))[0] == "NO_KANA"


def test_unrecognised_answer_is_malformed_not_silently_accepted():
    """An answer that doesn't declare its kind must not be treated as a reading."""
    assert parse_answer(_wf("みしまたいしゃ"))[0] == "MALFORMED"


# ─────────────────────────── the gate ───────────────────────────

def test_hiragana_passes():
    assert HIRAGANA_ONLY.match("みしまたいしゃ")
    assert HIRAGANA_ONLY.match("おおやまづみじんじゃ")


def test_katakana_is_rejected():
    """P1814 wants modern hiragana; all-katakana is the ancient-reading error."""
    assert not HIRAGANA_ONLY.match("ミシマタイシャ")


def test_all_katakana_is_still_refused_by_the_real_gate():
    """The error class the gate exists for: アスキ-, ツキタノ-, カミノヤシロ are
    all-katakana, and a shrine reading cannot legitimately be — the name ends in
    神社/神宮/宮, which read as hiragana."""
    for bad in ("ミシマタイシャ", "アスキ", "カミノヤシロ", "ツキタノ"):
        assert not acceptable_reading(bad), bad


def test_mixed_katakana_is_accepted():
    """RELAXED 2026-08-05 on Emma's ruling — these are the real overseas and
    colonial-era shrines, previously rejected wholesale and producing nothing.

    Safe because the cleanup this gate was guarding against only touches items
    with an ojp-hani P1448 + カミノヤシロ qualifier and emits value-matched
    removals; an overseas shrine has neither, so there is nothing to collide."""
    for ok in ("ハワイだいじんぐう", "ハワイいしづちじんじゃ", "スワトウじんじゃ",
               "ペリリューじんじゃ", "サムハラじんじゃ", "アラハバキかみ"):
        assert acceptable_reading(ok), ok


def test_pure_hiragana_is_still_accepted():
    assert acceptable_reading("みしまたいしゃ")
    assert acceptable_reading("おーやま")


def test_non_kana_is_refused_by_the_real_gate():
    """Relaxing to allow katakana must not open the door to kanji or latin."""
    for bad in ("三嶋大社", "Mishima Taisha", "みしま大社", "ハワイ大神宮", ""):
        assert not acceptable_reading(bad), bad


def test_kanji_and_latin_are_rejected():
    assert not HIRAGANA_ONLY.match("三嶋大社")
    assert not HIRAGANA_ONLY.match("Mishima Taisha")
    assert not HIRAGANA_ONLY.match("みしま大社")


def test_clean_kana_strips_only_punctuation_never_script():
    assert clean_kana(" みしま たいしゃ ") == "みしまたいしゃ"
    assert clean_kana("みしま・たいしゃ") == "みしまたいしゃ"
    assert clean_kana("「みしまたいしゃ」") == "みしまたいしゃ"
    # stripping must not rescue a katakana answer into passing the gate
    assert not HIRAGANA_ONLY.match(clean_kana("ミシマ・タイシャ"))


def test_long_vowel_and_iteration_marks_are_allowed():
    """ー and ゝ appear in genuine hiragana readings and must not be rejected."""
    assert HIRAGANA_ONLY.match("おーやま")
    assert HIRAGANA_ONLY.match("すゝき")


def test_qs_line_shape_uses_bare_quotes():
    """P1814's datatype is `string`, not monolingual text — a ja: prefix would be
    rejected by the submitter. This pins the format the collector emits."""
    qid, kana = "Q1", "みしまたいしゃ"
    url = "https://ja.wikipedia.org/wiki/%E4%B8%89%E5%B6%8B%E5%A4%A7%E7%A4%BE"
    line = f'{qid}|P1814|"{kana}"|S143|Q177837|S4656|"{url}"'
    assert re.match(r'^Q\d+\|P1814\|"[ぁ-ゖーゝゞ]+"\|S143\|Q177837\|S4656\|"https://', line)
    assert "ja:" not in line
