"""Step 1 of Emma's description algorithm: clear descriptions on label-less items.

Her ruling, 2026-08-21, and the caveat she called extremely important:

    "we always remove descriptions from items without a label in that language"

    "many items can have the same label and empty descriptions, and many items can have the
     same description and an empty label, but once the two of them are both filled then it
     rejects edits to one to avoid duplication. Since labels are overwhelmingly more
     important than descriptions, it follows that any description on an item without a label
     is actively harmful."

Wikidata's uniqueness constraint is on the (label, description) PAIR; either field alone may
repeat freely. A description on a label-less item therefore stakes the half that matters
least, and when the label arrives the completed pair can collide -- and the LABEL edit is
what gets rejected. A description with no label costs a label.

Measured the same day: 10,250 orphan descriptions across 100 languages, of which id (5,024)
and uk (4,591) are 94%. Emma authorised those two. 5,020 of the id ones are items that also
have a staged `Lid` label edit, which is 22.8% of the pending Indonesian labels -- so this is
not a hypothetical collision risk.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import audit_orphan_descriptions as aod  # noqa: E402

STAGED = os.path.join(HERE, "orphan_description_removals.txt")
LINE_RE = re.compile(r'^Q\d+\|D[a-z]{2,3}(?:-[a-z]+)?\|""$')


def _lines():
    if not os.path.exists(STAGED):
        return []
    return [l.strip() for l in io.open(STAGED, encoding="utf-8") if l.strip()]


# ───────────────────────── the emitted form ─────────────────────────

def test_removal_line_is_an_empty_value_set_not_a_dash_removal():
    """`-Qxxx|Den|"text"` is a VALUE-MATCHED removal and needs the exact current text;
    direct_daily_edits.execute_line refuses term removals outright. An empty-value set is
    unconditional and is what wbsetdescription treats as a clear."""
    line = aod.removal_line("Q167146", "id")
    assert line == 'Q167146|Did|""'
    assert not line.startswith("-")


def test_emitted_lines_parse_to_an_empty_description_value():
    """The whole mechanism rests on this: the parser must yield term_value == '' so the
    API call becomes wbsetdescription(value='') rather than setting the literal text '""'."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_dde", os.path.join(HERE, "direct_daily_edits.py"))
    dde = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(dde)
    except SystemExit:
        pass
    parsed = dde.parse_qs_line(aod.removal_line("Q167146", "id"))
    assert parsed["term_kind"] == "D"
    assert parsed["term_lang"] == "id"
    assert parsed["term_value"] == ""
    assert parsed["is_removal"] is False, "must not take the unsupported dash-removal path"


# ───────────────────────── the staged file ─────────────────────────

def test_staged_file_is_well_formed():
    lines = _lines()
    if not lines:
        return                                  # nothing staged yet is a valid state
    bad = [l for l in lines if not LINE_RE.match(l)]
    assert not bad, "malformed removal lines: %s" % bad[:5]


def test_only_the_languages_emma_authorised():
    """She named Indonesian and Ukrainian. The other 98 languages in the audit -- 635 items
    -- are NOT authorised, and staging them would be widening her instruction."""
    langs = {l.split("|")[1][1:] for l in _lines()}
    assert langs <= {"id", "uk"}, "unauthorised languages staged: %s" % (langs - {"id", "uk"})


def test_no_duplicate_lines():
    """A re-run merges rather than appends; a duplicate would mean that broke."""
    lines = _lines()
    assert len(lines) == len(set(lines))


def test_file_is_sorted_so_regeneration_does_not_churn():
    """Same lesson as the 2026-08-21 tok.txt/id_proposed.txt churn: a generated file that
    reorders on every run makes its own diff unreadable, which is how a dead pipeline went
    unnoticed for two days."""
    lines = _lines()

    def key(line):
        qid, rest = line.split("|", 1)
        return (rest, int(qid[1:]) if qid[1:].isdigit() else 0, qid)

    assert lines == sorted(lines, key=key)


def test_registered_as_an_atomic_file():
    """An unregistered file is staged work that never reaches Wikidata -- the exact silent
    orphaning the ATOMIC_FILES superset comment already warns about."""
    src = io.open(os.path.join(HERE, "direct_daily_edits.py"), encoding="utf-8").read()
    assert '"orphan_description_removals.txt"' in src
