"""A carry is an INSERTION. The test suite's job is to keep it one.

``carry_missing_sections.py`` exists because the other two duplicate-pair scripts are
all-or-nothing about the body — one replaces the target's, one leaves it alone — and
seven pairs are complementary rather than superset/subset. The risk it introduces is
the mirror of ``merge_duplicate_pairs.py``'s: that an "insertion" quietly drops or
duplicates something on the target. So the properties under test are the ones that
make the edit reviewable without re-reading the page:

* nothing that was on the target before is missing afterwards,
* a section already covered on the target is refused, not appended twice,
* a re-run after a successful carry is a no-op (idempotence), and
* a section whose named citation would be left behind is refused rather than carried
  into a cite error.

The last one is a real hazard on this corpus: these pages are jawiki imports full of
``<ref name=":0" />`` back-references, and the definition sits wherever the first use
was — frequently in a section that is NOT the one being carried.
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

from shinto_miraheze.carry_missing_sections import (  # noqa: E402
    CARRIES, carry_sections,
)

SOURCE = (
    "'''Lead''' of the source.\n\n"
    "== Overview ==\nThe overview only the source has.\n\n"
    "=== A subsection ===\nCarried with its parent.\n\n"
    "== Genealogy ==\n*thin list\n\n"
    "== See also ==\n*An annotated pointer — with a real sentence after it.\n\n"
    "== References ==\n<references/>\n"
)

TARGET = (
    "The target's lead.\n\n"
    "==Genealogy==\nThe fuller genealogy table.\n\n"
    "==Notelist==\n{{notelist}}\n"
    "==References==\n{{reflist}}\n"
    "[[Category:Kuni no miyatsuko]]\n"
)

PLAN = [("Overview", "Genealogy"), ("See also", "Notelist")]


def test_it_inserts_and_removes_nothing():
    out, notes = carry_sections(SOURCE, TARGET, PLAN)
    assert out is not None, notes
    assert "The target's lead." in out
    assert "The fuller genealogy table." in out
    assert "{{notelist}}" in out and "{{reflist}}" in out
    assert "[[Category:Kuni no miyatsuko]]" in out
    assert "The overview only the source has." in out
    assert "An annotated pointer" in out
    assert len(out) > len(TARGET)


def test_a_carried_section_brings_its_subsections():
    out, _ = carry_sections(SOURCE, TARGET, [("Overview", "Genealogy")])
    assert "=== A subsection ===" in out
    assert "Carried with its parent." in out


def test_sections_land_at_the_named_anchor():
    out, _ = carry_sections(SOURCE, TARGET, PLAN)
    assert out.index("== Overview ==") < out.index("==Genealogy==")
    assert out.index("==Genealogy==") < out.index("== See also ==")
    assert out.index("== See also ==") < out.index("==Notelist==")


def test_two_sections_sharing_an_anchor_keep_their_declared_order():
    """Inserting them one at a time at the same offset silently reverses them.

    The second insertion lands in front of the first, so the page comes out with the
    sections in the opposite order to the one written in CARRIES — a wrong edit that
    saves cleanly and reports success. 尾張氏 was the first pair to need two sections at
    one anchor, and the reversal was found in a dry-run before it shipped.
    """
    source = ("Lead.\n\n"
              "== First ==\nsection one.\n\n"
              "== Second ==\nsection two.\n\n"
              "== Genealogy ==\n*thin\n")
    out, notes = carry_sections(source, TARGET, [("First", "Genealogy"),
                                                 ("Second", "Genealogy")])
    assert out is not None, notes
    assert out.index("== First ==") < out.index("== Second ==")
    assert out.index("== Second ==") < out.index("==Genealogy==")
    assert "The fuller genealogy table." in out


def test_it_refuses_a_section_the_target_already_has():
    """The target's Genealogy is the fuller one; appending the source's duplicates it."""
    out, reason = carry_sections(SOURCE, TARGET, [("Genealogy", "Notelist")])
    assert out is None
    assert "already" in reason


def test_a_rerun_after_a_successful_carry_is_refused():
    """Idempotence — the property that makes re-dispatching a run safe."""
    once, _ = carry_sections(SOURCE, TARGET, PLAN)
    twice, reason = carry_sections(SOURCE, once, PLAN)
    assert twice is None
    assert "already" in reason


def test_an_entry_extended_after_a_partial_carry_does_only_the_new_part():
    """A part already on the target is SKIPPED so the rest can still run.

    尾張氏 needed this: its two sections landed, then its lead was added to the same
    entry, and refusing the whole entry on the already-present sections would have made
    the extended entry permanently unrunnable. The no-duplication property is what the
    guard is for, and skipping preserves it — the test above still shows a plain re-run
    being refused.
    """
    once, _ = carry_sections(SOURCE, TARGET, PLAN)
    assert once.count("== Overview ==") == 1
    twice, notes = carry_sections(
        SOURCE, once, PLAN,
        lead={"heading": "Lineage", "anchor": "Genealogy"})
    assert twice is not None, notes
    assert twice.count("== Overview ==") == 1      # not carried a second time
    assert twice.count("== See also ==") == 1
    assert "== Lineage ==" in twice                # the new part did run
    assert any("skipped" in n for n in notes)


def test_it_refuses_when_a_named_ref_would_be_left_behind():
    source = (
        "Lead with the definition.<ref name=\":0\">{{Cite web|title=x}}</ref>\n\n"
        "== Overview ==\nBody that only back-references it.<ref name=\":0\" />\n"
    )
    out, reason = carry_sections(source, TARGET, [("Overview", "Genealogy")])
    assert out is None
    assert "citation" in reason


def test_a_ref_already_defined_on_the_target_is_fine():
    source = "Lead.\n\n== Overview ==\nBody.<ref name=\":0\" />\n"
    target = TARGET.replace("The target's lead.",
                            "The target's lead.<ref name=\":0\">{{Cite web|title=x}}</ref>")
    out, notes = carry_sections(source, target, [("Overview", "Genealogy")])
    assert out is not None, notes


def test_it_refuses_a_redirect_on_either_side():
    assert carry_sections("#REDIRECT [[X]]\n", TARGET, PLAN)[0] is None
    assert carry_sections(SOURCE, "#REDIRECT [[X]]\n", PLAN)[0] is None


def test_it_refuses_rather_than_guessing_at_a_missing_heading():
    out, reason = carry_sections(SOURCE, TARGET, [("Territory", "Genealogy")])
    assert out is None and "no heading" in reason
    out, reason = carry_sections(SOURCE, TARGET, [("Overview", "Nonexistent")])
    assert out is None and "no heading" in reason


def test_it_refuses_an_empty_source_section():
    source = "Lead.\n\n== Overview ==\n\n== Genealogy ==\n*thin list\n"
    out, reason = carry_sections(source, TARGET, [("Overview", "Genealogy")])
    assert out is None and "empty" in reason


def test_an_empty_wrapper_over_a_real_subsection_is_still_carried():
    """Emptiness is judged on the SECTION, which includes its subsections.

    ``== Base ==`` over ``=== Territory ===`` is the shape the redirect script's
    empty-heading exemption was written for — a wrapper, not a stub. It carries the
    subsection's content, so refusing it here would strand real text on the source.
    """
    source = SOURCE.replace("The overview only the source has.\n", "")
    out, notes = carry_sections(source, TARGET, [("Overview", "Genealogy")])
    assert out is not None, notes
    assert "Carried with its parent." in out


LEAD_SOURCE = (
    "{{Infobox clan\n|founder = [[Someone]]\n|people = [[A]]<br/>[[B]]\n}}\n\n"
    "The '''clan''' traces its progenitor to Someone.\n\n"
    "== Genealogy ==\n*thin list\n"
)


def test_the_lead_can_be_carried_as_its_own_section():
    """The gate compares headings and never sees a lead, so one has to be carried.

    尾張氏's lead was 2,125b against the target's 1,246b and held the clan's progenitor
    and its descendant houses. The redirect would have passed the pair anyway.
    """
    out, notes = carry_sections(
        LEAD_SOURCE, TARGET, [],
        lead={"heading": "Lineage", "anchor": "Genealogy", "append": "Also: X and Y."})
    assert out is not None, notes
    assert "== Lineage ==" in out
    assert "traces its progenitor to Someone" in out
    assert "Also: X and Y." in out
    assert out.index("== Lineage ==") < out.index("==Genealogy==")


def test_the_leads_infobox_is_dropped_not_carried():
    """A second clan infobox mid-article is not what "carry the lead" means."""
    out, _ = carry_sections(LEAD_SOURCE, TARGET, [],
                            lead={"heading": "Lineage", "anchor": "Genealogy"})
    assert "{{Infobox clan" not in out
    assert "|founder" not in out
    assert "traces its progenitor" in out


def test_a_templates_only_lead_is_refused():
    source = "{{Infobox clan\n|founder = [[Someone]]\n}}\n\n== Genealogy ==\n*thin\n"
    out, reason = carry_sections(source, TARGET, [],
                                 lead={"heading": "Lineage", "anchor": "Genealogy"})
    assert out is None and "nothing to carry" in reason


def test_nested_templates_in_the_lead_do_not_swallow_the_prose():
    """Braces are matched by depth — a regex stops at the first ``}}``."""
    source = ("{{Infobox|a={{nested|x}}|b=y}}\n\n"
              "Real prose survives.\n\n== Genealogy ==\n*thin\n")
    out, notes = carry_sections(source, TARGET, [],
                                lead={"heading": "Lineage", "anchor": "Genealogy"})
    assert out is not None, notes
    assert "Real prose survives." in out
    assert "{{Infobox" not in out and "{{nested" not in out


def test_carrying_the_lead_twice_is_refused():
    once, _ = carry_sections(LEAD_SOURCE, TARGET, [],
                             lead={"heading": "Lineage", "anchor": "Genealogy"})
    twice, reason = carry_sections(LEAD_SOURCE, once, [],
                                   lead={"heading": "Lineage", "anchor": "Genealogy"})
    assert twice is None and "already" in reason


def test_every_carries_entry_is_well_formed():
    """The list is hand-written per pair, so the shape is worth asserting."""
    for entry in CARRIES:
        assert entry["source"] and entry["target"]
        assert entry["source"] != entry["target"]
        assert entry["sections"], "an entry with no sections carries nothing"
        for pair in entry["sections"]:
            assert len(pair) == 2 and all(isinstance(x, str) and x for x in pair)
