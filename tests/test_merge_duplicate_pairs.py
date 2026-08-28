"""A merge replaces the target's body, so it must refuse when the target is fuller.

Emma asked for the Japanese-titled page's content merged into the English one and
the Japanese redirected. This script does that only where the Japanese-titled page
genuinely holds more — measured 2026-08-28, that is 2 of the 12 candidates, because
ten have an English page of comparable or greater size already carrying
``{{translated page}}``.

The gate is the whole safety property. Because ``merge_text`` overwrites the
target's body, running it on a pair where the target is the fuller page would
destroy content — the same failure the JP-script heuristic was gated for, and the
ratio is checked against the LIVE pages at run time rather than against what was
true when a pair was added to ``MERGES``.
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

from shinto_miraheze.merge_duplicate_pairs import (  # noqa: E402
    MERGES, MIN_SOURCE_RATIO, merge_text,
)

BIG = ("== Overview ==\n" + ("detailed content. " * 200) +
       "\n[[Category:Shinano Province]]\n[[Category:Ō clan]]\n")
SMALL = ("== Overview ==\nthin summary.\n"
         "{{wikidata link|Q11595951|ja|科野国造}}\n"
         "[[Category:History of Nagano Prefecture]]\n[[Category:Shinano Province]]\n")


def test_the_source_body_wins_when_it_is_substantially_fuller():
    merged, note = merge_text(BIG, SMALL)
    assert merged is not None, note
    assert "detailed content." in merged
    assert "thin summary." not in merged


def test_it_refuses_when_the_target_is_the_fuller_page():
    """THE guard. Overwriting a fuller target would destroy content."""
    merged, reason = merge_text(SMALL, BIG)
    assert merged is None
    assert "below the" in reason and "gate" in reason


def test_it_refuses_at_the_ratio_boundary_rather_than_guessing():
    target = "x" * 1000
    just_under = "y" * int(1000 * MIN_SOURCE_RATIO - 1)
    assert merge_text(just_under, target)[0] is None
    just_over = "== H ==\n" + "y" * int(1000 * MIN_SOURCE_RATIO + 10)
    assert merge_text(just_over, target)[0] is not None


def test_categories_are_unioned_not_replaced():
    """The target legitimately owns its categories; the merge must not drop them."""
    merged, _ = merge_text(BIG, SMALL)
    assert "[[Category:History of Nagano Prefecture]]" in merged   # target-only
    assert "[[Category:Ō clan]]" in merged                         # source-only
    assert "[[Category:Shinano Province]]" in merged               # both
    assert merged.count("[[Category:Shinano Province]]") == 1      # not duplicated


def test_the_targets_wikidata_link_is_kept_and_the_sources_dropped():
    src = BIG + "{{wikidata link|Q99999|ja|wrong}}\n"
    merged, _ = merge_text(src, SMALL)
    assert "Q11595951" in merged
    assert "Q99999" not in merged
    assert merged.count("wikidata link") == 1


def test_a_source_that_is_already_a_redirect_is_refused():
    merged, reason = merge_text("#REDIRECT [[Somewhere]]\n", SMALL)
    assert merged is None
    assert "already a redirect" in reason


def test_a_target_that_is_a_redirect_is_refused():
    merged, reason = merge_text(BIG, "#REDIRECT [[Somewhere]]\n")
    assert merged is None
    assert "target is a redirect" in reason


def test_only_pairs_that_passed_the_measurement_are_listed():
    """Ten of the twelve candidates are redirect-only, not merges."""
    assert MERGES == [("科野国造", "Shinano no Kuni no Miyatsuko"),
                      ("国造", "Kuni no miyatsuko")]
