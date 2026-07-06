"""Tests for fandom_subset_orchestrator.decide — the keep/delete/copyover rule.

Emma 2026-07-06: a miraheze redirect is a valid equivalent (it points at a real target),
so a fandom page at the same title must NOT be orphan-deleted just because both are
redirects — that was wrongly deleting Template:Ill every few days.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fandom_subset_orchestrator import decide  # noqa: E402


def test_miraheze_redirect_keeps_fandom_redirect():
    action, _ = decide("Template:Ill", True, "redirect", set(), set())
    assert action == "skip"


def test_miraheze_redirect_over_real_fandom_content_copies():
    action, _ = decide("Foo", False, "redirect", set(), set())
    assert action == "copyover"


def test_missing_miraheze_deletes():
    assert decide("Foo", False, "missing", set(), set())[0] == "delete"


def test_miraheze_article_skips():
    assert decide("Foo", False, "article", set(), set())[0] == "skip"


def test_protected_fandom_unique_always_skips():
    assert decide("Foo", True, "missing", {"Foo"}, set())[0] == "skip"


def test_main_page_skips():
    assert decide("Main Page", False, "missing", set(), {"Main Page"})[0] == "skip"
