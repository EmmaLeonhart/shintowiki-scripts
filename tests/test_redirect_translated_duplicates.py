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
    MIN_TARGET_RATIO, PAIR_HEADINGS, append_categories, carried_categories,
    RATIO_EXEMPT, check_pair, heading_classes, load_pairs, normalize_heading, sections,
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


# --- the empty-heading exemption -------------------------------------------
# Measured 2026-08-28 across the 16 held pairs: the largest single cause of a false
# refusal was a heading with nothing under it. 島津国造 and 熊野国造 were held on a
# ``Base`` that only wraps ``=== Territory ===``; 上毛野国造 on a ``Genealogy`` with a
# blank line under it; 伊勢国造 on an equally blank ``墓``. Nothing was missing from any
# of those English pages.

def _wrapper_page(pad=PAD):
    """``== Base ==`` with no body, nesting ``=== Territory ===`` — the real shape."""
    return ("== Overview ==\n\n=== Ancestry ===\n%s\n== Base ==\n\n"
            "=== Territory ===\n%s\n" % (pad, pad))


def test_an_empty_source_heading_does_not_hold_the_pair_back():
    ok, reason, _ = check_pair(_wrapper_page(),
                               _page(["Ancestry", "Governed Region"], PAD * 4))
    assert ok, reason


def test_an_empty_target_heading_cannot_vouch_for_a_missing_section():
    """The other direction — otherwise a blank stub would wave content through."""
    target = "== Ancestry ==\n%s\n== Tombs ==\n\n" % (PAD * 6)
    ok, reason, _ = check_pair(_page(["Ancestry", "Tombs"]), target)
    assert not ok
    assert "'tombs'" in reason


def test_a_section_with_real_content_is_still_required():
    """那須国造: its Territory holds 1,993b the English page has nowhere."""
    ok, reason, _ = check_pair(_page(["Base", "Territory"]),
                               _page(["Headquarters"], PAD * 8))
    assert not ok
    assert "'territory'" in reason


def test_sections_pairs_each_heading_with_its_own_body():
    got = sections("lead\n== A ==\nalpha\n=== B ===\n\n== C ==\ngamma\n")
    assert [h for h, _ in got] == ["A", "B", "C"]
    assert got[0][1].strip() == "alpha"
    assert got[1][1].strip() == ""
    assert got[2][1].strip() == "gamma"


# --- per-pair heading equivalences ------------------------------------------

def test_a_pair_specific_heading_resolves_for_that_pair_only():
    """闘鶏大山主's ice house is its himuro — but only on that pair."""
    src = _page(["Overview", "The Ice House of Tsuge"])
    dst = _page(["Overview", "The Himuro of Tsuge"], PAD * 4)
    ok, reason, _ = check_pair(src, dst, source_title="闘鶏大山主")
    assert ok, reason
    ok, reason, _ = check_pair(src, dst)
    assert not ok, "the equivalence must not leak to pairs it was not made about"
    assert "unrecognised heading" in reason


def test_base_maps_to_territory_for_akashi_and_nowhere_else():
    """明石国造's Base IS the target's Territory; 那須国造's Base and Territory are two
    separate sections, so a general base==territory class would lose one of them."""
    ok, _, _ = check_pair(_page(["Base"]), _page(["Territory"], PAD * 4),
                          source_title="明石国造")
    assert ok
    ok, reason, _ = check_pair(_page(["Base", "Territory"]),
                               _page(["Territory"], PAD * 8), source_title="明石国造")
    assert ok, reason  # only Base is remapped; Territory still needs its own match
    ok, _, _ = check_pair(_page(["Base"]), _page(["Territory"], PAD * 4))
    assert not ok


