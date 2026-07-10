"""The grader/report for commons_normalize — score the reading, not the macrons.

Compares the normalizer's candidate against the enwiki title on the CORE reading (stem +
suffix), treating the house " Temple"/" Shrine" suffix as house-appended and macron
differences as acceptable. Buckets: exact / macron-only / mismatch / rejected.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import report_commons_label_accuracy as rep  # noqa: E402


# ─────────────── core() — strip house suffix, disambiguator, fold case ───────────────

def test_core_strips_the_temple_suffix():
    assert rep.core("Kiyomizu-dera Temple") == rep.core("Kiyomizu-dera")


def test_core_strips_the_grand_shrine_suffix():
    assert rep.core("Izumo Grand Shrine") == rep.core("Izumo")


def test_core_strips_an_enwiki_parenthetical():
    assert rep.core("Hase-dera (Kamakura)") == rep.core("Hase-dera")


def test_core_folds_case_and_whitespace():
    assert rep.core("  meiji   SHRINE ") == rep.core("Meiji Shrine")


# ─────────────── bucket() ───────────────

def test_a_house_suffix_only_difference_is_exact():
    # candidate has " Temple", enwiki does not — the correct outcome, counted exact
    assert rep.bucket("Kiyomizu-dera Temple", "Kiyomizu-dera") == "exact"


def test_a_true_match_is_exact():
    assert rep.bucket("Meiji Shrine", "Meiji Shrine") == "exact"


def test_a_macron_only_difference_is_acceptable_not_a_failure():
    # candidate missed the macron (Senso), enwiki has it (Sensō) → acceptable
    assert rep.bucket("Senso-ji Temple", "Sensō-ji") == "macron-only"


def test_a_wrong_reading_is_a_mismatch():
    assert rep.bucket("Senso-ji Temple", "Asakusa") == "mismatch"


def test_a_none_candidate_is_rejected():
    assert rep.bucket(None, "Sensō-ji") == "rejected"


# ─────────────── build_report() over fixture rows ───────────────

def _rows():
    return [
        {"qid": "Q1", "commons": "Sensouji", "enwiki": "Sensō-ji", "ja": "浅草寺", "en": ""},
        {"qid": "Q2", "commons": "Sensoji", "enwiki": "Sensō-ji", "ja": "", "en": ""},
        {"qid": "Q3", "commons": "Ideha-jinja", "enwiki": "Dewa Shrine", "ja": "", "en": ""},
        {"qid": "Q4", "commons": "Matthäuskirche", "enwiki": "", "ja": "", "en": ""},
        {"qid": "Q5", "commons": "Amaterasu", "enwiki": "Amaterasu", "ja": "", "en": ""},
    ]


def test_build_report_buckets_every_gradeable_row():
    r = rep.build_report(_rows())
    # Q1 exact (Sensō-ji Temple vs Sensō-ji); Q2 macron-only (Senso-ji vs Sensō-ji);
    # Q3 mismatch (Kanda Shrine vs Kanda Myojin — genuinely different reading);
    # Q4 not gradeable (no enwiki); Q5 gradeable but rejected (Amaterasu → None).
    assert r["counts"]["gradeable"] == 4      # Q1,Q2,Q3,Q5 have an enwiki title
    assert r["buckets"]["exact"] == 1
    assert r["buckets"]["macron-only"] == 1
    assert r["buckets"]["mismatch"] == 1
    assert r["buckets"]["rejected"] == 1


def test_build_report_lists_mismatches_in_full():
    r = rep.build_report(_rows())
    m = [x for x in r["mismatches"] if x["qid"] == "Q3"][0]
    assert m["commons"] == "Ideha-jinja"
    assert m["candidate"] == "Ideha Shrine"
    assert m["enwiki"] == "Dewa Shrine"


def test_grand_shrine_vs_shrine_is_a_reading_match_not_a_mismatch():
    """Meiji Jingu → "Meiji Grand Shrine"; enwiki "Meiji Shrine". Same reading (Meiji);
    Grand-vs-plain is a suffix flavour, so this is exact, not a failure."""
    assert rep.bucket("Meiji Grand Shrine", "Meiji Shrine") == "exact"


def test_english_grand_shrine_matches_enwiki_untranslated_taisha():
    """Our house translates 大社; enwiki keeps it. Same reading → exact, not a failure."""
    assert rep.bucket("Fushimi Inari Grand Shrine", "Fushimi Inari-taisha") == "exact"
    assert rep.bucket("Izumo Grand Shrine", "Izumo-taisha") == "exact"


def test_english_shrine_matches_enwiki_untranslated_jingu():
    assert rep.bucket("Usa Shrine", "Usa Jingū") == "exact"


def test_hyphen_and_space_are_noise_in_the_reading():
    assert rep.bucket("Gifu-Gokoku Shrine", "Gifu Gokoku Shrine") == "exact"


def test_a_genuine_reading_glitch_still_mismatches():
    # Ideha vs Dewa, Iyahiko vs Yahiko — real different readings, must NOT collapse.
    assert rep.bucket("Ideha Shrine", "Dewa Shrine") == "mismatch"
    assert rep.bucket("Iyahiko Shrine", "Yahiko Shrine") == "mismatch"


def test_hachiman_is_name_material_not_a_stripped_suffix():
    """Fujisaki-hachiman-gu Shrine vs Fujisaki Hachimangū — strip only the gū, keep
    'hachiman'. Both reduce to fujisakihachiman → exact."""
    assert rep.bucket("Fujisaki-hachiman-gu Shrine", "Fujisaki Hachimangū") == "exact"
    assert rep.bucket("Yushima Tenman-gu Shrine", "Yushima Tenmangū") == "exact"


def test_a_kanji_commons_name_is_out_of_scope_not_rejected():
    rows = [{"qid": "Q1", "commons": "厳島神社", "enwiki": "Itsukushima Shrine",
             "ja": "厳島神社", "en": ""}]
    r = rep.build_report(rows)
    assert r["counts"]["non_romaji"] == 1
    assert r["counts"]["gradeable"] == 0
    assert r["buckets"]["rejected"] == 0


def test_headline_accuracy_counts_macron_only_as_a_pass():
    r = rep.build_report(_rows())
    # (exact + macron-only) / gradeable = 2/4
    assert abs(r["accuracy"] - 0.5) < 1e-9


def test_a_hardcoded_override_wins_over_the_normalizer():
    rows = [{"qid": "Q9", "commons": "Urifu", "enwiki": "Mefu Shrine",
             "ja": "売布神社", "en": ""}]
    r = rep.build_report(rows)
    # 売布神社 → forced "Mefu Shrine" by hardcoded_label, overriding the Commons romaji
    assert r["buckets"]["exact"] == 1
