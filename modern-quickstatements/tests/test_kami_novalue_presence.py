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