# Keys whose redirect has LANDED. A PAIR_HEADINGS key leaves duplicate_qids.state on
# the day its pair is redirected -- the collector stops grouping a source that is a
# redirect -- so "no longer a live pair" is the success condition, not staleness.
REDIRECTED_PAIRS = frozenset({
    # All five were redirected on 2026-08-29 by run 33235580849.
    "天道根命", "明石国造", "紀伊国造", "針間鴨国造", "闘鶏大山主",
    # The 2026-08-30 batch. Six pairs were worked and redirected that day; these are the
    # four that also hold a key above, so they are the four that belong here. 建稲種命
    # (→ Takeinadane) and 那須国造 (→ Nasu no Kuni no Miyatsuko) landed the same day but
    # hold no key, and this set is the record of KEYS whose redirect has landed --
    # listing a non-key would make it a log of the batch rather than the record these
    # two assertions actually read.
    #
    # Each was checked against the LIVE wiki on 2026-09-04 before being recorded, because
    # a name added here on the strength of the queue saying it was done would turn the
    # assertion into a rubber stamp -- the thing it exists to catch is a key naming no
    # pair at all. All four are #REDIRECT by EmmaBot on 2026-08-30, each pointing at a
    # page that exists and is not itself a redirect:
    #   健磐龍命  → Takeiwatatsu-no-Mikoto      (44,829b)  21:33Z
    #   尾張氏    → Owari clan                  (17,180b)  20:32Z
    #   牟義都国造 → Mukizu no Kuni no Miyatsuko  (6,821b)  19:22Z
    #   神大根王  → Kami Ōne                     (5,297b)  23:19Z
    # 神大根王's target is 5,297b, the exact figure ``RATIO_EXEMPT`` records from its
    # section-by-section reading, so the exemption is still describing this pair.
    "健磐龍命", "尾張氏", "牟義都国造", "神大根王",
})


def test_every_pair_headings_key_was_a_real_pair():
    """A key must name a pair that is live OR one whose redirect has landed.

    This asserted every key was still LIVE, and therefore failed the moment the
    mechanism worked: the nine redirects of 2026-08-29 took all five keys out of
    ``duplicate_qids.state``, and CI went red on the next commit to touch the tree for
    that reason alone. The thing worth guarding is unchanged -- a key that names no
    pair at all is a typo or a decision recorded against the wrong page -- so a
    redirected key has to be recorded rather than merely absent.
    """
    japanese = {jp for _, jp, _ in load_pairs()}
    unaccounted = sorted(set(PAIR_HEADINGS) - japanese - REDIRECTED_PAIRS)
    assert not unaccounted, unaccounted


def test_the_ratio_gate_still_refuses_a_pair_that_is_not_exempt():
    """The exemption is per pair; nothing else may slip through with it."""
    small_target = _page(["Overview"], "x")
    big_source = _page(["Overview"], PAD * 8)
    ok, reason, _ = check_pair(big_source, small_target)
    assert not ok and "below the" in reason and "gate" in reason


def test_an_exempt_pair_skips_the_ratio_gate_but_not_the_heading_gate():
    """神大根王's exemption exists because the gate was measuring its infobox.

    It must not become a way past the check that actually looks at content: a source
    heading with no counterpart is still refused for an exempt pair.
    """
    exempt = sorted(RATIO_EXEMPT)[0]
    small_target = _page(["Overview"], "x")
    big_source = _page(["Overview"], PAD * 8)
    ok, reason, _ = check_pair(big_source, small_target, source_title=exempt)
    assert ok, reason

    missing = _page(["Overview", "Territory"], PAD * 8)
    ok, reason, _ = check_pair(missing, small_target, source_title=exempt)
    assert not ok
    assert "no counterpart" in reason and "territory" in reason


def test_every_ratio_exempt_key_is_a_live_or_redirected_pair():
    japanese = {jp for _, jp, _ in load_pairs()}
    unaccounted = sorted(RATIO_EXEMPT - japanese - REDIRECTED_PAIRS)
    assert not unaccounted, unaccounted


def test_no_redirected_pair_is_still_live():
    """The other direction: a key listed as redirected must not still be pairing."""
    japanese = {jp for _, jp, _ in load_pairs()}
    still_live = sorted(REDIRECTED_PAIRS & japanese)
    assert not still_live, still_live


def test_pair_headings_are_normalised_forms():
    """They are looked up post-``normalize_heading``, so they must match that output."""
    for title, mapping in PAIR_HEADINGS.items():
        for heading in mapping:
            assert normalize_heading(heading) == heading, (title, heading)
