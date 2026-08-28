"""A property dump is identified by its HEADINGS, not by how much text it holds.

Emma handed back six duplicate groups on 2026-08-28 with "you make your own
decision based on reading the pages". Reading them showed every one was a real
article beside a Wikidata property dump -- and that the prose-length test MISSED
ALL SIX, scoring those dumps at 308-3,726 bytes against a 200-byte threshold.

They clear it because a dump is not only property sections: it also carries
``== References ==`` and an imported ``== Japanese Wikipedia content ==`` block,
and citation text measures like prose however it is stripped.

The heading signal separates them completely -- measured on those six pairs, the
dumps carry 6-10 ``== something (Pnnn) ==`` headings and the articles carry
exactly ZERO. So the count alone decides. A majority test was tried first and
failed four of the six, because importing the jawiki article's own headings
(祭神, 脚注, 外部リンク) costs a dump its majority while leaving it a dump.
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

from shinto_miraheze.classify_duplicate_group_pages import (  # noqa: E402
    MIN_PROPERTY_HEADINGS, is_property_dump,
)

# The real shape, from `Achi Shrine (Achi)` and `Teranomikoto Shrine`.
DUMP = """{{Infobox religious building|name=X}}
== instance of (P31) ==
* a
== part of (P361) ==
* b
== located in the administrative territorial entity (P131) ==
* c
== coordinate location (P625) ==
* d
== References ==
<references />
== Japanese Wikipedia content ==
=== 祭神 ===
some imported text
=== 脚注 ===
=== 外部リンク ===
"""

ARTICLE = """{{Infobox religious building|name=X}}
'''X Shrine''' is a shinto shrine.
== Enshrined deities ==
text
== History ==
text
== Local information ==
text
== References ==
<references />
"""


def test_a_property_dump_is_detected():
    assert is_property_dump(DUMP)


def test_a_real_article_is_not():
    assert not is_property_dump(ARTICLE)


def test_the_imported_jawiki_headings_do_not_rescue_a_dump():
    """The majority test failed here: 4 property headings against 6 others.

    A dump that imports the jawiki article carries 祭神 / 脚注 / 外部リンク and loses
    its majority while remaining, entirely, a dump.
    """
    import re
    props = len(re.findall(r"^=+.*\(P\d+\).*=+$", DUMP, re.MULTILINE))
    others = len(re.findall(r"^=+[^=\r\n]+=+$", DUMP, re.MULTILINE)) - props
    assert others >= props, "fixture no longer reproduces the majority-test trap"
    assert is_property_dump(DUMP)


def test_a_page_with_no_headings_is_not_called_a_dump():
    """The tiny stubs have no headings; prose length decides those, not this."""
    assert not is_property_dump("{{Infobox|x}} is a shinto shrine.\n")


def test_one_or_two_property_headings_is_not_enough():
    """A real article may legitimately mention a property section or two."""
    text = ARTICLE + "\n== described by source (P1343) ==\n* x\n"
    assert not is_property_dump(text)
    assert MIN_PROPERTY_HEADINGS == 3


def test_the_threshold_is_reached_at_exactly_three():
    text = "== a (P1) ==\n== b (P2) ==\n"
    assert not is_property_dump(text)
    assert is_property_dump(text + "== c (P3) ==\n")


def test_a_long_dump_still_reads_as_a_dump():
    """Byte count must not rescue it — that was the whole failure."""
    padded = DUMP + ("filler prose. " * 500)
    assert is_property_dump(padded)
