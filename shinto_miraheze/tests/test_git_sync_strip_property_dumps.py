"""Tests for the Wikidata-property-dump strip (Emma 2026-07-06).

The strip removes `== <property> (Pxxx) ==` sections + their bullet bodies and
NOTHING else — infobox, {{wikidata link}}, interwiki, the real article, and
categories must survive. This is destructive on live wiki pages, so the boundary
behaviour is pinned here.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import git_sync_strip_property_dumps as s  # noqa: E402


PAGE = """{{Infobox religious building
| name = Test Shrine
| deity = {{ill|Foo|qid=Q1}}
}}

{{nihongo|'''Test Shrine'''|試験神社}} is a shinto shrine.

== instance of (P31) ==

* {{ill|Shinto shrine|qid=Q845945}}
* {{ill|Shikinaisha|qid=Q134917286}}

== part of (P361) ==

* {{ill|List|qid=Q1}}
** Series ordinal: 35
** P155: {{ill|Prev|qid=Q2}}

== street address (P6375) ==

* {'text': 'somewhere', 'language': 'ja'}

[[ja:試験神社]]

{{wikidata link|Q999|ja|試験神社}}

== Japanese content ==
{{Shrine|Name=Test}}
'''Test Shrine''' is a shrine.
=== History ===
Founded long ago.

== Categories ==
[[Category:Shinto shrines in Nowhere]]
[[Category:sync these pages now]]
"""


def test_removes_all_property_sections():
    out = s.strip_property_dump(PAGE)
    assert "(P31)" not in out
    assert "(P361)" not in out
    assert "(P6375)" not in out
    assert "instance of" not in out
    assert "Series ordinal" not in out  # sub-bullets go too


def test_keeps_infobox_wikidata_interwiki_article_categories():
    out = s.strip_property_dump(PAGE)
    assert "{{Infobox religious building" in out
    assert "{{wikidata link|Q999" in out
    assert "[[ja:試験神社]]" in out
    assert "== Japanese content ==" in out
    assert "{{Shrine|Name=Test}}" in out
    assert "=== History ===" in out           # article's own headings untouched
    assert "[[Category:Shinto shrines in Nowhere]]" in out


def test_retag_swaps_sync_now_for_git_synced():
    out = s.retag(s.strip_property_dump(PAGE))
    assert "sync these pages now" not in out
    assert "[[Category:Git synced pages]]" in out


def test_non_property_h2_heading_is_kept():
    # A normal '== Foo ==' heading (no Pxxx) must NOT be stripped.
    txt = "== Overview ==\nsome prose\n\n== instance of (P31) ==\n* x\n"
    out = s.strip_property_dump(txt)
    assert "== Overview ==" in out and "some prose" in out
    assert "(P31)" not in out


def test_redirect_page_survives():
    txt = ("{{Infobox religious building\n| name = R\n}}\n\n"
           "== instance of (P31) ==\n* {{ill|x|qid=Q1}}\n\n"
           "== Japanese content ==\n#REDIRECT [[Other Shrine]]\n\n"
           "== Categories ==\n[[Category:Foo]]\n")
    out = s.strip_property_dump(txt)
    assert "#REDIRECT [[Other Shrine]]" in out
    assert "(P31)" not in out
