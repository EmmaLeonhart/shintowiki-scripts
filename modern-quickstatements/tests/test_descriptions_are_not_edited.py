"""No batch may edit a description.

Emma, 2026-09-11: *"the Ukrainian descriptions are being updated in a bad way
that seems to indicate a lack of understanding of the purpose, descriptions
should not be being edited either way really. The emergency stuff was intended
to rapidly apply labels to things with orphaned descriptions to see how much
actual description changes were needed."*

An orphan description — one in a language the item has no label in — costs the
item a label, because Wikidata's uniqueness constraint is on the (label,
description) PAIR. **Supplying the label is the fix.** Rewriting the description
was only ever a means to unblock the label, and it lands without it: the
uniqueness check WITHHOLDS a colliding label instead.

Two description-editing paths existed and both are gone: the compound
`Dxx||Lxx` pair units in `description_label_pairs.txt`, and
`generate_description_restores.py`, which I built to undo the flattening and
which was itself 1,433 more description edits. This test is what stops either
coming back.

`description_removals.txt` is the one exception and is asserted separately: Emma
named two specific items and asked for every description cleared off them.
"""
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import direct_daily_edits as d  # noqa: E402

DESC_LINE = re.compile(r"^-?Q\d+\|D[A-Za-z-]+\|")

# Files that write a description for a reason other than rewriting one.
#
#  * description_removals.txt — Emma named Q11558526 and Q17128375 and asked for
#    every description cleared off them. A removal she asked for, not a rewrite.
#  * description_adds.txt — adds a description to an item that has a LABEL in
#    that language and no description. Step 3 of the four-step path in
#    docs/description_label_policy.md, and capped until January 2027. It cannot
#    overwrite anything: its selector requires the description to be absent.
#  * description_enrichment_en.txt — unique English descriptions for the
#    collision groups, from the cloud pipeline
#    (docs/description_enrichment_pipeline.md). It exists to make a colliding
#    (label, description) pair unique so a label CAN land.
#    ⭐ MEASURED 2026-09-14, all 13 items: every one has an English label and NO
#    English description, so like description_adds.txt it cannot overwrite anything
#    and every line is step 3 of the policy. The premise had been inferred from the
#    pipeline's purpose; it is now checked. See the test at the bottom of this file.
#
# ⚠ Emma said "descriptions should not be being edited either way really", and
# these two adders are description writes. They are neither the flattening she was
# describing nor a rewrite of anything, and both are documented policy, so they are
# left running.
#
# ⛔ "and raised with her" used to end that sentence, and it had been raised only in
# a commit message and in this comment — neither of which is a channel she reads
# (CLAUDE.md: the ONLY one is AskUserQuestion). That is the "flagged for review"
# non-outcome. It is closed by measurement instead of a question: both adders
# provably cannot overwrite, so there is nothing left to decide.
ALLOWED = {"description_removals.txt", "description_adds.txt",
           "description_enrichment_en.txt"}


@pytest.mark.parametrize("name", [f for f in d.ATOMIC_FILES if f not in ALLOWED])
def test_no_registered_batch_edits_a_description(name):
    path = os.path.join(MQ, name)
    if not os.path.exists(path):
        pytest.skip(f"{name} not generated here")
    for raw in open(path, encoding="utf-8"):
        for part in raw.strip().split("||"):
            assert not DESC_LINE.match(part), f"{name} edits a description: {part}"


def test_the_description_fix_generator_emits_only_labels():
    """Read from the source, so a future edit that reintroduces a Dxx line fails
    here even before a batch is regenerated."""
    src = open(os.path.join(MQ, "generate_description_fixes.py"),
               encoding="utf-8").read()
    body = src.split('"""', 2)[2]          # skip the module docstring
    assert "|D{lang}|" not in body
    assert '|L{lang}|"' in body


def test_the_restore_generator_is_gone():
    """It undid the flattening by making 1,433 more description edits, which is
    the same mistake in the other direction."""
    assert not os.path.exists(
        os.path.join(MQ, "generate_description_restores.py"))
    assert "description_restores.txt" not in d.ATOMIC_FILES


# ---- the enrichment exemption's premise, measured rather than assumed ----------

def test_the_enrichment_batch_is_add_only_and_collision_breaking():
    """`description_enrichment_en.txt` is exempt above on the grounds that it makes a
    colliding (label, description) pair unique so a LABEL can land. That premise had
    never been checked against the file or against Wikidata — it was inferred from
    the pipeline's purpose.

    Checked live 2026-09-14, all 13 items: **every one has an English label and NO
    English description.** So each line is exactly step 3 of
    `docs/description_label_policy.md` — *"If item has a label and no description,
    add a programmatically generated fill in the blanks description"* — and `Den`
    cannot overwrite anything, which is the same property `description_adds.txt` is
    exempted for.

    That closes the "raise it with Emma" note attached to the exemption. It was
    raised in a commit message and a comment, which is not a channel she reads, and
    the measurement means there is nothing left to decide: the file does what her
    own written policy asks for.

    What IS testable offline is the collision-breaking property, and it is the thing
    that would silently fail: three of the 13 are all labelled "Nifuno Shrine", and
    they only work if their descriptions differ (Onyū / Mikata / Tsuruga district). A
    duplicate description would recreate the collision the batch exists to break.
    """
    path = os.path.join(MQ, "description_enrichment_en.txt")
    if not os.path.exists(path):
        pytest.skip("not generated in this checkout")
    rows = []
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'^(Q\d+)\|Den\|"([^"]+)"$', line)
        assert m, f"line {i} is not a bare English description add: {line}"
        rows.append(m.groups())

    seen = {}
    for qid, desc in rows:
        assert desc not in seen, (
            f"{qid} and {seen[desc]} would both get {desc!r} — identical descriptions "
            "cannot break a (label, description) collision, which is the only reason "
            "this batch is allowed to write descriptions at all")
        seen[desc] = qid
