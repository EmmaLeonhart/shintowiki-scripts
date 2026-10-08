"""The P21/P569 presence checks must see novalue/somevalue statements.

Emma, 2026-10-08, with a screenshot of a kami carrying a column of identical
"date of birth: no value" statements: "I think there is an error where the no value
thing is applied constantly in quickstatements".

The cause: `<kami>|P569|novalue` is emitted only where the kami has no P569, and
the check was `OPTIONAL { ?k wdt:P569 ?d }`. A novalue statement has no `wdt:`
triple (WDQS writes it as `?k a wdno:P569`), so a kami that already had one still
read as "no P569" and every drip round added another. `p:P569` matches the
statement node whatever its value, so it sees novalue too.
"""
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def test_presence_checks_use_statement_nodes():
    for name in ("generate_shinto_short_names.py", "generate_shinto_honorifics.py"):
        src = _src(name)
        assert re.search(r"\?k p:P569\s+\?d", src), name
        assert re.search(r"\?k p:P21\s+\?g", src), name
        assert not re.search(r"\?k wdt:P569\s+\?d", src), name
        assert not re.search(r"\?k wdt:P21\s+\?g", src), name


# --- short name as a qualifier on P1035 (Emma, 2026-10-08) -----------------------
# "short name is supposed to be a qualifier but is being applied as a top level
# statement"; chose "Qualifier on P1035"; romaji: "regular one is ja and romaji is mul".

def test_stage2_emits_short_name_as_p1035_qualifier():
    src = _src("generate_shinto_short_names.py")
    assert "|P1035|{best_h}|P1813|ja:" in src
    assert "|P1813|mul:" in src
    # the old top-level shape must be gone
    assert "f'{qid}|P1813|ja:" not in src
    assert "|P2440|" not in src.split('"""', 2)[2]
    # and the presence check reads the qualifier on the P1035 statement
    assert "?st pq:P1813 ?sn" in src


def test_toplevel_remover_is_confirmed_and_value_matched():
    src = _src("generate_shinto_short_name_toplevel_removals.py")
    assert "?st pq:P1813 ?v" in src and "?top ps:P1813 ?v" in src
    import sys
    sys.path.insert(0, HERE)
    import generate_shinto_short_name_toplevel_removals as m
    lines = m.build_lines([("Q1", "ja", 'Ame"no'), ("Q1", "ja", 'Ame"no')])
    assert lines == ['-Q1|P1813|ja:"Ame\\"no"']
    stage1 = re.search(r'^KAMI_CLASS = "(Q\d+)"', _src("generate_shinto_honorifics.py"), re.M)
    assert stage1 and m.KAMI_CLASS == stage1.group(1)


def test_toplevel_remover_is_registered():
    with open(os.path.join(HERE, "direct_daily_edits.py"), encoding="utf-8") as f:
        assert '"shinto_short_name_toplevel_removals.txt"' in f.read()
    wf = os.path.join(os.path.dirname(HERE), ".github", "workflows", "generate-quickstatements.yml")
    with open(wf, encoding="utf-8") as f:
        assert "python generate_shinto_short_name_toplevel_removals.py" in f.read()
