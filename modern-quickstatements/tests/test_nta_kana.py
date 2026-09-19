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


def idx(entries, pref="山梨県"):
    """({(city, folded name): [(kana, houjin, pref)]}, ambiguous) exactly as load_index.

    The fold MUST be here too: load_index keys on gen.fold_name(name) and build() looks
    up gen.fold_name(ja), so a helper that skipped it would make every folding test fail
    for a reason that has nothing to do with the generator.
    """
    import collections
    by = collections.defaultdict(list)
    prefs = collections.defaultdict(set)
    for entry in entries:
        city, name, kana, houjin = entry[:4]
        p = entry[4] if len(entry) > 4 else pref
        for ck in gen.city_keys(city):
            by[(ck, gen.fold_name(name))].append((kana, houjin, p))
            prefs[ck].add(p)
    return by, {c for c, ps in prefs.items() if len(ps) > 1}


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


def test_old_form_kanji_folds_to_the_modern_form():
    """The registry records the LEGALLY REGISTERED name, usually pre-1949 old forms."""
    assert gen.fold_name("淨嚴寺") == "浄厳寺"
    assert gen.fold_name("圓行寺") == "円行寺"
    assert gen.fold_name("寳藏院") == "宝蔵院"
    assert gen.fold_name("三ッ宮神社") == "三ツ宮神社"


def test_folding_matches_across_the_two_spellings():
    index, ambiguous = idx([("上越市", "淨嚴寺", "ジョウゴンジ", "1234567890123")])
    lines, _ = gen.build([("Q9", "浄厳寺", "上越市")], index, ambiguous)
    assert len(lines) == 1 and lines[0].startswith('Q9|P1814|"じょうごんじ"')


def test_folding_turns_a_spelling_pair_into_a_refusal_not_a_coin_flip():
    """龍源寺 and 竜源寺 in one municipality are two corporations with one folded name."""
    index, ambiguous = idx([("鈴鹿市", "龍源寺", "リュウゲンジ", "1"),
                 ("鈴鹿市", "竜源寺", "タツミナモトジ", "2")])
    lines, stats = gen.build([("Q10", "龍源寺", "鈴鹿市")], index, ambiguous)
    assert lines == []
    assert stats["same name twice in one municipality"] == 1


def test_the_folded_name_is_never_what_gets_emitted():
    """Folding is a comparison form. The emitted line carries the QID and the reading,
    never a rewritten name -- nothing downstream should see 竜 where Wikidata says 龍."""
    index, ambiguous = idx([("甲府市", "龍雲寺", "リュウウンジ", "1234567890123")])
    lines, _ = gen.build([("Q11", "龍雲寺", "甲府市")], index, ambiguous)
    assert lines == ['Q11|P1814|"りゅううんじ"|S854|"%s"'
                     % (gen.REGISTRY % "1234567890123")]
    assert "竜" not in lines[0]


def test_a_match_in_a_different_municipality_is_not_used():
    """遠妙寺 exists in 中央市 and 笛吹市; 長谷寺 in 徳島市 reads チョウコクジ."""
    index, ambiguous = idx([("山梨県中央市", "遠妙寺", "オンミョウジ", "1")])
    lines, stats = gen.build([("Q1", "遠妙寺", "笛吹市")], index, ambiguous)
    assert lines == []
    assert stats["no match in the registry"] == 1


def test_a_reading_with_no_corporate_number_is_refused():
    index, ambiguous = idx([("甲府市", "専徳寺", "セントクジ", "")])
    lines, stats = gen.build([("Q2", "専徳寺", "甲府市")], index, ambiguous)
    assert lines == []
    assert stats["no corporate number — would be uncited"] == 1


def test_two_corporations_of_the_same_name_in_one_municipality_are_refused():
    index, ambiguous = idx([("甲府市", "八幡神社", "ハチマンジンジャ", "1"),
                 ("甲府市", "八幡神社", "ヤワタジンジャ", "2")])
    lines, stats = gen.build([("Q3", "八幡神社", "甲府市")], index, ambiguous)
    assert lines == []
    assert stats["same name twice in one municipality"] == 1


