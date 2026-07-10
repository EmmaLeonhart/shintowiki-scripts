"""commons_normalize — Commons category name → house-style English label.

Spec: docs/superpowers/specs/2026-07-10-commons-romaji-normalization-design.md
Mid-pipeline fallback (fires after existing-label + kana derivation). Japanese shrines +
temples only. Transcribes a *marked* long vowel (Sensouji→Sensō-ji), never guesses an
unmarked one (Sensoji→Senso-ji, the acceptable missed macron). Conservative: junk → None.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import commons_normalize as cn  # noqa: E402


# ─────────────── the two canonical cases (Emma, 2026-07-10) ───────────────

def test_marked_long_vowel_becomes_macron():
    assert cn.normalize("Sensouji") == "Sensō-ji Temple"


def test_unmarked_long_vowel_is_left_plain():
    assert cn.normalize("Sensoji") == "Senso-ji Temple"


# ─────────────── the long-vowel transcriber in isolation ───────────────

def test_transcribe_ou_to_o_macron():
    assert cn.transcribe_long_vowels("sensou") == "sensō"


def test_transcribe_uu_to_u_macron():
    assert cn.transcribe_long_vowels("juu") == "jū"


def test_transcribe_oo_to_o_macron():
    assert cn.transcribe_long_vowels("tookyoo") == "tōkyō"


def test_transcribe_leaves_a_bare_vowel_alone():
    assert cn.transcribe_long_vowels("senso") == "senso"


# ─────────────── temple suffixes → "<Stem>-<suffix> Temple" ───────────────

def test_category_prefix_is_stripped():
    assert cn.normalize("Category:Kiyomizu-dera") == "Kiyomizu-dera Temple"


def test_dera_suffix():
    assert cn.normalize("Kiyomizu-dera") == "Kiyomizu-dera Temple"


def test_in_suffix():
    assert cn.normalize("Sanzen-in") == "Sanzen-in Temple"


def test_dera_beats_ji_because_longer_endings_win_first():
    # "-dera" ends in ...a not ...ji, but the ordering guard matters for names like this
    assert cn.normalize("Hase-dera") == "Hase-dera Temple"


def test_a_macroned_temple_name_is_kept():
    assert cn.normalize("Tōfuku-ji") == "Tōfuku-ji Temple"


# ─────────────── shrine forms (kana_english house table) ───────────────

def test_jinja_becomes_shrine():
    assert cn.normalize("Yasukuni Jinja") == "Yasukuni Shrine"


def test_jingu_becomes_grand_shrine():
    assert cn.normalize("Meiji Jingu") == "Meiji Grand Shrine"


def test_jingu_with_macron_also_grand_shrine():
    assert cn.normalize("Meiji Jingū") == "Meiji Grand Shrine"


def test_taisha_becomes_grand_shrine():
    assert cn.normalize("Izumo-taisha") == "Izumo Grand Shrine"


def test_attached_gu_suffix():
    assert cn.normalize("Kotohira-gu") == "Kotohira-gu Shrine"


def test_taisha_beats_the_attached_sha_suffix():
    # "taisha" ends in "sha"; the longer shrine word must win, not "<Stem>-sha Shrine"
    assert cn.normalize("Fushimi Inari-taisha") == "Fushimi Inari Grand Shrine"


# ─────────────── already-suffixed input is kept ───────────────

def test_already_english_shrine_is_kept():
    assert cn.normalize("Meiji Shrine") == "Meiji Shrine"


def test_already_english_temple_is_kept():
    assert cn.normalize("Kōfuku-ji Temple") == "Kōfuku-ji Temple"


# ─────────────── disambiguators ───────────────

def test_comma_disambiguator_is_stripped():
    assert cn.normalize("Suwa-jinja, Nagasaki") == "Suwa Shrine"
    assert cn.normalize("Category:Kushida-jinja, Fukuoka") == "Kushida Shrine"


def test_lowercase_shrine_is_normalized_to_title_case():
    assert cn.normalize("Yoshida shrine") == "Yoshida Shrine"
    assert cn.normalize("Category:Uesugi shrine") == "Uesugi Shrine"


def test_hyphenated_shrine_word_is_handled():
    assert cn.normalize("Kumano-Nachi-shrine") == "Kumano-Nachi Shrine"


def test_a_parenthetical_containing_a_comma_is_stripped_before_the_comma_split():
    # "(Naka-ku, Nagoya)" — the comma is INSIDE the bracket; strip the bracket first
    assert cn.normalize("Fuji Sengen Shrine (Naka-ku, Nagoya)") == "Fuji Sengen Shrine"
    assert cn.normalize("Nagao-jinja (Katsurao, Fukushima)") == "Nagao Shrine"


def test_daijingu_is_not_split_into_dai_plus_jingu():
    assert cn.normalize("Izumo-daijingū") == "Izumo Daijingu"


def test_myojin_does_not_become_a_temple():
    # "Kanda-Myojin" must not match temple "-in" on the "jin"
    assert cn.normalize("Kanda-Myojin") != "Kanda-Myoj-in Temple"


def test_parenthetical_disambiguator_is_stripped():
    assert cn.normalize("Kasuga-taisha (Nara)") == "Kasuga Grand Shrine"


def test_fullwidth_disambiguator_is_stripped():
    assert cn.normalize("Hikawa-jinja（Ōmiya）") == "Hikawa Shrine"


# ─────────────── the default: no suffix → append " Shrine" ───────────────

def test_a_name_with_no_recognised_suffix_gets_shrine_appended():
    # Emma 2026-07-10: the established default. Buddhist devotional names ride it too.
    assert cn.normalize("Arako Kannon") == "Arako Kannon Shrine"
    assert cn.normalize("Kawasaki Daishi") == "Kawasaki Daishi Shrine"
    assert cn.normalize("Category:Shibamata Taishakuten") == "Shibamata Taishakuten Shrine"


def test_the_default_shrine_matches_enwiki_after_the_grader_strips_it():
    # "Arako Kannon Shrine" vs enwiki "Arako Kannon": grader strips " Shrine" → same reading.
    import report_commons_label_accuracy as rep
    assert rep.bucket(cn.normalize("Arako Kannon"), "Arako Kannon") == "exact"


def test_circumflex_long_vowel_folds_to_a_macron():
    assert cn.normalize("Tôfuku-ji") == "Tōfuku-ji Temple"
    assert cn.normalize("Yamada Ten'man-gû") == "Yamada Ten'man-gu Shrine"


# ─────────────── still None: empty / kanji ───────────────

def test_an_empty_name_returns_none():
    assert cn.normalize("") is None
    assert cn.normalize("Category:") is None


def test_a_kanji_commons_name_returns_none():
    # No Latin letters → out of scope for the romaji stage (the kana stage handles it).
    assert cn.normalize("厳島神社") is None


def test_a_bare_suffix_with_no_stem_returns_none():
    assert cn.normalize("-ji") is None
    assert cn.normalize("Jinja") is None
