"""French elision on shrine labels: "sanctuaire de Hakusan" -> "d’Hakusan".

Emma 2026-08-04 asked for this as a rule that generates its QuickStatements
straight away, since it needs no per-item judgement. What it actually needed was
a measurement first — see the module docstring. The tests below are mostly the
two ways this went wrong before it went right.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
ROOT = os.path.dirname(MQ)
for p in (MQ, os.path.join(ROOT, "shinto_miraheze")):
    if p not in sys.path:
        sys.path.insert(0, p)

_KEEP_STDOUT_ALIVE = [sys.stdout]
import generate_french_elision_fixes as gen  # noqa: E402
_KEEP_STDOUT_ALIVE.append(sys.stdout)
import direct_daily_edits as dde  # noqa: E402
_KEEP_STDOUT_ALIVE.append(sys.stdout)

OUT = os.path.join(MQ, "french_elision_fixes.txt")


def test_the_query_names_a_real_entity():
    """The bug that made this generator report a clean corpus. SHRINE already
    holds "Q845945" and the template read `wd:Q%s`, so the query asked for
    `wd:QQ845945` — an entity that does not exist. WDQS answers that with zero
    rows and no error, which is indistinguishable from having no work to do."""
    assert "wd:QQ" not in gen.QUERY
    assert "wd:Q845945" in gen.QUERY


def test_the_query_does_not_rely_on_a_word_boundary():
    # SPARQL's REGEX is XPath flavoured and has no \b.
    assert r"\b" not in gen.QUERY


def test_de_before_a_plain_vowel_elides():
    assert gen.elide("sanctuaire de Ise") == "sanctuaire d’Ise"


def test_de_before_a_macron_vowel_elides():
    # The case Emma named. It does not occur in the corpus today — the rule is
    # carried anyway so the first one a future label pass introduces is caught.
    assert gen.elide("sanctuaire de Ōminakami") == "sanctuaire d’Ōminakami"


def test_de_before_h_elides():
    # NOT a grammar decision — French elides before mute h and not before
    # aspirated h, and whether a Japanese h- is either is not a question French
    # answers. The corpus decided it 3,645 to 25.
    assert gen.elide("sanctuaire de Hakusan") == "sanctuaire d’Hakusan"


def test_de_before_a_consonant_is_left_alone():
    assert gen.elide("sanctuaire de Samukawa") is None


def test_de_la_and_de_le_are_not_elision_sites():
    # A different construction. "de la" must never become "d’la".
    assert gen.elide("sanctuaire de la Éternité") is None
    assert gen.elide("sanctuaire de le Ise") is None


def test_elision_happens_mid_label_too():
    assert gen.elide("sanctuaire Kumano de Hayatama") == \
        "sanctuaire Kumano d’Hayatama"


def test_already_elided_labels_produce_nothing():
    assert gen.elide("sanctuaire d’Hachiman") is None


def test_file_is_registered_with_the_drip():
    assert "french_elision_fixes.txt" in dde.ATOMIC_FILES


def test_every_committed_line_parses_and_is_french():
    lines = [l.strip() for l in open(OUT, encoding="utf-8") if l.strip()]
    assert lines, "generator produced nothing — check the query before the corpus"
    for line in lines:
        assert dde.parse_qs_line(line), line
        assert "|Lfr|" in line, line


def test_no_committed_line_still_contains_an_unelided_de():
    for line in open(OUT, encoding="utf-8"):
        if not line.strip():
            continue
        value = line.split("|", 2)[2].strip().strip('"')
        assert not re.search(" de [%s]" % gen.VOWELS, value), line
