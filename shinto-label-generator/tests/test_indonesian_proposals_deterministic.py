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


def _binding(num, ja="三嶋神社"):
    """A row the generator can actually derive from.

    The en label used to be irrelevant here — the label was read off the KANJI
    with pykakasi, so an empty `enLabel` still produced output. Since 2026-09-11
    the English label IS the source (Emma: "They should be derived from the
    proposed English labels"), so a row without one correctly yields nothing and
    these tests would be asserting against an empty file."""
    return {"item": {"value": "http://www.wikidata.org/entity/Q%d" % num},
            "jaLabel": {"value": ja},
            "enLabel": {"value": "Mishima Shrine"},
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
        # Isolate from the real staged en-label batches: they are resolved
        # __file__-relative, so a temp cwd does not hide them.
        monkeypatch.setattr(gip, "load_en_proposals", lambda: {})
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


# ---- the derivation itself ---------------------------------------------------
#
# Emma, 2026-09-10: "the Indonesian labels often appear quite dubious and I'm not
# sure how they were derived. They should be derived from the proposed English
# labels for the shrines." The four cases named below were the actual output of
# the pykakasi-on-kanji derivation and are pinned so it cannot come back.

import generate_indonesian_proposals as gip  # noqa: E402


@pytest.mark.parametrize("en,expected", [
    ("Sasuke Inari Shrine", "Kuil Sasuke Inari"),
    # "Kuil Genpachi Hata" — pykakasi read 元八幡 as gen-pachi-hata.
    ("Moto Hachiman", "Kuil Moto Hachiman"),
    # "Kuil Fujisaki Hachi Hata" — 八旛 read as hachi-hata.
    ("Fujisaki Hachimangū", "Kuil Fujisaki Hachimangū"),
    # "Kuil Sueyamajinja" AND "Kuil Tozanjinja" — the same QID twice.
    ("Tōzan Shrine", "Kuil Tōzan"),
    # "Kuil Yusuharahachimangu" — no spaces, macron dropped.
    ("Yusuhara Hachimangū", "Kuil Yusuhara Hachimangū"),
])
def test_the_english_label_is_the_source(en, expected):
    assert gip.indonesian_label(en, "shrine")[0] == expected


def test_a_macron_is_kept():
    """623 of the sampled id labels carry one; `Kuil Ueno Tenmangū` is the corpus
    form. The old code stripped them."""
    assert gip.indonesian_label("Ueno Tenmangū", "shrine")[0] == "Kuil Ueno Tenmangū"


def test_a_parenthetical_disambiguator_is_kept():
    """Corpus: 'Ueno Ōji Shrine (Osaka)' -> 'Kuil Ueno Ōji (Osaka)'."""
    assert (gip.indonesian_label("Ueno Ōji Shrine (Osaka)", "shrine")[0]
            == "Kuil Ueno Ōji (Osaka)")


def test_a_transliterated_suffix_stays_in_the_name():
    """CLAUDE.md: "The ending is part of the name. 社 ≠ 神社 ≠ 宮." Corpus 1,449
    against 27."""
    assert (gip.indonesian_label("Kunōzan Tōshō-gū", "shrine")[0]
            == "Kuil Kunōzan Tōshō-gū")


@pytest.mark.parametrize("en,want", [
    ("Udo Jingū", "Kuil Agung Udo"),
    ("Sumiyoshi Taisha", "Kuil Agung Sumiyoshi"),
    ("Izumo-daijingū", "Kuil Agung Izumo"),
    ("Ise Jingū (Naikū)", "Kuil Agung Ise (Naikū)"),
])
def test_jingu_and_taisha_become_kuil_agung(en, want):
    """Emma's ruling, 2026-09-11. The corpus splits 53 `Kuil <whole>` against 46
    `Kuil Agung X`, so it decides nothing; she chose Agung. The hyphen left by
    stripping "Izumo-daijingū" goes with the suffix."""
    assert gip.indonesian_label(en, "shrine")[0] == want


@pytest.mark.parametrize("en", [
    "Kōtai Jingū (disambiguation)",
    "Hachiman Shrine (disambiguation)",
])
def test_a_disambiguation_page_is_refused(en):
    """A parenthetical is normally kept as a disambiguator, but this one says the
    item IS a Wikimedia disambiguation page. `Q20037429` is P31 both Q4167410 and
    a shrine class, which is how it reaches the shrine query; the Agung rule then
    proposed "Kuil Agung Kōtai (disambiguation)" for it — a shrine label on a
    navigation page, in the wrong language, when the item already carries the id
    description "Halaman disambiguasi"."""
    assert gip.indonesian_label(en, "shrine")[0] is None


def test_an_ordinary_parenthetical_is_still_kept():
    """The refusal above must not swallow real disambiguators."""
    assert (gip.indonesian_label("Ueno Ōji Shrine (Osaka)", "shrine")[0]
            == "Kuil Ueno Ōji (Osaka)")


def test_the_grand_shrine_word_alone_is_still_refused():
    """"Kuil Agung" with no name is not a label."""
    assert gip.indonesian_label("Jingū", "shrine")[0] is None


def test_no_english_label_produces_nothing():
    """Reading the kanji instead is what produced "Kuil Genpachi Hata"."""
    assert gip.indonesian_label("", "shrine")[0] is None


def test_forbidden_whitespace_is_folded():
    """It arrives from the EN label, and tests/test_label_whitespace.py refuses
    it in any committed batch."""
    label = gip.indonesian_label("Wakamiya Hachiman Shrine", "shrine")[0]
    assert label == "Kuil Wakamiya Hachiman"
    assert " " not in label


def test_a_gloss_label_is_refused():
    """Deriving faithfully from a descriptive English label gives a faithful and
    still-useless Indonesian one: "Kuil Co-Enshrinement of Ohowano"."""
    assert gip.indonesian_label(
        "Co-Enshrinement of Ohowano Shrine (Ronsha 1)", "shrine")[0] is None


def test_a_temple_gets_wihara():
    assert (gip.indonesian_label("Hojuji Temple (Toyonaka City)", "temple")[0]
            == "Wihara Hojuji (Toyonaka City)")
