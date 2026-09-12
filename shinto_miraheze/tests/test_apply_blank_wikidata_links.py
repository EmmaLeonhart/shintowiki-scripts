"""`apply_blank_wikidata_links.fill` must never overwrite, and never rewrite.

Two failure modes are worth a test each, and both have precedent in this repo.

**Overwriting a QID.** The proposal is evidence gathered at resolve time, not a
licence to write at apply time. Between the two, `wikidata_lookup` or a human may
have filled the same template — with a different QID, possibly a better one. So
the apply step re-reads and fills only a template that is *still* blank.

**Rewriting the page.** `git_synced/` files carry `[[Category:Git synced pages]]`
as the sync's membership test; a wholesale rewrite that drops the trailing line
makes the sync push the page and then delete the local file (2026-08-23, `Open
questions`). This script replaces the template call in place, so every other byte
survives — including that category. The test below pins it on a page shaped like
the real ones.
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

import pytest

from shinto_miraheze.apply_blank_wikidata_links import fill  # noqa: E402

PAGE = """'''Shizensha''' (自然社) is a Japanese new religion.

== External links ==
* [https://www.sizensya.or.jp/ Official website]

{{wikidata link}}
[[Category:Japanese new religions]]
[[Category:Git synced pages]]
"""


def test_it_fills_a_blank_template():
    new, reason = fill(PAGE, "Q139921367")
    assert reason == "filled"
    assert "{{wikidata link|Q139921367}}" in new


def test_it_changes_nothing_else_on_the_page():
    """Byte-for-byte apart from the call itself — the trailing categories, and
    `[[Category:Git synced pages]]` above all, must survive."""
    new, _ = fill(PAGE, "Q139921367")
    assert new.replace("{{wikidata link|Q139921367}}", "{{wikidata link}}") == PAGE
    assert new.rstrip().endswith("[[Category:Git synced pages]]")


@pytest.mark.parametrize("existing", [
    "{{wikidata link|Q1}}",
    "{{wikidata link|Q99999}}",
    "{{wikidata link|ja|自然社}}",
])
def test_it_never_overwrites_an_existing_qid(existing):
    """Including — especially — a QID that disagrees with the proposal."""
    text = PAGE.replace("{{wikidata link}}", existing)
    new, reason = fill(text, "Q139921367")
    assert new is None
    assert "not overwriting" in reason or "no longer carries" in reason


def test_an_empty_first_parameter_still_counts_as_blank():
    text = PAGE.replace("{{wikidata link}}", "{{wikidata link|}}")
    new, reason = fill(text, "Q139921367")
    assert reason == "filled"
    assert "{{wikidata link|Q139921367}}" in new


def test_two_blank_templates_are_left_alone():
    """Which one the proposal was about is not recoverable here — that is the
    multiple_wikidata_links op's problem, not this script's guess."""
    text = PAGE.replace("{{wikidata link}}", "{{wikidata link}}\n{{wikidata link}}")
    new, reason = fill(text, "Q139921367")
    assert new is None
    assert "ambiguous" in reason


def test_a_page_without_the_template_is_refused():
    new, reason = fill("Just prose.\n[[Category:X]]\n", "Q139921367")
    assert new is None
    assert "no longer carries" in reason
