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
    # cdo (Min Dong — mixed Chinese chars + Bàng-uâ-cê romanization, not a plain
    # transliteration) still has no generator; th/my/pa/new/mad/km/lo/dz/shn all
    # gained one 2026-07-06 (wunsen for Thai, Aksharamukha for the Brahmic set).
    rows = [("de", 267), ("my", 25), ("th", 33), ("cdo", 5)]
    covered, todo = r.split_coverage(rows)
    cov_langs = {c["lang"] for c in covered}
    todo_langs = {c["lang"] for c in todo}
    assert {"de", "my", "th"} <= cov_langs
    assert "cdo" in todo_langs


def test_todo_sorted_by_count_desc():
    rows = [("th", 33), ("sv", 37), ("pl", 35)]
    _, todo = r.split_coverage(rows)
    counts = [c["count"] for c in todo]
    assert counts == sorted(counts, reverse=True)


def test_mul_is_skipped():
    rows = [("mul", 39), ("de", 267)]
    _, todo = r.split_coverage(rows)
    assert "mul" not in {c["lang"] for c in todo}
