"""The wrong-link removal must be precise and idempotent.

It edits four pages that carry a QID which is not their subject. Emma approved
removal specifically (2026-08-27) after the alternative — repointing — was ruled
out by searching Wikidata and finding no suitable item for any of them.

Two properties matter more than the removal itself:

* it must strip ONLY the ``{{wikidata link}}`` call, since these pages are
  otherwise correct and are not the defect;
* it must refuse to act when the link no longer carries the expected wrong QID, so
  a re-run cannot undo someone's later repoint.
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

from shinto_miraheze.remove_wrong_wikidata_links import (  # noqa: E402
    TARGETS, strip_link,
)

REAL_CALL = ("{{wikidata link|Q22070227|en|Himegami|fr|Himégami|ja|比売神|zh|比賣神"
             "|grok=none|check_date=2026-05-29}}")


def test_the_four_targets_are_the_ones_that_were_investigated():
    assert TARGETS == {
        "Template:Ichinomiya": "Q1656379",
        "Template:Sōja shrines": "Q1107129",
        "Benzaiten shrines": "Q818468",
        "Hime Shrine": "Q22070227",
    }


def test_only_the_link_is_removed():
    text = f"Shrines dedicated to Himegami.\n\n{REAL_CALL}\n[[Category:Something]]\n"
    new, qid = strip_link(text, "Q22070227")
    assert qid == "Q22070227"
    assert "wikidata link" not in new
    assert "Shrines dedicated to Himegami." in new
    assert "[[Category:Something]]" in new


def test_a_different_qid_is_left_alone():
    """Someone repointed it since; a re-run must not undo that."""
    text = f"body\n{REAL_CALL}\n"
    new, qid = strip_link(text, "Q818468")     # expecting a different wrong QID
    assert new is None
    assert qid == "Q22070227"


def test_a_page_with_no_link_is_left_alone():
    new, qid = strip_link("body with no template at all\n", "Q818468")
    assert new is None and qid is None


def test_running_twice_changes_nothing_the_second_time():
    text = f"body\n{REAL_CALL}\n"
    once, _ = strip_link(text, "Q22070227")
    twice, qid = strip_link(once, "Q22070227")
    assert twice is None and qid is None


def test_case_and_spacing_variants_of_the_template_name_are_matched():
    for call in ("{{Wikidata Link|Q818468|en|Benzaiten}}",
                 "{{ wikidata link |Q818468|en|Benzaiten}}"):
        new, qid = strip_link(f"body\n{call}\n", "Q818468")
        assert new is not None, call
        assert qid == "Q818468"
        assert "Q818468" not in new


def test_other_templates_on_the_page_survive():
    text = ("{{Infobox religious building|name=X}}\n"
            f"{REAL_CALL}\n"
            "{{Reflist}}\n")
    new, _ = strip_link(text, "Q22070227")
    assert "{{Infobox religious building|name=X}}" in new
    assert "{{Reflist}}" in new
