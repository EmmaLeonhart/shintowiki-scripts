"""The daily drip must bail on a real 429, and ONLY on a real 429.

Run 34258613053 (2026-09-08) selected 500 lines, reached line 168, printed
"Rate-limited — stopping further edits" and stopped. Wikidata had not rate-limited
anything: the line failed with

    Qualifier error: The statement has already a qualifier with hash
    a5a17d924a943d498c302ff429c1a0b52fc17de4

and the bail-out test was `"429" in msg`, which that hex hash satisfies. 332 edits
were abandoned and the log named the wrong cause. A 40-char hex hash carries "429"
roughly 0.9% of the time, so this is a recurring tax on the daily rate, not a freak.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QS_DIR = os.path.dirname(HERE)
if QS_DIR not in sys.path:
    sys.path.insert(0, QS_DIR)

SRC = io.open(os.path.join(QS_DIR, "direct_daily_edits.py"), encoding="utf-8").read()


def _sentinel():
    m = re.search(r'^RATE_LIMIT_MSG = "([^"]+)"', SRC, re.M)
    assert m, "RATE_LIMIT_MSG is gone — the bail-out has lost its sentinel"
    return m.group(1)


def test_sentinel_is_what_the_429_paths_actually_return():
    """The constant and the returned literal are the same string, or the bail never fires."""
    sentinel = _sentinel()
    returns = re.findall(r'return False, "(429[^"]*)"', SRC)
    assert returns, "no HTTP-429 return paths found in direct_daily_edits.py"
    assert set(returns) == {sentinel}, (
        "429 paths return %r but the bail-out matches %r" % (sorted(set(returns)), sentinel))


def test_a_hash_containing_429_is_not_a_rate_limit():
    """The exact message from run 34258613053. It must not trip the bail-out."""
    sentinel = _sentinel()
    msg = ("Qualifier error: The statement has already a qualifier with hash "
           "a5a17d924a943d498c302ff429c1a0b52fc17de4")
    assert "429" in msg, "the regression case must still contain the bare digits"
    assert sentinel not in msg


def test_a_real_rate_limit_still_stops_the_run():
    assert _sentinel() in "429 Too Many Requests"


def test_the_bail_out_does_not_test_the_bare_number():
    """Checked against CODE only — the fix's own comment quotes the old test verbatim."""
    code = "\n".join(l for l in SRC.splitlines() if not l.lstrip().startswith("#"))
    assert '"429" in msg' not in code, "bare-substring test reintroduced"
