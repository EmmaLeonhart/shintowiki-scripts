"""The ブルーノ・プラス-repurposed husks must never receive an edit.

queue.md A5, Emma: "document, don't touch; no contact until we understand the
editor." Detail in docs/bruno_plus_analysis_2026-07.md — these are items whose
entire contents were replaced with a different shrine, so editing one both
touches an item we were told to leave alone and implicitly endorses the
repurposing.

Found 2026-08-04: TEN staged lines across five atomic files targeted husks,
including `Q123044569|Len|"Ōmiwa Shrine"` — which would have put an English
label on the repurposed identity. Nothing had gone out only because the Wikidata
freeze was still on.

They arrive honestly. The husk now IS the 大美和神社 / 近殿神社 item on Wikidata,
so any generator that resolves a jawiki article to a QID by sitelink lands on it.
That is why the guard belongs at the submitter — the single road to Wikidata —
rather than in each generator, where the next generator written would miss it.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
# The submitter imports sibling modules (conflict_gate, sutra_gate) by bare name,
# so the package dir has to be importable — same shape as the drift-guard test.
sys.path.insert(0, MQ)

import direct_daily_edits as dde  # noqa: E402

SUBJECT = re.compile(r"^-?(Q\d+)\|")


def test_the_husk_set_is_the_documented_one():
    assert dde.REPURPOSED == {
        "Q123044569", "Q134886554", "Q134736575", "Q140476265"}


@pytest.mark.parametrize("qid", sorted(dde.REPURPOSED))
def test_submitter_refuses_every_husk(qid):
    """Refused without a network call: the gate must not depend on a revision
    lookup that could fail open, and must not spend a request to learn nothing."""
    editable, reason = dde.item_is_editable(qid)
    assert editable is False
    assert "repurposed" in reason.lower() or "husk" in reason.lower()


def test_a_normal_qid_is_not_refused_by_this_gate(monkeypatch):
    """Guard against the gate being written so broadly it blocks everything —
    a refusal that refuses all edits would look like a working guard."""
    monkeypatch.setattr(dde.conflict_gate, "fetch_item_revisions", lambda q: [])
    monkeypatch.setattr(dde.conflict_gate, "is_item_fresh_enough", lambda r, t: True)
    editable, reason = dde.item_is_editable("Q42")
    assert editable is True and reason is None


def test_no_atomic_file_stages_an_edit_to_a_husk():
    """The staged files themselves must be clean, so a husk edit cannot be
    delivered by any path that bypasses the submitter's gate."""
    offenders = []
    for name in sorted(os.listdir(MQ)):
        if not name.endswith(".txt"):
            continue
        for n, line in enumerate(open(os.path.join(MQ, name), encoding="utf-8"), 1):
            m = SUBJECT.match(line.strip())
            if m and m.group(1) in dde.REPURPOSED:
                offenders.append(f"{name}:{n} {line.strip()[:80]}")
    assert not offenders, (
        "staged QuickStatements target repurposed husks:\n  " + "\n  ".join(offenders))


def test_every_workflow_that_writes_atomic_files_strips_husks():
    """The chokepoint has to be on EVERY road, or it is not a chokepoint.

    `strip_husk_lines.py` was wired into `generate-quickstatements.yml` as its last
    step before the commit. `generate-shrines-missing-en-label.yml` also writes atomic
    .txt files (identical_name_en_labels.txt, kana_en_labels.txt, the temple pair) and
    had no such step, so the two workflows disagreed: 96efe817 re-added
    `Q134886554|Len|"Chikadono Shrine"` on 2026-09-07 and the test above stayed red on
    main until the other workflow stripped it on 2026-09-10.

    A future workflow that generates into this directory and commits will hit this.
    """
    wf_dir = os.path.join(os.path.dirname(MQ), ".github", "workflows")
    missing = []
    for name in sorted(os.listdir(wf_dir)):
        if not name.endswith((".yml", ".yaml")):
            continue
        text = open(os.path.join(wf_dir, name), encoding="utf-8").read()
        # Does it RUN a generator that writes an atomic .txt, and commit afterwards?
        writes = any(f"python {g}" in text for g in ATOMIC_GENERATORS)
        if writes and "strip_husk_lines.py" not in text:
            missing.append(name)
    assert not missing, (
        "these workflows generate atomic QuickStatements files but never strip husk "
        "lines: " + ", ".join(missing))


# Generators known to write into modern-quickstatements/*.txt. Named rather than
# discovered so adding one is a deliberate act, and the test above then requires
# whatever workflow runs it to carry the strip step.
ATOMIC_GENERATORS = [
    "generate_identical_name_en_labels.py",
    "generate_kana_en_labels.py",
    "generate_temple_en_labels.py",
    "generate_temple_identical_name_en_labels.py",
    "generate_cjk_ja_backfill.py",
]
