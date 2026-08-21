"""The Indonesian proposal output must not depend on the order SPARQL returned rows in.

`generate_indonesian_proposals.py` is the one label generator whose query carries no
`ORDER BY`, so WDQS hands back an arbitrary permutation each run. The writer preserved
that order, and every CI regeneration therefore committed the entire file as changed:
measured 2026-08-20, **77,980 insertions against 77,980 deletions** on `id_proposed.txt`
and again on the rendered `id_proposed.html` — identical content, `set(old) == set(new)`,
`old != new`.

Why that mattered beyond tidiness: the churn was camouflage. When a regeneration diff is
always six figures, nobody reads it — and during the two days these pipelines were dead on
their first line, the diff shrank to a one-line date stamp, which reads as "nothing needed
regenerating" rather than as an alarm.

Sorting happens in the WRITER, not the query, so the guarantee survives an endpoint that
ignores `ORDER BY` and any future edit to the query. It cannot be done by sorting the file
afterwards: each statement line is preceded by its own `# Source:` comment, and a line sort
divorces the two.
"""
import io
import os
import random
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _binding(num, ja="三嶋大社"):
    return {"item": {"value": "http://www.wikidata.org/entity/Q%d" % num},
            "jaLabel": {"value": ja},
            "enLabel": {"value": ""},
            "kanaReading": {"value": "みしま"},
            "type": {"value": "shrine"}}


QIDS = [5, 40, 7, 1000, 123456, 22, 999]


@pytest.fixture
def run_in(tmp_path, monkeypatch):
    """Run main() in a temp cwd so the real quickstatements/ output is never touched."""
    monkeypatch.chdir(tmp_path)
    os.makedirs(tmp_path / "quickstatements", exist_ok=True)

    def run(rows):
        import generate_indonesian_proposals as gip
        monkeypatch.setattr(gip, "fetch_candidates", lambda: rows)
        gip.main()
        return io.open(str(tmp_path / "quickstatements" / "id_proposed.txt"),
                       encoding="utf-8").read()
    return run


def test_same_output_regardless_of_input_order(run_in):
    rows = [_binding(q) for q in QIDS]
    outs = []
    for seed in (1, 2, 3):
        shuffled = list(rows)
        random.Random(seed).shuffle(shuffled)
        outs.append(run_in(shuffled))
    assert outs[0] == outs[1] == outs[2], (
        "output depends on SPARQL row order — this is the 77,980-line churn returning")


def test_sorted_numerically_not_lexically(run_in):
    """Q999 must precede Q1000. A lexical sort is deterministic too, but it interleaves
    magnitudes and makes the file hard for a human to scan."""
    out = run_in([_binding(q) for q in QIDS])
    got = [l.split("\t")[0] for l in out.splitlines() if l.startswith("Q")]
    assert got == ["Q5", "Q7", "Q22", "Q40", "Q999", "Q1000", "Q123456"], got


def test_every_statement_keeps_its_own_source_comment(run_in):
    """The reason the fix is a record sort and not a line sort: the comment and the
    statement it describes must stay adjacent, in that order."""
    lines = run_in([_binding(q) for q in QIDS]).splitlines()
    assert len(lines) == 2 * len(QIDS)
    for comment, statement in zip(lines[0::2], lines[1::2]):
        assert comment.startswith("# Source:"), comment
        assert statement.startswith("Q") and "\tLid\t" in statement, statement


def test_the_query_still_has_no_order_by():
    """Pins the premise. If someone adds ORDER BY later the sort is redundant but still
    correct — and this test failing is the prompt to re-read this file, not to delete it."""
    src = io.open(os.path.join(HERE, "generate_indonesian_proposals.py"),
                  encoding="utf-8").read()
    # Comment lines are stripped first: the sort's own rationale block explains WHY there
    # is no ORDER BY, so a whole-file grep matches the explanation and fails on itself.
    code = [l for l in src.splitlines() if not l.lstrip().startswith("#")]
    assert not any("ORDER BY" in l for l in code), (
        "query gained an ORDER BY — the writer-side sort is now belt-and-braces; "
        "keep it, and update this test's rationale")
