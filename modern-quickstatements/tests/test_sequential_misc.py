"""The sequential-misc file mechanism in the only editor that reaches Wikidata.

Emma 2026-07-10 (Open questions): a single file run ONE line per day, top-to-bottom,
never interleaved, so remove-then-add / add-then-remove pairs are safe under the
otherwise-random drip. These tests pin the pure logic: which line runs today, when
the cursor advances vs holds, and that an empty/absent file changes nothing.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import direct_daily_edits as dde  # noqa: E402


# ─────────────────────── line loading ───────────────────────

def test_absent_file_is_empty(tmp_path):
    assert dde.load_sequential_lines(str(tmp_path / "nope.txt")) == []


def test_comments_and_blanks_are_filtered(tmp_path):
    p = tmp_path / "seq.txt"
    p.write_text("# header\n\nQ1|P2|Q3\n  \n# mid comment\nQ4|P5|Q6\n",
                 encoding="utf-8")
    assert dde.load_sequential_lines(str(p)) == ["Q1|P2|Q3", "Q4|P5|Q6"]


def test_the_shipped_file_holds_exactly_the_intended_lines():
    """The file shipped empty until 2026-07-17, when Emma's inbound-links fix was
    MOVED here from the atomic drip (commit 50b42c1a7): at ~105k pool lines a 2-line
    file had a ~0.28%/day draw chance — about a year's expected wait — while this
    channel lands one line/day in order. The old assertion (`== []`) was the
    ships-empty tripwire and it fired as designed; it is repointed here rather than
    deleted, so the file's contents still cannot drift unnoticed.

    Pin the exact lines, in order: the cursor is an index into this list, so an
    insertion or reorder above the cursor silently misaligns which edit runs next.
    """
    assert dde.load_sequential_lines() == [
        'Q140568717|P50|Q140568870|P1545|"1"',
        'Q140568719|P50|Q140568870|P1545|"1"',
    ]


def test_every_shipped_sequential_line_parses():
    """A line parse_qs_line() returns None for is skipped silently — and in THIS
    channel a skipped line also stalls the cursor behind it."""
    for line in dde.load_sequential_lines():
        assert dde.parse_qs_line(line) is not None, line


# ─────────────────────── cursor persistence ───────────────────────

def test_missing_cursor_is_zero(tmp_path):
    assert dde.load_sequential_cursor(str(tmp_path / "none.state")) == 0


def test_corrupt_cursor_is_zero(tmp_path):
    p = tmp_path / "seq.state"
    p.write_text("{ not json", encoding="utf-8")
    assert dde.load_sequential_cursor(str(p)) == 0


def test_cursor_round_trips(tmp_path):
    p = str(tmp_path / "seq.state")
    dde.save_sequential_cursor(7, p)
    assert dde.load_sequential_cursor(p) == 7
    assert json.loads(open(p, encoding="utf-8").read()) == {"cursor": 7}


# ─────────────────────── which line runs today ───────────────────────

def test_next_line_at_cursor():
    lines = ["a", "b", "c"]
    assert dde.next_sequential_line(lines, 0) == (0, "a")
    assert dde.next_sequential_line(lines, 2) == (2, "c")


def test_drained_sequence_returns_none():
    assert dde.next_sequential_line(["a", "b"], 2) == (None, None)
    assert dde.next_sequential_line([], 0) == (None, None)


def test_negative_cursor_is_treated_as_drained():
    # Fail-safe: never index backwards into already-run lines.
    assert dde.next_sequential_line(["a"], -1) == (None, None)


# ─────────────────────── advance vs hold ───────────────────────

def test_advance_on_success():
    assert dde.sequential_should_advance(True, "Created") is True
    assert dde.sequential_should_advance(True, "Skipped (already exists)") is True
    assert dde.sequential_should_advance(True, "Removed") is True


def test_advance_on_already_gone_removal():
    # execute_removal returns this exact string when the claim is already absent;
    # the removal's end state is reached, so the cursor must move on rather than
    # retry the same already-done removal forever.
    assert dde.sequential_should_advance(False, "Claim not found for removal") is True


def test_hold_on_genuine_error():
    assert dde.sequential_should_advance(False, "API error: permission denied") is False
    assert dde.sequential_should_advance(False, "429 Too Many Requests") is False
    assert dde.sequential_should_advance(False, "Qualifier error: bad value") is False


def test_hold_is_the_default_for_anything_unrecognised():
    assert dde.sequential_should_advance(False, "") is False
    assert dde.sequential_should_advance(False, "something new") is False


# ─────────────────────── the ordering guarantee it exists for ───────────────────────

def test_pair_never_runs_out_of_order():
    """A two-line pair: line 0 must land before line 1 is ever attempted. Simulate
    day-by-day: the cursor only reaches line 1 after line 0 reached its end state."""
    lines = ["-Q1|P2|Q3", "Q1|P2|Q4"]  # remove-then-add, in order
    cursor = 0

    # Day 1: line 0 errors (e.g. rate-limited) -> HOLD.
    idx, line = dde.next_sequential_line(lines, cursor)
    assert (idx, line) == (0, "-Q1|P2|Q3")
    if not dde.sequential_should_advance(False, "429 Too Many Requests"):
        pass  # cursor unchanged
    assert cursor == 0  # line 1 (the add) has NOT run — no blanking risk

    # Day 2: line 0 succeeds -> advance.
    idx, line = dde.next_sequential_line(lines, cursor)
    assert idx == 0
    if dde.sequential_should_advance(True, "Removed"):
        cursor += 1
    assert cursor == 1

    # Day 3: now, and only now, line 1 (the add) is reachable.
    idx, line = dde.next_sequential_line(lines, cursor)
    assert (idx, line) == (1, "Q1|P2|Q4")
