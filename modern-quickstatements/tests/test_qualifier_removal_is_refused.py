"""A '-' line with qualifier fields destroys the statement it looks like it edits.

QuickStatements cannot remove a qualifier — Help:QuickStatements lists *"remove a
qualifier without removing the statement itself"* under what it cannot do — and
`direct_daily_edits.execute_removal` parses the trailing qualifier fields and then
ignores them, matching on entity+property+value and calling wbremoveclaims on the claim.
So a line like

    -Q135040123|P1448|ojp-hani:"白城神社"|P1814|"シラキノ"

does not strip the katakana qualifier. It deletes the whole ojp-hani official name.

`kana_redundant_remove.txt` emitted 332 of those. Four executed after Emma lifted the
Wikidata lockout on 2026-09-06 — Q135040123, Q135070009, Q135194697 (09-07/08) and
Q135195565 (09-08) — and each item now has no P1448 at all, having also lost two
references, its P1264, and the カミノヤシロ qualifier `generate_kana_qualifier_add.py`
had just placed on it. All 332 carried references; 329 carried a P1264.

Two pins: the executor refuses the shape, and no registered atomic file emits it.
"""
import glob
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QS_DIR = os.path.dirname(HERE)
if QS_DIR not in sys.path:
    sys.path.insert(0, QS_DIR)

import direct_daily_edits as dde


def _lines(path):
    for n, line in enumerate(io.open(path, encoding="utf-8"), 1):
        line = line.strip()
        if line and not line.startswith("#"):
            yield n, line


def test_execute_removal_refuses_a_line_with_qualifier_fields():
    """No session/token needed — the refusal must come before any API call."""
    parsed = dde.parse_qs_line(
        '-Q135040123|P1448|ojp-hani:"白城神社"|P1814|"シラキノ"')
    assert parsed["is_removal"]
    assert parsed["qualifiers"], "the fixture stopped carrying qualifier fields"
    ok, msg = dde.execute_removal(None, None, parsed)
    assert not ok
    assert "Refused" in msg


def test_a_plain_removal_is_still_attempted():
    """The guard must not swallow the legitimate whole-statement removals."""
    parsed = dde.parse_qs_line('-Q135041341|P1814|"ヒハメノ-"')
    assert parsed["is_removal"] and not parsed["qualifiers"]
    # Reaching find_claim with a None session is how we know it was not refused.
    try:
        dde.execute_removal(None, None, parsed)
    except AttributeError:
        pass
    else:
        raise AssertionError("expected the call to reach find_claim(None, ...)")


def test_no_registered_atomic_file_emits_a_qualifier_removal():
    offenders = []
    for name in dde.ATOMIC_FILES:
        path = os.path.join(QS_DIR, name)
        if not os.path.exists(path):
            continue
        for n, line in _lines(path):
            if line.startswith("-") and len(line.split("|")) > 3:
                offenders.append("%s:%d %s" % (name, n, line))
    assert not offenders, (
        "these lines read as qualifier removals and would delete the whole statement: %r"
        % offenders[:5])


def test_the_kana_generator_no_longer_emits_the_sibling_shape():
    src = io.open(os.path.join(QS_DIR, "generate_kana_qualifier_remove.py"),
                  encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "P1448|{ml(on)}|P1814" not in code, "sibling-qualifier removal reintroduced"
