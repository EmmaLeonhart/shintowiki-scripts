"""Tests for language_registry — B3: the single source of truth for which
query.csv languages have a label generator and which are the uncovered long tail."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import language_registry as r  # noqa: E402


def test_known_generators_are_covered():
    for lang in ["tr", "de", "ru", "fa", "hi", "fr", "pt", "zh", "ko", "tok", "id"]:
        assert lang in r.COVERED, f"{lang} should be a covered language"


def test_source_langs_not_treated_as_todo():
    rows = [("ja", 30000), ("en", 25000), ("de", 267)]
    covered, todo = r.split_coverage(rows)
    todo_langs = {c["lang"] for c in todo}
    assert "ja" not in todo_langs and "en" not in todo_langs


def test_uncovered_language_is_todo():
    # my (Burmese) still has no generator; th gained one (wunsen romaji→Thai)
    # 2026-07-06; pl gained one in the 2026-07-04 rung-2 tier.
    rows = [("de", 267), ("pl", 35), ("th", 33), ("my", 25)]
    covered, todo = r.split_coverage(rows)
    cov_langs = {c["lang"] for c in covered}
    todo_langs = {c["lang"] for c in todo}
    assert {"de", "pl", "th"} <= cov_langs
    assert "my" in todo_langs
    assert "th" not in todo_langs


def test_todo_sorted_by_count_desc():
    rows = [("th", 33), ("sv", 37), ("pl", 35)]
    _, todo = r.split_coverage(rows)
    counts = [c["count"] for c in todo]
    assert counts == sorted(counts, reverse=True)


def test_mul_is_skipped():
    rows = [("mul", 39), ("de", 267)]
    _, todo = r.split_coverage(rows)
    assert "mul" not in {c["lang"] for c in todo}
