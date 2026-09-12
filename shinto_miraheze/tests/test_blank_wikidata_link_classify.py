"""The `da:` langlink is the filled/blank test — pin it before it looks arbitrary.

`report_blank_wikidata_links.py` sizes the blank-`{{wikidata link}}` population
without downloading 11,069 page bodies, by asking `allpages` for two cheap props
and reading the answer off a Danish interlanguage link. That looks like a trick
until you read `Template:Wikidata link`:

    {{#if:{{{1|}}}|{{tmbox …}}[[da:{{{1}}}]][[sh:{{FULLPAGENAME}}]]|…}}

`[[da:{{{1}}}]]` sits INSIDE the `#if` on parameter 1, so the rendered langlink
exists exactly when the template has a QID. The test that matters is therefore
the one below it: if someone moves that link out of the `#if`, or drops it, the
whole measurement silently reclassifies every blank page as filled, and the
number this script exists to produce becomes a quiet zero.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import os
import re

import pytest

from shinto_miraheze.report_blank_wikidata_links import classify  # noqa: E402


@pytest.mark.parametrize("has_template,has_langlink,expected", [
    (True, True, "filled"),
    (True, False, "blank"),
    (False, False, "missing"),
])
def test_the_three_verdicts(has_template, has_langlink, expected):
    assert classify(has_template, has_langlink) == expected


def test_no_template_is_missing_even_if_a_da_langlink_exists():
    """A page can carry a hand-written `[[da:…]]` without the template. It has no
    `{{wikidata link}}` to fill, so it belongs in `missing`, not `filled` —
    otherwise a hand-written interwiki hides a page from the very count the
    script produces."""
    assert classify(False, True) == "missing"


def test_the_template_still_gates_the_langlink_on_parameter_1():
    """Read off the committed copy of the template rather than the live wiki, so
    the test does not need the network and does not go red when the wiki is down.

    `miraheze_unique/Template%3AWikidata link.wiki` is the synced copy.
    """
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "miraheze_unique", "Template%3AWikidata link.wiki")
    if not os.path.exists(path):
        pytest.skip("template not present in the synced copy")
    text = open(path, encoding="utf-8").read()
    # The langlink must appear after an #if on {{{1}}} and before that #if's
    # else-branch separator — i.e. inside the has-a-QID branch.
    assert "[[da:{{{1}}}]]" in text, "the QID langlink is gone — the measurement is void"
    guard = re.search(r"\{\{#if:\{\{\{1\|\}\}\}\|", text)
    assert guard, "the #if on parameter 1 is gone — the langlink no longer means 'has a QID'"
    assert text.index("[[da:{{{1}}}]]") > guard.start()
