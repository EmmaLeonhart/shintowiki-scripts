"""The three lost-shrine creations, and the gate that holds them.

`lost_shrine_creates.txt` replaces the shrines whose items the ブルーノ・プラス repurposing
took over — the item now describes a different subject, so the shrine has no item anywhere.
Emma, 2026-08-24: *"Register it — deliver on 2026-09-18."*

What is worth pinning here is narrower than "the file parses":

  * **the citations survive.** 近殿神社's reading is ちかどのじんしゃ, the じんしゃ-for-じんじゃ
    misspelling. Emma's rule is that a cited one is preserved and an uncited one is corrected,
    and this one is cited to the National Tax Agency registry, so it is the legally registered
    フリガナ. Emitting the statement without its reference would put a bare ちかどのじんしゃ on
    a brand-new item and the next pipeline pass would "correct" the legally registered reading.
    The citation is what marks the value deliberate, so it has to travel with it.
  * **only the three repurposed items are in scope.** `destroyed_items/` holds 24 archives and
    21 of them were damaged as themselves, so they still describe their own subject and a new
    item would be a plain duplicate.
  * **the batch never reaches ATOMIC_FILES.** A CREATE block is strictly ordered and
    `direct_daily_edits.py` samples lines at random, so a `LAST|…` line drawn without its
    `CREATE` is meaningless.
"""
import io
import os
import sys
import datetime

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
if MQ not in sys.path:
    sys.path.insert(0, MQ)

import create_items  # noqa: E402
import lost_shrine_gate  # noqa: E402
import direct_daily_edits as dde  # noqa: E402

BATCH = "lost_shrine_creates.txt"
BATCH_PATH = os.path.join(MQ, BATCH)

# The repurposed three. Named here so a widening of the batch has to change a test.
LOST = {"Q123044569", "Q134736575", "Q134886554"}


@pytest.fixture(scope="module")
def blocks():
    return create_items.load_blocks(BATCH_PATH)


def test_batch_is_registered_with_a_gate():
    assert create_items.GATES.get(BATCH) == "lost_shrine_gate"


def test_there_are_exactly_three_blocks(blocks):
    assert len(blocks) == 3


def test_every_block_has_an_english_label_and_a_p31(blocks):
    for b in blocks:
        assert any(ln.startswith('LAST|Len|"') for ln in b), b
        assert any(ln.startswith("LAST|P31|Q") for ln in b), b


def test_every_statement_line_parses(blocks):
    for b in blocks:
        for ln in b:
            assert dde.parse_qs_line(ln.replace("LAST", "Q1", 1)) is not None, ln


def test_the_nta_citation_travels_with_the_jinsha_reading(blocks):
    """The reading is preserved BECAUSE it is cited; a bare copy invites a 'fix'."""
    kana = [ln for b in blocks for ln in b if ln.startswith("LAST|P1814|")]
    assert kana, "no kana lines at all"
    misspelt = [ln for ln in kana if "じんしゃ" in ln]
    assert misspelt, "近殿神社's ちかどのじんしゃ is missing from the batch"
    for ln in misspelt:
        assert "|S854|" in ln, ln
        assert "houjin-bangou.nta.go.jp" in ln, ln


def test_references_parse_as_references_not_qualifiers(blocks):
    for b in blocks:
        for ln in b:
            if "|S854|" not in ln:
                continue
            parsed = dde.parse_qs_line(ln.replace("LAST", "Q1", 1))
            assert parsed["references"], ln
            assert not any(p.startswith("S") for p, _ in parsed["qualifiers"]), ln


def test_no_contradicting_description_is_reimported(blocks):
    """見光寺's archived ja description placed it in Yokohama; its own P131 says Hannō."""
    for b in blocks:
        if not any('LAST|Lja|"見光寺"' == ln for ln in b):
            continue
        assert not any(ln.startswith("LAST|Dja|") for ln in b), \
            "the contradicting ja description came back"
        return
    pytest.fail("見光寺 block not found")


def test_only_the_repurposed_three_are_generated():
    """21 of the 24 archives were damaged as themselves — new items would duplicate."""
    src = io.open(os.path.join(MQ, "generate_lost_shrine_creates.py"),
                  encoding="utf-8").read()
    ns = {}
    for line in src.splitlines():
        if line.startswith("LOST = "):
            exec(line, ns)
            break
    assert set(ns["LOST"]) == LOST


def test_batch_is_not_in_atomic_files():
    """A CREATE block is ordered; the drip samples lines at random."""
    import submit_daily_batch as sdb
    assert BATCH not in dde.ATOMIC_FILES
    assert BATCH not in sdb.ATOMIC_FILES


def test_gate_is_shut_while_the_lockout_holds(monkeypatch):
    monkeypatch.setattr(lost_shrine_gate, "editing_allowed",
                        lambda: (False, "LOCKED until 2026-09-18"))
    ok, why = lost_shrine_gate.is_open(today=datetime.date(2026, 9, 1),
                                       last_watched_edit=None)
    assert not ok
    assert "lockout" in why


def test_gate_opens_once_the_lockout_lifts_and_conflict_gate_is_clear(monkeypatch):
    monkeypatch.setattr(lost_shrine_gate, "editing_allowed",
                        lambda: (True, "no lockout"))
    ok, _ = lost_shrine_gate.is_open(today=datetime.date(2026, 9, 30),
                                     last_watched_edit=datetime.date(2020, 1, 1))
    assert ok


def test_gate_fails_closed_when_the_conflict_check_raises(monkeypatch):
    def boom():
        raise RuntimeError("network down")
    monkeypatch.setattr(lost_shrine_gate, "editing_allowed",
                        lambda: (True, "no lockout"))
    monkeypatch.setattr(lost_shrine_gate.conflict_gate,
                        "fetch_last_watched_edit", boom)
    ok, why = lost_shrine_gate.is_open(today=datetime.date(2026, 9, 30))
    assert not ok
    assert "refusing" in why


def test_gate_fails_closed_when_the_lockout_check_raises(monkeypatch):
    def boom():
        raise RuntimeError("state file unreadable")
    monkeypatch.setattr(lost_shrine_gate, "editing_allowed", boom)
    ok, why = lost_shrine_gate.is_open(today=datetime.date(2026, 9, 30),
                                       last_watched_edit=None)
    assert not ok
    assert "refusing" in why


def test_gate_is_shut_right_now():
    """Belt and braces: whatever the date is when this runs, the real gate agrees."""
    ok, why = lost_shrine_gate.is_open()
    if datetime.date.today() < datetime.date(2026, 9, 18):
        assert not ok, why
