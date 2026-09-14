"""A truncated WDQS body must be retried by every caller that can safely do so.

WDQS answers 200 and then cuts the response short mid-row; `r.json()` raises
requests' `JSONDecodeError`, a `ValueError`. On 2026-09-13 that ended a forty-minute
sweep at its last language with nothing written — these generators write their `.txt`
only at the end, so one short read costs everything the run did.

⚠ THIS COVERS THREE CALLERS, NOT ALL OF THEM, and the split is deliberate. A survey
found ~41 WDQS callers with no retry loop at all and 8 with one that catches only
`ReadTimeout`/`ConnectionError`. Of those 8, **five parse the body OUTSIDE the try**,
so widening the clause would not help them — they need code moved, in generators
that can only be verified by running a forty-minute sweep. The three here parse
inside the try, so adding a clause is purely additive: no previously-succeeding path
changes, and a previously-fatal one retries.

The rest ride along with each file's next real change, and
`modern-quickstatements/wdqs_transport.py` is what they migrate to.
"""

import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

# (module, how to call its fetcher). Each parses r.json() inside its try, and each
# fetcher takes different arguments — one a query, one a list of labels, one nothing
# at all — so the call is spelled per module rather than assumed.
COVERED = [
    ("generate_shrines_missing_en_label", lambda m: m.fetch_sparql("SELECT * WHERE {}")),
    ("generate_identical_name_en_labels", lambda m: m.fetch_batch(["jinja"])),
    ("generate_cjk_ja_backfill", lambda m: m.fetch_rows()),
    # The five whose parse sits OUTSIDE the request's try. They were tagged
    # "verifiable only by running a forty-minute sweep" and that was wrong — the
    # faked transport below IS the verification, as the first three had already
    # shown an hour earlier. Guarding the parse is as additive as widening a clause.
    ("generate_derived_name_in_kana", lambda m: m.fetch_sparql("SELECT * WHERE {}")),
    ("generate_kana_qualifier_add", lambda m: m.fetch_sparql("SELECT * WHERE {}")),
    ("generate_kana_qualifier_remove", lambda m: m.fetch_sparql("SELECT * WHERE {}")),
    ("generate_katakana_reading_add", lambda m: m.fetch_sparql("SELECT * WHERE {}")),
    ("generate_katakana_reading_remove", lambda m: m.fetch_sparql("SELECT * WHERE {}")),
]

OK = (b'{"results": {"bindings": [{"item": {"value": "http://www.wikidata.org/entity/Q1"},'
      b' "lab": {"value": "jinja"}, "l": {"value": "x"}, "x": {"value": "ok"}}]}}')
SHORT = b'{"results": {"bindings": [{"item": {"value": "http://www.wikidata.org/entit'


def _load(name):
    if MQ not in sys.path:
        sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        f"_t_short_{name}", os.path.join(MQ, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Resp:
    def __init__(self, body):
        self._body = body
        self.status_code = 200

    def json(self):
        import json
        return json.loads(self._body)

    def raise_for_status(self):
        return None


@pytest.mark.parametrize("name,call", COVERED, ids=[c[0] for c in COVERED])
def test_a_short_read_is_retried_then_succeeds(name, call, monkeypatch):
    """Driven through the real function with the transport faked — the same shape
    used for wdqs_transport and generate_description_fixes, because reading the
    source for an `except` clause does not tell you the parse is inside it."""
    mod = _load(name)
    calls = {"n": 0}

    def fake_post(*a, **kw):
        calls["n"] += 1
        return _Resp(SHORT if calls["n"] == 1 else OK)

    monkeypatch.setattr(mod.requests, "post", fake_post, raising=False)
    monkeypatch.setattr(mod.requests, "get", fake_post, raising=False)
    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    # The return shapes differ (raw bindings vs post-processed lines), so what is
    # asserted is the behaviour under test: the short read did not end the call, and
    # a second request was made.
    call(mod)
    assert calls["n"] == 2, f"{name}: short read not retried ({calls['n']} call(s))"
