"""Tests for the category-translation collector (queue item 5 back half).

The collector folds finished RAG work-files (TRANSLATED marker filled) into
category_moves.csv and never trusts a malformed / no-op / unfinished answer.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import collect_category_translations as c  # noqa: E402
import build_category_translation_queue as b  # noqa: E402


def test_parse_done():
    src, tr, skip = c.parse_file(
        "<!-- SOURCE: Category:三条市の歴史 -->\n"
        "<!-- TRANSLATED: Category:History of Sanjō, Niigata -->\n")
    assert src == "Category:三条市の歴史"
    assert tr == "Category:History of Sanjō, Niigata"
    assert skip is None


def test_parse_pending_empty_translated():
    src, tr, skip = c.parse_file("<!-- SOURCE: Category:X -->\n<!-- TRANSLATED: -->")
    assert src == "Category:X" and tr == "" and skip is None


def test_parse_skip():
    src, tr, skip = c.parse_file(
        "<!-- SOURCE: Category:X -->\n<!-- TRANSLATED: -->\n<!-- SKIP: nonsense name -->")
    assert skip == "nonsense name"


def test_worker_file_has_markers_and_context():
    txt = b._work_file("三条市の歴史", ["三条市 page A", "page B"], "{{wikidata link||ja|Cat}}")
    assert "<!-- SOURCE: Category:三条市の歴史 -->" in txt
    assert "<!-- TRANSLATED: -->" in txt
    assert "page A" in txt and "wikidata link" in txt


def test_has_cjk_filters_already_english():
    # genuinely Japanese-named → queue
    assert b._has_cjk("三条市の歴史")
    assert b._has_cjk("さいたま市の神社")
    # already-English residual (failed phase-1 QID) → NOT queued for RAG
    assert not b._has_cjk("Buildings and structures in Kurume")
    assert not b._has_cjk("1988 books")


def test_safe_filename_matches_sync_convention():
    # ':' -> %3A, '/' -> %2F, with the Category: prefix, .wiki suffix
    assert b._safe_filename("三条市の歴史") == "Category%3A三条市の歴史.wiki"
    assert b._safe_filename("A/B") == "Category%3AA%2FB.wiki"


def test_roundtrip_worker_answer_parses():
    # A worker fills the marker; the collector must read it back.
    txt = b._work_file("X市の神社", ["p"], "wt")
    filled = txt.replace("<!-- TRANSLATED: -->",
                         "<!-- TRANSLATED: Category:Shinto shrines in X -->")
    src, tr, skip = c.parse_file(filled)
    assert src == "Category:X市の神社"
    assert tr == "Category:Shinto shrines in X"
