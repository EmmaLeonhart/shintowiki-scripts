"""`write_quickstatements` must produce the same bytes regardless of SPARQL row order.

This file exists because an audit got it wrong in an instructive way. On 2026-08-20 the five
label pipelines were checked for churn by grepping for `ORDER BY`; `fetch_shrines_tokiponize`
has one, so it was cleared, and the conclusion recorded was that
`generate_indonesian_proposals` was "the only one affected". The next CI regeneration
falsified that: `tok.txt` churned **26,834 lines**, verified a pure permutation (same line
count, `set(old) == set(new)`, `old != new`).

The clause is `ORDER BY ?srcLabel` — the shrine NAME, not the QID. Shrine names are
massively non-unique here (八幡神社 alone is hundreds), and SPARQL guarantees nothing about
the relative order of rows sharing a sort key. **An ORDER BY on a non-unique column is not a
total order**, which is precisely what a grep for the clause cannot see.

The other three pipelines order by `?item`, the QID, which is unique — those were and are
genuinely safe.

The sort keeps `source_label` as the primary key, so the alphabetical-by-name order the
query was reaching for is preserved; the QID is appended only to break ties.
"""
import os
import random
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from fetch_shrines_tokiponize import write_quickstatements  # noqa: E402


def _row(qid, src_label, tok):
    return {"qid": "Q%d" % qid, "en_label": "", "ja_label": "",
            "source_lang": "en", "source_label": src_label,
            "target_lang": "tok", "toki_pona_label": tok}


# Deliberately name-colliding: this is the real shape of the data, and the exact case an
# ORDER BY on ?srcLabel cannot disambiguate.
ROWS = [
    _row(2821462, "Hachiman Shrine", "tomo sewi Hatiman"),
    _row(139584513, "Hachiman Shrine", "tomo sewi Hatiman tu"),
    _row(65260948, "Hachiman Shrine", "tomo sewi Hatiman tu wan"),
    _row(2824122, "Atago Shrine", "tomo sewi Atako"),
    _row(999, "Atago Shrine", "tomo sewi Atako tu"),
    _row(1000, "Zenkoji", "tomo sewi Senkoki"),
]


def _write(tmp_path, rows):
    out = write_quickstatements(rows, outdir=str(tmp_path))
    with open(out["tok"], encoding="utf-8") as fh:
        return fh.read()


def test_same_bytes_regardless_of_row_order(tmp_path):
    outs = []
    for seed in (1, 2, 3, 4):
        shuffled = list(ROWS)
        random.Random(seed).shuffle(shuffled)
        outs.append(_write(tmp_path, shuffled))
    assert len(set(outs)) == 1, (
        "output depends on SPARQL row order — the 26,834-line tok.txt churn is back")


def test_name_collisions_are_ordered_by_qid_not_left_to_the_endpoint(tmp_path):
    """The three Hachiman rows share a srcLabel, so ORDER BY ?srcLabel leaves their
    relative order undefined. They must come out in QID order, numerically."""
    out = _write(tmp_path, list(reversed(ROWS)))
    qids = [l.split("\t")[0] for l in out.splitlines() if l.startswith("Q")]
    hachiman = [q for q in qids if q in ("Q2821462", "Q139584513", "Q65260948")]
    assert hachiman == ["Q2821462", "Q65260948", "Q139584513"], hachiman


def test_alphabetical_by_source_label_is_preserved(tmp_path):
    """The query's intent -- browsable alphabetically by name -- must survive the fix.
    Sorting by QID alone would have been deterministic and also wrong here."""
    out = _write(tmp_path, list(ROWS))
    names = [l.split('"')[1] for l in out.splitlines() if l.startswith("# Source:")]
    assert names == sorted(names), names
    assert names[0].startswith("Atago") and names[-1].startswith("Zenkoji")


def test_every_statement_keeps_its_own_source_comment(tmp_path):
    """Why this is a record sort and not a line sort: comment and statement stay adjacent."""
    lines = _write(tmp_path, list(ROWS)).splitlines()
    assert len(lines) == 2 * len(ROWS)
    for comment, statement in zip(lines[0::2], lines[1::2]):
        assert comment.startswith("# Source:"), comment
        assert statement.startswith("Q") and "\tLtok\t" in statement, statement
