"""Overwriting a live page with a redirect requires a proven Wikidata redirect.

The JP-script heuristic (Japanese title loses to the rōmaji one) was safe for as
long as ``perform_move`` only ever performed a MediaWiki *move*: a move cannot
clobber an existing page, so the branch returned ``skipped:dst exists as real
page`` and a wrong guess cost nothing.

Adding a redirect-over-content path on 2026-08-26 removed that protection and
turned the same heuristic destructive. Measured on 2026-08-27, its 45 pending
moves included 健磐龍命 -- 19,095 bytes with ``Nihon Shoki`` and ``Fudoki of Higo
Province`` sections -- redirecting onto a 13,161-byte page structured differently
and containing neither. Two titles sharing a QID is not evidence that one article
contains the other.

So content overwrite is gated on ``proven``, which the caller sets only for a move
whose reason is a resolved Wikidata redirect.
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

from shinto_miraheze.dedupe_duplicate_qids import perform_move  # noqa: E402


class _Page:
    """Minimal mwclient.Page stand-in."""

    def __init__(self, text="", exists=True):
        self._text = text
        self.exists = exists
        self.saved = None
        self.moved_to = None

    def text(self):
        return self._text

    def save(self, text, summary=""):
        self.saved = (text, summary)

    def move(self, dst, reason="", no_redirect=False):
        self.moved_to = dst


class _Site:
    def __init__(self, pages):
        self.pages = pages


REAL_ARTICLE = "== Overview ==\nSubstantial content that exists only here.\n"


def _site(src_text=REAL_ARTICLE, dst_exists=True, dst_text=REAL_ARTICLE):
    return _Site({"SRC": _Page(src_text), "DST": _Page(dst_text, exists=dst_exists)})


def test_unproven_move_never_overwrites_a_live_page():
    """THE regression guard: the JP-script heuristic must not clobber content."""
    site = _site()
    result = perform_move(site, "SRC", "DST", "tag", apply=True, proven=False)
    assert result.startswith("skipped:")
    assert "unproven" in result
    assert site.pages["SRC"].saved is None
    assert site.pages["SRC"].moved_to is None


def test_proven_move_does_overwrite():
    site = _site()
    result = perform_move(site, "SRC", "DST", "tag", apply=True, proven=True)
    assert result == "redirected"
    text, summary = site.pages["SRC"].saved
    assert text.startswith("#REDIRECT [[DST]]")
    assert "same Wikidata item" in summary


def test_proven_dry_run_writes_nothing():
    site = _site()
    result = perform_move(site, "SRC", "DST", "tag", apply=False, proven=True)
    assert result.startswith("dry:")
    assert site.pages["SRC"].saved is None


def test_git_synced_category_is_carried_across():
    """Dropping it makes the next sync untrack and delete the local file."""
    site = _site(src_text=REAL_ARTICLE + "\n[[Category:Git synced pages]]\n")
    perform_move(site, "SRC", "DST", "tag", apply=True, proven=True)
    text, _ = site.pages["SRC"].saved
    assert "[[Category:Git synced pages]]" in text


def test_no_category_added_when_the_source_never_had_one():
    site = _site()
    perform_move(site, "SRC", "DST", "tag", apply=True, proven=True)
    text, _ = site.pages["SRC"].saved
    assert "Git synced pages" not in text


def test_a_free_destination_still_uses_a_real_move_even_unproven():
    """Nothing to clobber, so the original move path is untouched."""
    site = _site(dst_exists=False)
    result = perform_move(site, "SRC", "DST", "tag", apply=True, proven=False)
    assert result == "moved"
    assert site.pages["SRC"].moved_to == "DST"


def test_a_source_that_is_already_a_redirect_is_left_alone():
    site = _site(src_text="#REDIRECT [[Somewhere]]")
    result = perform_move(site, "SRC", "DST", "tag", apply=True, proven=True)
    assert result == "skipped:src already redirect"
    assert site.pages["SRC"].saved is None


# ── a conditional skip must not be buried in the done-state ───────────────
#
# main() records skips into dedupe_duplicate_qids.state and filters `pending`
# against it, so anything recorded never runs again. That is right for a finished
# page and wrong for one merely awaiting evidence — it silently retired the 44
# JP-script pages, which skip for lack of proof, not because they are resolved.

from shinto_miraheze.dedupe_duplicate_qids import is_terminal_skip  # noqa: E402


def test_a_finished_source_is_terminal():
    assert is_terminal_skip("skipped:src already redirect")
    assert is_terminal_skip("skipped:src missing")


def test_an_unproven_heuristic_skip_is_conditional():
    """It comes back the moment a Wikidata redirect or a human merge arrives."""
    assert not is_terminal_skip(
        "skipped:dst exists as real page (heuristic move, unproven)")


def test_a_destination_that_is_currently_a_redirect_is_conditional():
    assert not is_terminal_skip("skipped:dst is a redirect (title collision)")


def test_the_real_perform_move_outcome_for_an_unproven_move_is_conditional():
    """Wire the two halves together rather than trusting the string by eye."""
    site = _site()
    result = perform_move(site, "SRC", "DST", "tag", apply=True, proven=False)
    assert result.startswith("skipped:")
    assert not is_terminal_skip(result)


def test_the_real_outcome_for_an_already_redirected_source_is_terminal():
    site = _site(src_text="#REDIRECT [[Somewhere]]")
    result = perform_move(site, "SRC", "DST", "tag", apply=True, proven=True)
    assert is_terminal_skip(result)