def test_an_emitted_line_is_hiragana_and_carries_its_reference():
    index, ambiguous = idx([("甲府市", "船形神社", "フナカタジンジャ", "1234567890123")])
    lines, _ = gen.build([("Q4", "船形神社", "甲府市")], index, ambiguous)
    assert len(lines) == 1
    line = lines[0]
    assert line.startswith('Q4|P1814|"ふなかたじんじゃ"|S854|"')
    assert "selHouzinNo=1234567890123" in line
    assert not KATAKANA.search(line.split("|S854|")[0])
    parsed = dde.parse_qs_line(line)
    assert parsed["property"] == "P1814"
    assert parsed["value"] == {"type": "string", "value": "ふなかたじんじゃ"}
    assert [p for p, _ in parsed["references"]] == ["P854"]


def test_an_ambiguous_municipality_with_no_prefecture_is_refused():
    """北区 exists in several prefectures. Without a prefecture there is nothing to tell
    a Tokyo 北区 temple from an Osaka one, and 106 of 1,433 first-pass emissions sat on
    exactly such a name."""
    index, ambiguous = idx([("北区", "大護寺", "ダイゴジ", "1", "東京都"),
                            ("北区", "妙覚寺", "ミョウカクジ", "2", "大阪府")])
    assert "北区" in ambiguous
    lines, stats = gen.build([("Q20", "大護寺", "北区")], index, ambiguous)
    assert lines == []
    assert stats["municipality name not unique, no prefecture to settle it"] == 1


def test_an_ambiguous_municipality_is_settled_by_the_prefecture():
    index, ambiguous = idx([("北区", "大護寺", "ダイゴジ", "1234567890123", "東京都"),
                            ("北区", "妙覚寺", "ミョウカクジ", "2", "大阪府")])
    lines, _ = gen.build([("Q21", "大護寺", "北区", "東京都")], index, ambiguous)
    assert len(lines) == 1 and lines[0].startswith('Q21|P1814|"だいごじ"')


def test_a_prefecture_that_disagrees_refuses_the_match():
    index, ambiguous = idx([("北区", "大護寺", "ダイゴジ", "1", "東京都"),
                            ("北区", "妙覚寺", "ミョウカクジ", "2", "大阪府")])
    lines, stats = gen.build([("Q22", "大護寺", "北区", "大阪府")], index, ambiguous)
    assert lines == []
    assert stats["municipality name not unique, prefecture disagrees"] == 1


def test_a_unique_municipality_needs_no_prefecture():
    index, ambiguous = idx([("甲府市", "船形神社", "フナカタジンジャ", "1234567890123")])
    assert ambiguous == set()
    lines, _ = gen.build([("Q23", "船形神社", "甲府市")], index, ambiguous)
    assert len(lines) == 1


def test_an_unplaced_item_takes_a_nationally_unique_name():
    """No P131 means no municipality to match on and no claim to contradict, so a name
    the registry holds exactly once is an unambiguous identification."""
    by_name = {gen.fold_name("福谷寺"): [("ウキガイジ", "1234567890123")]}
    lines, stats = gen.build_unplaced([("Q30", "福谷寺")], by_name)
    assert lines == ['Q30|P1814|"うきがいじ"|S854|"%s"' % (gen.REGISTRY % "1234567890123")]
    assert stats["unplaced: emitted"] == 1


def test_an_unplaced_item_with_a_repeated_name_is_refused():
    by_name = {gen.fold_name("少林寺"): [("ショウリンジ", "1"), ("ショウリンジ", "2")]}
    lines, stats = gen.build_unplaced([("Q31", "少林寺")], by_name)
    assert lines == []
    assert stats["unplaced: name is not nationally unique"] == 1


def test_an_unplaced_item_absent_from_the_registry_is_refused():
    lines, stats = gen.build_unplaced([("Q32", "汕頭神社")], {})
    assert lines == []
    assert stats["unplaced: name absent from the registry"] == 1


def test_an_unplaced_item_still_needs_its_corporate_number():
    by_name = {gen.fold_name("有金寺"): [("ユウキンジ", "")]}
    lines, stats = gen.build_unplaced([("Q33", "有金寺")], by_name)
    assert lines == []
    assert stats["unplaced: no corporate number — would be uncited"] == 1


def test_the_unique_name_rule_is_not_applied_to_a_placed_item():
    """A nationally unique name in a DIFFERENT municipality is a conflict with an
    explicit P131, not evidence. build() must refuse it however unique the name is."""
    index, ambiguous = idx([("豊田市", "平勝寺", "ヘイショウジ", "1234567890123")])
    lines, stats = gen.build([("Q34", "平勝寺", "岡崎市")], index, ambiguous)
    assert lines == []
    assert stats["no match in the registry"] == 1


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
