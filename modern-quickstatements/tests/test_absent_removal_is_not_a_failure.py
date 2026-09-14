"""A removal whose statement is already gone is not a failure.

The 2026-09-13 drip reported **"481 succeeded, 1 failed"**. The one failure was

    [190/501] REMOVE: -Q135039251|P31|Q135160342
      FAIL: Claim not found for removal

— the statement was already absent, which is the outcome that line exists to
produce. The code already knew: `sequential_should_advance` has always treated this
exact message as the intended end state and moves the cursor past it. Only the tally
disagreed.

That matters more than one line in five hundred. The failure count is the number a
reader has to be able to trust, and a batch where nothing went wrong reporting a
failure is the same misleading signal as a step warning that blames WDQS without
checking — three of which came off this repo the same day.

⚠ It is deliberately NOT folded into "succeeded". The message cannot distinguish
"already removed" from "the value never matched" — a formatting difference in the
staged line looks identical from here — so it gets its own word and its own counter,
and control flow is untouched.
"""

import importlib.util
import inspect
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)


def _mod():
    if MQ not in sys.path:
        sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        "_t_dde_absent", os.path.join(MQ, "direct_daily_edits.py"))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    return mod


def test_the_sentinel_is_one_constant_shared_by_both_readers():
    """It was a bare string literal in three places — the producer, the cursor
    rule and (by absence) the tally. Three copies is how the tally came to
    disagree with the cursor rule about the same event."""
    mod = _mod()
    assert mod.CLAIM_ABSENT_MSG == "Claim not found for removal"
    src = open(os.path.join(MQ, "direct_daily_edits.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert code.count('"Claim not found for removal"') == 1, (
        "the sentinel is spelled out more than once again")


def test_the_cursor_still_advances_past_an_absent_claim():
    """The behaviour that was already right and must stay right: a removal whose
    target is gone has reached its end state, so the sequence moves on rather than
    retrying the same line every run forever."""
    mod = _mod()
    assert mod.sequential_should_advance(False, mod.CLAIM_ABSENT_MSG) is True
    assert mod.sequential_should_advance(False, "Qualifier error: something") is False
    assert mod.sequential_should_advance(True, "Created") is True


def test_the_tally_counts_it_apart_from_failures():
    src = inspect.getsource(_mod().main)
    assert "already_absent += 1" in src, "it is counted as a failure again"
    assert "already absent ===" in src, "the summary no longer reports it"
    assert 'print(f"  ABSENT: {msg}")' in src, (
        "it still prints as FAIL, which is the word the reader acts on")


def test_it_is_not_counted_as_a_success():
    """"Claim not found" cannot tell "already removed" from "the value never
    matched". Folding it into succeeded would hide a staged line that does not
    match what is on Wikidata."""
    src = inspect.getsource(_mod().main)
    absent_branch = src[src.index("elif msg == CLAIM_ABSENT_MSG:"):src.index("else:", src.index("elif msg == CLAIM_ABSENT_MSG:"))]
    assert "succeeded += 1" not in absent_branch


def test_an_all_absent_run_does_not_redden_itself():
    """The outage detector fires on `succeeded == 0 and failed > 0`, and exists for
    an invalidated bot token failing every save. A run whose removals were all
    already done is not that, and must not be reported as an outage."""
    src = inspect.getsource(_mod().main)
    assert "if succeeded == 0 and failed > 0:" in src, (
        "the outage detector changed shape; re-check that an all-absent run stays "
        "green, since already_absent is no longer part of `failed`")
