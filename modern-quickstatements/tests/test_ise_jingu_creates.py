"""The 21 神宮125社 item creations: the batch and its gate.

Item creation is the most conspicuous write this repo makes, so what is asserted
here is mostly what must NOT happen: no unparseable line, no duplicate label
(which would defeat the idempotency state, keyed on the label), no description
(Emma's standing note — unrequested descriptions once broke her deduplication),
and a gate that stays shut through the Wikidata freeze and fails closed.
"""
import datetime
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
QS = os.path.dirname(HERE)
# The modules import their siblings (conflict_gate, direct_daily_edits) by bare
# name, so the package dir has to be importable — same shape as the husk test.
if QS not in sys.path:
    sys.path.insert(0, QS)

# Each of these rebinds sys.stdout to a fresh TextIOWrapper at module scope (the
# script-template invariant). Under pytest's capture that means several wrappers
# over one temp file, and the first one collected closes it out from under the
# rest — "ValueError: I/O operation on closed file" at teardown. Holding a
# reference to every wrapper keeps them all alive for the session.
_KEEP_STDOUT_ALIVE = [sys.stdout]

import create_items  # noqa: E402
_KEEP_STDOUT_ALIVE.append(sys.stdout)
import ise_jingu_gate  # noqa: E402
_KEEP_STDOUT_ALIVE.append(sys.stdout)
import direct_daily_edits as dde  # noqa: E402
_KEEP_STDOUT_ALIVE.append(sys.stdout)

BATCH = "ise_jingu_creates.txt"
BATCH_PATH = os.path.join(QS, BATCH)


@pytest.fixture(scope="module")
def blocks():
    return create_items.load_blocks(BATCH_PATH)


def test_batch_is_registered_with_a_gate():
    # create_items refuses any batch with no gate; this asserts the wiring, so a
    # rename of the gate module cannot silently make the batch unrunnable.
    assert create_items.GATES.get(BATCH) == "ise_jingu_gate"


def test_every_block_has_a_label_and_a_p31(blocks):
    assert blocks, "batch is empty"
    for block in blocks:
        assert create_items.block_label(block), block
        assert create_items.block_p31(block) == "Q845945", block


def test_labels_are_unique(blocks):
    # <batch>.state is keyed on the English label. Two blocks sharing one label
    # means the second is skipped as "already created" and silently never made.
    labels = [create_items.block_label(b) for b in blocks]
    assert len(labels) == len(set(labels))


def test_every_statement_line_parses(blocks):
    for block in blocks:
        for line in block:
            if line.startswith("LAST|Len|"):
                continue          # applied by wbeditentity, not parse_qs_line
            assert dde.parse_qs_line(line.replace("LAST", "Q1", 1)), line


def test_no_descriptions_are_set(blocks):
    # Emma, [[Open questions]]: a past run "randomly decided to add descriptions
    # when I never asked … that broke the deduplication process".
    for block in blocks:
        for line in block:
            assert not re.match(r"^LAST\|D[a-z-]+\|", line), line


def test_every_block_is_linked_to_the_jingu(blocks):
    # P361 = 伊勢神宮 is "the connection" Emma asked for, and all 99 of these
    # shrines that already have an item carry it.
    for block in blocks:
        assert "LAST|P361|Q687168" in block, create_items.block_label(block)


def test_p612_always_carries_the_bunrei_qualifier(blocks):
    # docs/wikidata_shrine_festival_model.md: a bare P612 is never correct.
    for block in blocks:
        for line in block:
            if "|P612|" in line:
                assert "|P1013|Q195793|" in line, line


def test_gate_is_shut_during_the_wikidata_freeze():
    ok, why = ise_jingu_gate.is_open(today=datetime.date(2026, 8, 9),
                                     last_watched_edit=None)
    assert not ok
    assert "freeze" in why


def test_gate_opens_after_the_freeze_when_conflict_gate_is_clear():
    long_ago = datetime.date(2020, 1, 1)
    ok, _ = ise_jingu_gate.is_open(today=datetime.date(2026, 9, 1),
                                   last_watched_edit=long_ago)
    assert ok


def test_gate_fails_closed_when_the_conflict_check_raises(monkeypatch):
    def boom():
        raise RuntimeError("network down")
    monkeypatch.setattr(ise_jingu_gate.conflict_gate,
                        "fetch_last_watched_edit", boom)
    ok, why = ise_jingu_gate.is_open(today=datetime.date(2026, 9, 1))
    assert not ok
    assert "refusing" in why


def test_gate_is_not_wired_backwards():
    # The freeze branch must reject dates BEFORE the cutoff, not after it — the
    # same inversion that would have made the bunrei sunset a no-op.
    before, _ = ise_jingu_gate.is_open(today=ise_jingu_gate.FREEZE_UNTIL
                                       - datetime.timedelta(days=1),
                                       last_watched_edit=None)
    assert not before
