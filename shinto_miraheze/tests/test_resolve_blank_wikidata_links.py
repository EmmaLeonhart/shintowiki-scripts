"""The Japanese-name extractor is the risky half — pin what it will NOT match.

`resolve_blank_wikidata_links.py` resolves a page to a QID by looking up the
Japanese name the page states for itself. That is the step that reaches
`Shizensha`, whose jawiki sitelink is 自然社 and whose title therefore matches
nothing on any wiki.

It is also the step that can quietly resolve a page to the wrong item. These
articles are full of incidental Japanese — deity names, an address, a
prefecture, a shrine rank — and a bare CJK run picked up anywhere in the body
would hand the sitelink lookup a place name and get back a confident, wrong
answer. So the extractor reads only fields that ANNOUNCE the string as the
subject's name, and the negative tests below are the point of this file.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import pytest

from shinto_miraheze.resolve_blank_wikidata_links import japanese_names  # noqa: E402


def test_native_name_is_the_shizensha_case():
    """Verbatim shape from the page. Emma's todo named Q139921367 as the answer,
    and 自然社 is the jawiki sitelink that reaches it."""
    text = ("{{Infobox religion | name = Shizensha (自然社) | native_name      = 自然社 "
            "| classification = [[Japanese new religion]] (新宗教)")
    assert japanese_names(text, "Shizensha") == ["自然社"]


def test_nihongo_takes_the_second_argument_when_the_first_is_this_page():
    assert (japanese_names("{{Nihongo|Take Shrine|多家神社|Take-jinja}}", "Take Shrine")
            == ["多家神社"])


def test_nihongo_naming_something_else_is_refused():
    """The real one, 2026-09-12. [[Take Shrine]]'s lead says
    `{{nihongo|Sōja|総社}}` — 総社 is a CLASS of shrine, not this shrine — and it
    resolved to Q1107129, the article about sōsha in general. Before this gate the
    same page had already resolved wrongly once, to 竹神社 in Mie. Two confident
    wrong answers for one page is what the romaji argument now prevents."""
    assert japanese_names("{{nihongo|Sōja|総社|}}", "Take Shrine") == []


def test_the_romaji_match_folds_macrons_and_case():
    assert japanese_names("{{nihongo|suikan|水干|}}", "Suikan") == ["水干"]
    assert japanese_names("{{nihongo|Tōzan|東山|}}", "Tozan") == ["東山"]


def test_a_bare_lang_ja_no_longer_counts():
    """`{{lang|ja|…}}` marks text as Japanese; it does not claim the text names
    this page's subject. Removed 2026-09-12 with the rest of the Take Shrine
    clean-up."""
    assert japanese_names("{{lang|ja|皇大神宮}}", "Kotai Jingu") == []


@pytest.mark.parametrize("text", [
    "A shrine in 大阪 dedicated to 天照大神, rebuilt in 1947.",
    "It holds the rank of 県社 and stands near 阿倍野区.",
    "[[Category:Pages with 50+ untranslated japanese characters]] 神社",
])
def test_incidental_japanese_in_the_body_is_not_a_name(text):
    """The whole reason the extractor reads fields and not prose. A place name
    or a deity name lifted from the body resolves to a real Wikidata item —
    just not this page's."""
    assert japanese_names(text, "Some Shrine") == []


def test_names_are_ordered_and_deduplicated():
    text = "| native_name = 自然社 |\n{{Nihongo|Shizensha|大祖教|y}}"
    assert japanese_names(text, "Shizensha") == ["自然社", "大祖教"]


def test_no_title_disables_the_nihongo_source_rather_than_the_gate():
    """An absent title is precisely when a caller would not notice the gate
    silently not running, so the source is skipped instead of let through."""
    assert japanese_names("{{Nihongo|Sōja|総社|}}", "") == []
    assert japanese_names("| native_name = 自然社 |", "") == ["自然社"]


def test_a_single_character_name_is_not_taken():
    """`{2,}` — one kanji is too weak to key a sitelink lookup on."""
    assert japanese_names("| native_name = 社 |", "X Shrine") == []


def test_the_lead_bold_parenthetical_is_the_canonical_name():
    """The MediaWiki lead convention: the bolded page title, then the native name.
    Measured across all 50 refusals on 2026-09-12 before being added — 16 pages
    carry it, 4 of those names are jawiki sitelinks, all 4 correct. It is what
    finally gets [[Take Shrine]] to Q11430665."""
    text = "'''Take Shrine''' (多家神社) is a Shinto shrine in Hiroshima."
    assert japanese_names(text, "Take Shrine") == ["多家神社"]


def test_a_lead_bold_naming_something_else_is_refused():
    """Same gate as Nihongo: a bolded run that is not this page's title belongs to
    some other subject."""
    text = "'''Sōja shrine''' (総社) is a class of shrine."
    assert japanese_names(text, "Take Shrine") == []


def test_the_lead_wins_over_a_mid_prose_nihongo_on_the_same_page():
    """[[Take Shrine]] in shape: the lead names 多家神社, the prose then uses
    {{nihongo|Sōja|総社}} for a term. Only the first is this shrine, and 総社
    resolved to Q1107129 — the article about sōsha in general — when it was let
    through."""
    text = ("'''Take Shrine''' (多家神社) is the {{nihongo|Sōja|総社}} of Aki Province.")
    assert japanese_names(text, "Take Shrine") == ["多家神社"]
