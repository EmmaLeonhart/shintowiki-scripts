"""Tests for interlang_consolidate — merging multiple {{wikidata link}} templates.

Emma 2026-07-06: a page can carry both a QID-only ``{{wikidata link|Q…}}`` and a
separate interwiki-bearing empty-QID ``{{wikidata link||lang|title|…}}`` (the migrated
interlanguage links). They must be actively consolidated into ONE template.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrators.ops import interlang_consolidate as ic  # noqa: E402


def test_merges_qid_and_interwiki_templates(monkeypatch):
    monkeypatch.setenv("ENABLE_INTERLANG_CONSOLIDATE", "1")
    text = (
        "{{wikidata link||ja|Category:X|ar|Category:Y}}\n"
        "[[en:Category:Z]]\n"
        "{{wikidata link|Q123}}\n"
    )
    new, _summary = ic.apply("Category:Foo", text)
    assert new.count("{{wikidata link") == 1
    assert "{{wikidata link|Q123|ja|Category:X|ar|Category:Y|en|Category:Z}}" in new
    assert "[[en:Category:Z]]" not in new


def test_merges_two_templates_without_standalone_links(monkeypatch):
    # No stray [[lang:]] links, but two templates still must merge.
    monkeypatch.setenv("ENABLE_INTERLANG_CONSOLIDATE", "1")
    text = "{{wikidata link||ja|Category:X}}\n{{wikidata link|Q9}}\n"
    new, _ = ic.apply("Category:Foo", text)
    assert new.count("{{wikidata link") == 1
    assert "{{wikidata link|Q9|ja|Category:X}}" in new


def test_single_template_no_links_is_noop(monkeypatch):
    monkeypatch.setenv("ENABLE_INTERLANG_CONSOLIDATE", "1")
    text = "{{wikidata link|Q5}}\n"
    new, summary = ic.apply("Category:Foo", text)
    assert new is None and summary is None


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_INTERLANG_CONSOLIDATE", raising=False)
    text = "{{wikidata link||ja|Category:X}}\n{{wikidata link|Q9}}\n"
    assert ic.apply("Category:Foo", text) == (None, None)
