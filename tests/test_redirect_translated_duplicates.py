"""A redirect makes the source unreachable, so it must refuse when the source holds more.

The counterpart of ``merge_duplicate_pairs``: that one runs where the Japanese-titled
page is fuller and its body has to survive; this one runs where the English page is
already the superset and only the duplicate title is left.

The two gates are the whole safety property, and both are checked against LIVE text:

* **byte ratio** — the English page is never the smaller of the two. Without it,
  健磐龍命 (19,798b, with Nihon Shoki / Fudoki / Engishiki sections) would have been
  redirected onto a 13,510b page carrying none of them.
* **heading correspondence, not heading COUNT** — count was the metric that
  mis-classified this set twice. An unrecognised heading REFUSES: an unknown never
  authorises an edit.
"""
import os
import sys

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "shinto_miraheze")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shinto_miraheze.redirect_translated_duplicates import (  # noqa: E402
    MIN_TARGET_RATIO, append_categories, carried_categories, check_pair,
    heading_classes, load_pairs, normalize_heading,
)

PAD = "prose. " * 60


def _page(headings, pad=PAD, cats=()):
    body = "".join("== %s ==\n%s\n" % (h, pad) for h in headings)
    return body + "".join("[[Category:%s]]\n" % c for c in cats)


JP_SECTIONS = ["Overview", "Name", "Ancestry", "Clan", "Base", "Territory",
               "Tutelary Shrines", "Descendants", "See also", "References"]
# The same article translated a second time, at the English title, with every
# section renamed. This is what the real pairs look like.
EN_SECTIONS = ["Overview", "Naming", "Ancestors", "Clan", "Headquarters", "Territory",
               "Clan Shrines", "Descendants", "Related Articles", "References"]


def test_renamed_sections_still_correspond():
    """Not one heading matches by string, yet every one has a counterpart."""
    ok, reason, detail = check_pair(_page(JP_SECTIONS), _page(EN_SECTIONS, PAD * 3))
    assert ok, reason
    assert detail["ratio"] > 1.0


def test_refuses_when_the_english_page_is_smaller():
    """The 健磐龍命 case: a redirect here would strand the fuller page."""
    ok, reason, _ = check_pair(_page(JP_SECTIONS, PAD * 3), _page(EN_SECTIONS))
    assert not ok
    assert "below the %sx gate" % MIN_TARGET_RATIO in reason


def test_refuses_a_missing_section_even_when_the_english_page_is_bigger():
    """Size alone is not the gate — 建稲種命 passes on bytes and lacks an Overview."""
    ok, reason, _ = check_pair(_page(["Overview", "Genealogy"]),
                               _page(["Genealogy", "Notelist"], PAD * 4))
    assert not ok
    assert "'overview'" in reason


def test_heading_count_parity_does_not_pass_a_pair():
    """The discarded metric: equal counts, one real section replaced by another."""
    ok, reason, _ = check_pair(_page(["Overview", "Territory"]),
                               _page(["Overview", "Genealogy"], PAD * 4))
    assert not ok
    assert "'territory'" in reason


def test_unrecognised_heading_refuses_rather_than_guesses():
    """闘鶏大山主's 'The Ice House of Tsuge' — unknown never authorises an edit."""
    ok, reason, _ = check_pair(_page(["Overview", "The Ice House of Tsuge"]),
                               _page(["Overview", "The Himuro of Tsuge"], PAD * 4))
    assert not ok
    assert "unrecognised heading" in reason


def test_apparatus_headings_are_exempt():
    """Missing footnotes lose no article content, in either script."""
    ok, _, _ = check_pair(_page(["Overview", "脚注", "関連項目"]),
                          _page(["Overview"], PAD * 4))
    assert ok


def test_japanese_headings_correspond_to_their_english_translations():
    ok, reason, _ = check_pair(
        _page(["概要", "表記", "祖先", "氏族", "本拠", "支配領域", "氏神", "系図"]),
        _page(["Overview", "Name", "Ancestry", "Clan", "Base of Operations",
               "Territory", "Tutelary Deities", "Genealogy"], PAD * 3))
    assert ok, reason


def test_trailing_etc_normalises():
    """白河国造's 'Tutelary Shrine, etc.' is the shrine section, not an unknown."""
    assert normalize_heading("Tutelary Shrine, etc.") == "tutelary shrine"
    assert heading_classes("Tutelary Shrine, etc.") == {"shrine"}


def test_an_already_redirected_source_is_refused():
    """Idempotence: a re-run cannot double-apply."""
    ok, reason, _ = check_pair("#REDIRECT [[Kuni no miyatsuko]]\n", _page(EN_SECTIONS))
    assert not ok
    assert "already a redirect" in reason


def test_a_redirect_target_is_refused():
    ok, reason, _ = check_pair(_page(JP_SECTIONS), "#REDIRECT [[Somewhere]]\n")
    assert not ok
    assert "target is a redirect" in reason


def test_jawiki_and_maintenance_categories_are_not_carried_over():
    """Measured 2026-08-28: source-only cats are jawiki imports plus source-state tags."""
    source = _page(JP_SECTIONS, cats=[
        "下野国", "栃木県の歴史",                  # jawiki category names
        "Need translation",                        # describes the SOURCE
        "Pages with 500+ untranslated japanese characters",
        "Usa clan",                                # a real classification
    ])
    assert carried_categories(source, _page(EN_SECTIONS)) == ["Usa clan"]


def test_a_category_the_target_already_has_is_not_duplicated():
    source = _page(JP_SECTIONS, cats=["Usa clan"])
    assert carried_categories(source, _page(EN_SECTIONS, cats=["Usa clan"])) == []


def test_carried_categories_are_appended_and_nothing_is_removed():
    target = _page(EN_SECTIONS, cats=["Kuni no miyatsuko"])
    out = append_categories(target, ["Usa clan"])
    assert "[[Category:Kuni no miyatsuko]]" in out
    assert out.rstrip().endswith("[[Category:Usa clan]]")
    assert append_categories(target, []) == target


def test_pairs_are_derived_from_live_state_not_hardcoded():
    """The count has been mis-stated four times by reusing a devlog figure."""
    pairs = load_pairs()
    assert pairs, "no pairs derived from the state file"
    for qid, jp, en in pairs:
        assert qid.startswith("Q")
        assert ":" not in jp and ":" not in en, "templates must be excluded"
    titles = [jp for _, jp, _ in pairs]
    assert len(titles) == len(set(titles))
