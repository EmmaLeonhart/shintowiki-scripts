r"""A QuickStatements value must survive being read back off the wiki page.

The generators are read-modify-write: parse the QS lines already on the page, keep
the ones that cannot be retired yet, re-render the whole page. For years the parse
captured each value *still escaped* and the render escaped it again, so a value's
backslashes doubled on every run. There was a ``qs_escape`` in four copies and a
``qs_unescape`` nowhere -- an inverse that does not exist cannot be called.

It stayed invisible because almost no shintowiki title contains a quote or a
backslash, and because a title that IS in ``duplicate_qids.state`` gets rewritten
from state each run, which silently repairs it. The one line that detonated had
both properties: ``List of Kofun in Japan with the Name "Hyo"`` (Q123999885) has two
double quotes, and its page is missing on miraheze, so the existence check dropped
it from the fresh set and only the page-copied value survived. By 2026-08-30 that
single line was 1,048,643 bytes and [[QuickStatements/P6262]] could no longer be
saved under MediaWiki's 2,048 KB ceiling.

The failure was filed as "the page has outgrown the limit, paginate it". It had not.
Splitting the page would not have helped for even one more run: a QS line is
indivisible, and the next doubling put that one line over the ceiling on its own.
"""
import importlib
import os
import re
import sys

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in (_ROOT, os.path.join(_ROOT, "shinto_miraheze")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from shinto_miraheze.qs_value import qs_escape, qs_unescape  # noqa: E402

BS = chr(92)

# The live title that broke the page, plus the shapes around it. shintowiki really
# does have ``Template:\`` and ``Template:\sandbox``, so a lone backslash is not a
# hypothetical.
VALUES = [
    "plain title",
    'List of Kofun in Japan with the Name "Hyo"',
    'List of Kofun in Japan with the Name "Inari"',
    "Template:" + BS,
    "Template:" + BS + "sandbox",
    BS,
    BS + BS,
    BS + '"',
    '"',
    '""',
    'a "b" ' + BS + " c",
    "shinto:Category:Articles with " + BS + BS + ' "quoted" bits',
    "健磐龍命",
]


def test_unescape_inverts_escape():
    for value in VALUES:
        assert qs_unescape(qs_escape(value)) == value, value


def test_escape_produces_a_value_that_reparses_off_a_rendered_line():
    """End to end through the line format the generators actually write and match."""
    line_re = re.compile(r'^(Q\d+)\|P6262\|"shinto:(.+)"$')
    for value in VALUES:
        line = 'Q1|P6262|"shinto:%s"' % qs_escape(value)
        m = line_re.match(line)
        assert m, line
        assert qs_unescape(m.group(2)) == value, value


def test_a_value_is_a_fixed_point_across_many_read_modify_write_cycles():
    """The property the page needed: run 500 grows nothing over run 1."""
    for value in VALUES:
        rendered = qs_escape(value)
        for _ in range(500):
            rendered = qs_escape(qs_unescape(rendered))
        assert rendered == qs_escape(value), value
        assert qs_unescape(rendered) == value, value


def test_the_old_behaviour_really_did_double_every_run():
    """Guards the diagnosis itself, so a later reader need not take it on trust.

    Re-escaping without unescaping is exponential. Each cycle doubles the backslashes
    already there and adds two more for the title's two quotes, so from two the count
    runs ``b -> 2b + 2``, i.e. ``2**(n+2) - 2`` after n cycles.

    The live page held **1,048,574**, which is that formula at n=18: the page had been
    regenerated eighteen times since the line was first written, and it took eighteen
    runs to go from 44 bytes to a megabyte.
    """
    value = 'List of Kofun in Japan with the Name "Hyo"'
    rendered = qs_escape(value)
    assert rendered.count(BS) == 2

    counts = []
    for _ in range(20):
        rendered = qs_escape(rendered)          # the bug, verbatim
        counts.append(rendered.count(BS))

    assert counts == [2 ** (n + 3) - 2 for n in range(20)]
    assert counts[17] == 1048574, "the count measured on the live page on 2026-09-04"
    assert len(rendered.encode("utf-8")) > 2048 * 1024, (
        "one line alone must exceed MediaWiki's ceiling -- which is why pagination "
        "was never the fix: a QS line cannot be split"
    )


def test_no_module_keeps_its_own_qs_escape():
    """Four copies drifted apart; that is how one of them lost backslash handling.

    ``modern-quickstatements/generate_shinto_honorifics.py`` escaped quotes and not
    backslashes, so a label containing one emitted an invalid QS value. One
    definition, imported everywhere -- the same rule ``user_agent.py`` records for
    the User-Agent string after it was copy-pasted into ~86 places.
    """
    offenders = []
    for sub in ("shinto_miraheze", "modern-quickstatements", "tests"):
        base = os.path.join(_ROOT, sub)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                if os.path.abspath(path) == os.path.abspath(
                        os.path.join(_ROOT, "shinto_miraheze", "qs_value.py")):
                    continue
                with open(path, encoding="utf-8") as fh:
                    if re.search(r"^def qs_(un)?escape\b", fh.read(), re.M):
                        offenders.append(os.path.relpath(path, _ROOT))
    assert not offenders, offenders


# --- the repair path -------------------------------------------------------

# The script wraps ``sys.stdout`` in a utf-8 TextIOWrapper at module load. Left in
# place that closes pytest's capture buffer at teardown and the whole session dies
# with "I/O operation on closed file" before a single test runs -- the same hazard
# ``shinto_miraheze/tests/test_title_filename_roundtrip.py`` documents. Import with
# the real streams put back afterwards.
# Restoring the streams is not sufficient on its own: the discarded wrapper closes
# the buffer it wrapped when it is collected, and that buffer is pytest's capture
# tmpfile. ``detach()`` breaks that link first.
_stdout, _stderr = sys.stdout, sys.stderr
try:
    _gen = importlib.import_module("generate_p6262_quickstatements")
finally:
    _wrapper = sys.stdout
    sys.stdout, sys.stderr = _stdout, _stderr
    if _wrapper is not _stdout:
        try:
            _wrapper.detach()
        except Exception:
            pass


def test_parse_qs_page_returns_the_real_title_not_the_escaped_text():
    value = 'shinto:List of Kofun in Japan with the Name "Hyo"'
    line = 'Q123999885|P6262|"%s"' % qs_escape(value)
    assert _gen.parse_qs_page(line) == {"Q123999885": value}


def test_the_page_value_never_wins_over_the_state_file():
    """A QID the state knows is re-derived, which is what repairs a polluted line."""
    corrupt = "shinto:List of Kofun " + BS * 64 + "junk"
    clean = 'shinto:List of Kofun in Japan with the Name "Hyo"'
    preserved, removed, repaired = _gen.resolve_existing(
        {"Q123999885": corrupt}, {"Q123999885": clean}, {"Q123999885": []})
    assert preserved == {"Q123999885": clean}
    assert removed == []
    assert repaired == 1


def test_a_qid_the_state_does_not_know_keeps_its_page_value():
    preserved, removed, repaired = _gen.resolve_existing(
        {"Q1": "shinto:Orphan"}, {}, {"Q1": []})
    assert preserved == {"Q1": "shinto:Orphan"} and removed == [] and repaired == 0


def test_a_line_already_on_wikidata_is_removed_at_its_state_value():
    """The removal test must use the corrected value, or a polluted line never goes.

    Comparing the page's own text against Wikidata is what kept Q123999885 on the
    page: the corrupted string matched nothing, so it was preserved forever.
    """
    clean = "shinto:Kami One"
    preserved, removed, repaired = _gen.resolve_existing(
        {"Q1": "shinto:Kami One" + BS * 8}, {"Q1": clean}, {"Q1": [clean]})
    assert removed == ["Q1"] and preserved == {} and repaired == 1


def test_an_unknown_wikidata_answer_preserves_rather_than_drops():
    """``None`` means the SPARQL fetch said nothing about this QID, not 'no claim'."""
    preserved, removed, _ = _gen.resolve_existing(
        {"Q1": "shinto:Page"}, {"Q1": "shinto:Page"}, {})
    assert preserved == {"Q1": "shinto:Page"} and removed == []
