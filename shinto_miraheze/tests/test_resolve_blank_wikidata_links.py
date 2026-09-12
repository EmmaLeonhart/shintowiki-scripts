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
    assert japanese_names(text) == ["自然社"]


def test_nihongo_takes_the_second_positional_argument():
    assert japanese_names("{{Nihongo|Take Shrine|竹神社|Take-jinja}}") == ["竹神社"]


def test_lang_ja_counts():
    assert japanese_names("{{lang|ja|皇大神宮}}") == ["皇大神宮"]


@pytest.mark.parametrize("text", [
    "A shrine in 大阪 dedicated to 天照大神, rebuilt in 1947.",
    "It holds the rank of 県社 and stands near 阿倍野区.",
    "[[Category:Pages with 50+ untranslated japanese characters]] 神社",
])
def test_incidental_japanese_in_the_body_is_not_a_name(text):
    """The whole reason the extractor reads fields and not prose. A place name
    or a deity name lifted from the body resolves to a real Wikidata item —
    just not this page's."""
    assert japanese_names(text) == []


def test_names_are_ordered_and_deduplicated():
    text = "| native_name = 自然社 |\n{{lang|ja|自然社}} {{Nihongo|x|大祖教|y}}"
    assert japanese_names(text) == ["自然社", "大祖教"]


def test_a_single_character_name_is_not_taken():
    """`{2,}` — one kanji is too weak to key a sitelink lookup on."""
    assert japanese_names("| native_name = 社 |") == []
