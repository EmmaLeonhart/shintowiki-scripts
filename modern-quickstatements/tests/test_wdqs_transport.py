"""The shared WDQS transport: throttled, 429 bails, transport failures retry.

Written 2026-09-13 after a truncated body ended a forty-minute sweep. A survey the
same evening found 65 of the 72 WDQS callers in this repo cannot survive that —
each hand-rolls its own transport. Sixty-five files is not a change to make in one
sitting and the severity does not call for it: CI runs every generator
`continue-on-error` and the next day repairs the file.

So this module took the three callers that were literally the same function
copy-pasted, all written 2026-09-12/13. What is pinned here is the policy, because
the policy is CLAUDE.md's and not the module's: 429 bails unconditionally, a
transport failure backs off, and the throttle lives in the transport where a new
caller cannot forget it.
"""

import importlib.util
import os
import re
import sys
import time
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def _restore_the_globals_these_tests_patch():
    """⛔ `_mod()` gives a FRESH module object, but `mod.time` and `mod.urllib` are
    the same singletons every other test imports. So `mod.time.sleep = ...` below
    is not a local patch — it clobbers `time.sleep` process-wide and, without this,
    leaves it clobbered.

    It left `tests/test_wikidata_pacing.py::test_wd_pace_actually_waits` failing
    for anyone who ran the suite with this directory ahead of `tests/`: wd_pace
    called a no-op sleep and returned instantly. CI only stayed green because
    `ci.yml` happens to list `tests/` first, which is argument order, not
    isolation — the next person to reorder that line would have inherited a
    failure with nothing in it pointing here.
    """
    sleep, urlopen = time.sleep, urllib.request.urlopen
    try:
        yield
    finally:
        time.sleep, urllib.request.urlopen = sleep, urlopen

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

# Strip comments and docstrings before scanning a source file, so a note ABOUT
# the dead 429 check is not mistaken for the check itself. Several of the
# adopters carry exactly such a note.
COMMENT_RE = re.compile(r"#.*")
DOCSTRING_RE = re.compile(r'"""[\s\S]*?"""')

MIGRATED = ("generate_invalid_p825_removals.py",
            "generate_ronsha_role_qualifiers.py",
            "generate_misplaced_form_removals.py",
            # Adopted 2026-09-15, on the tick after its reference fix — the
            # "rides with the file's next real change" cadence the queue item
            # sets. It qualified on the item's own test for whether a migration
            # is an upgrade: its transport spaced queries **0.5s** apart (the
            # exact figure CLAUDE.md cites from the match_jinjacho_shrines.py
            # incident that produced the 2.5s floor) and backed off 5/10/15,
            # weaker than the documented 15/45/135. Safe on the module's
            # GET-only constraint: three short fixed queries, no VALUES clause.
            "generate_court_rank_quickstatements.py",
            # Adopted 2026-09-15 alongside its own reference fix, same cadence.
            # Its WDQS client was the weakest in the set: no retry at all, no
            # throttle, and a `if r.status == 429` check after a SUCCESSFUL
            # urlopen — dead code, because urllib raises HTTPError on a 429 and
            # never returns a response to test. So the whole documented policy
            # (bail on 429, back off on 5xx and truncation, 2.5s spacing) was
            # absent, and the module is strictly stronger.
            #
            # ⚠ It also talks to ja.wikipedia, which the other adopters do
            # through `requests`. Its fetcher moved to `requests` too rather
            # than narrowing the urlopen assertion below — the assertion is the
            # evidence, and an adopter with a raw urlopen in it cannot be told
            # apart from one that regrew a WDQS client.
            "generate_saijin_quickstatements.py",
            # Adopted 2026-09-15 with its own skip-set fix, same cadence and the
            # same client as its saijin sibling: no retry, no throttle, and a
            # `if r.status == 429` after a successful urlopen that can never fire.
            "generate_honzon_quickstatements.py",
            # ── Adopted 2026-09-16, as one batch, and the batching needs a word ──
            # The queue item says migration "rides with each file's next real
            # change", because it is per-file reading and NOT uniformly an upgrade.
            # That still holds. What the reading found is a SUBCLASS where it is
            # uniform: a file whose only 429 handling is `if r.status == 429` after
            # a successful urlopen. That branch is unreachable — urllib raises
            # HTTPError on a 429 and never returns a response to test (proved
            # against a local server that answers 429: the with-body never runs) —
            # and none of these five had any retry construct at all. So the whole
            # documented policy was absent from every one of them, and the module
            # is strictly stronger. No judgement call was left per file.
            #
            # These five are the members of that subclass whose ONLY urlopen was
            # the WDQS one, so nothing else had to move to satisfy the assertion
            # below. The rest of the subclass also fetches ja.wikipedia or the
            # Wikidata API through urlopen; converting those fetchers is each
            # file's own change, on the cadence above.
            "generate_bunrei_qualifier_repair.py",
            "generate_reisai_qualifier_repair.py",
            # ⚠ This one paced itself with a bare `wd_pace()` — READ_INTERVAL,
            # **0.3s** — for a SPARQL caller, which `wd_pace.py` tells you in its
            # own docstring not to do, and it fires one query per property pair.
            # 0.5s in generate_court_rank_quickstatements.py was called out as the
            # figure from the incident that set the 2.5s floor; this was lower.
            "generate_kami_parent_qualifiers.py",
            "generate_sango_quickstatements.py",
            "generate_shinto_honorifics.py",
            # ── The rest of the subclass, same day, second pass ──────────────
            # These eight also fetched ja.wikipedia, the Wikidata API, jmapps or
            # rakuten through urlopen, so each needed that fetcher moved to
            # `requests` before it could satisfy the assertion below. Five of them
            # carried a byte-identical `_get`; it is still five copies, not one
            # shared helper — building a second shared transport for the ja.wp API
            # is its own change and was not smuggled into this one.
            #
            # ⚠ Each conversion also turned a 429 from a retried exception into a
            # bail. Under `urlopen` a 429 raised `HTTPError`, and `except Exception`
            # swallowed it straight back into the retry loop — the opposite of the
            # repo's unconditional policy, and indistinguishable from a timeout.
            "generate_address_citation_from_article.py",
            "generate_kofun_quickstatements.py",
            "generate_ontology_census_page.py",
            "generate_p3225_quickstatements.py",
            "generate_shakaku_references.py",
            "generate_souken_quickstatements.py",
            "match_kokugakuin_ids.py",
            # ⚠ Its rakuten fetcher carried the SAME dead `if r.status == 429`
            # beside the WDQS one. Moving it to `requests` — which returns a 429
            # response rather than raising — is what makes that check fire for the
            # first time. It was kept, not deleted.
            "parse_onkamui_bunrei.py")


def _mod():
    if MQ not in sys.path:
        sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        "_t_wdqs", os.path.join(MQ, "wdqs_transport.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Resp:
    status = 200

    def __init__(self, body):
        self._body = body

    def read(self, *a):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


OK = b'{"results": {"bindings": [{"x": {"value": "ok"}}]}}'
SHORT = b'{"results": {"bindings": [{"x": {"value": "tru'


def test_a_truncated_body_is_retried():
    mod = _mod()
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        return _Resp(SHORT if calls["n"] == 1 else OK)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    assert mod.query("SELECT * WHERE {}") == [{"x": {"value": "ok"}}]
    assert calls["n"] == 2, f"not retried ({calls['n']} call(s))"


def test_429_bails_without_retrying():
    """Unconditional repo policy. Widening the retry set must not sweep it up."""
    mod = _mod()
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, None)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    try:
        mod.query("SELECT * WHERE {}")
    except SystemExit as e:
        assert "429" in str(e)
    else:
        raise AssertionError("429 did not bail")
    assert calls["n"] == 1, f"429 retried {calls['n']} times"


def test_a_5xx_is_retried_then_gives_up():
    mod = _mod()
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 504, "Gateway", {}, None)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    try:
        mod.query("SELECT * WHERE {}")
    except mod.urllib.error.HTTPError:
        pass
    else:
        raise AssertionError("a persistent 504 should surface, not be swallowed")
    assert calls["n"] == mod.RETRIES


def test_the_timeout_reaches_urlopen_and_is_not_silently_replaced():
    """`timeout` is a parameter because the callers genuinely differ, and the
    default would have quietly halved one of them.

    `site/generate_orphan_label_fixes.py` allowed **600s**; this module hardcoded
    300. Adopting it without the parameter is not a visible break — it is the same
    query given half the budget, which shows up as an occasional timeout on the
    longest run and nowhere else.
    """
    mod = _mod()
    seen = {}

    def fake(req, timeout=None):
        seen["timeout"] = timeout
        return _Resp(b'{"results": {"bindings": []}}')

    mod.urllib.request.urlopen = fake
    mod.WDQS_THROTTLE = 0
    mod.query("SELECT * WHERE {}")
    assert seen["timeout"] == mod.TIMEOUT == 300, seen
    mod.query("SELECT * WHERE {}", timeout=600)
    assert seen["timeout"] == 600, seen


def test_the_throttle_is_in_the_transport():
    """Emma, 2026-08-24: "You just want to rate limit within your scripts." Pacing
    the transport is the only version a new caller cannot forget."""
    mod = _mod()
    assert mod.WDQS_THROTTLE >= 2.5, (
        "the documented floor is 2.5s; a lower one is how this repo 429'd itself "
        "out of every weekly refresh for a month")
    src = open(os.path.join(MQ, "wdqs_transport.py"), encoding="utf-8").read()
    assert "_last_call" in src and "time.monotonic()" in src, (
        "the throttle is no longer enforced inside query()")


def test_a_429_check_after_a_successful_urlopen_can_never_fire():
    """The mechanism that made the 2026-09-16 batch a uniform upgrade rather than a
    judgement call — pinned because it is the whole argument.

    Eleven WDQS callers in this repo carried, or carried until that batch::

        with urllib.request.urlopen(req, timeout=180) as r:
            if r.status == 429:
                raise SystemExit("429 from WDQS — bailing.")

    which reads as the repo's unconditional 429 policy and is not it. urllib's
    default opener raises `HTTPError` for any non-2xx, so the body of that `with`
    never runs on a 429 and `r.status` is always a success code. The policy held in
    those files only by accident, through an uncaught traceback.

    Asserted against a real server rather than from memory, because "urlopen raises
    on 4xx" is exactly the kind of thing that gets asserted confidently and wrongly.
    """
    import http.server
    import threading
    import urllib.error

    class _H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(429)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        reached = False
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_port}/", timeout=10) as r:
                reached = r.status
        except urllib.error.HTTPError as e:
            assert e.code == 429
        assert reached is False, (
            "urlopen returned a 429 response instead of raising, so `if r.status == 429` "
            "would be live after all — re-read the migration note in MIGRATED above")
    finally:
        srv.shutdown()


def test_post_puts_the_query_in_the_body_and_not_the_url():
    """`post=True` exists because a long VALUES clause does not fit in a GET URL and
    comes back **414 URI Too Long** — deterministically, after burning the backoff.

    This module's own note used to read *"it is GET-only ... if a caller ever needs
    one, add POST rather than chunking around it here."* Callers needed one: every
    WDQS caller in the repo pacing below the 2.5s floor turned out to be a POST
    caller, each with a VALUES clause, and none of them could adopt the module until
    this existed.
    """
    mod = _mod()
    seen = {}

    def fake(req, timeout=None):
        seen["url"] = req.full_url
        seen["data"] = req.data
        seen["ctype"] = req.get_header("Content-type")
        return _Resp(b'{"results": {"bindings": []}}')

    mod.urllib.request.urlopen = fake
    mod.WDQS_THROTTLE = 0

    mod.query("SELECT * WHERE {}", post=True)
    assert seen["data"] is not None, "post=True sent no body"
    assert b"query=" in seen["data"], seen["data"]
    assert "?" not in seen["url"], f"the query is still in the URL: {seen['url']}"
    assert seen["ctype"] == "application/x-www-form-urlencoded", seen["ctype"]

    mod.query("SELECT * WHERE {}")
    assert seen["data"] is None, "GET sent a body"
    assert "query=" in seen["url"], seen["url"]


def test_no_adopter_builds_its_own_wdqs_request():
    """Regrowth guard for EVERY adopter, not just the ones listed in `MIGRATED`.

    `MIGRATED`'s check is `"urllib.request.urlopen" not in src`, which is blunt: it
    cannot tell a WDQS client from a ja.wikipedia or Wikidata-API fetcher, so a file
    that legitimately keeps one can never be listed there. Several adopters are in
    exactly that position — `audit_model_adoption.py`, `investigate_property_modelling.py`
    and `generate_saijin_deity_research.py` each still read the API through `urlopen`,
    correctly.

    This asks the narrower question instead: does a file that imports the transport
    also aim a request at a SPARQL endpoint itself? That is the thing being banned,
    and it can be asked of every adopter regardless of what else the file talks to.

    ⚠ **Its blind spot, stated rather than left to be discovered.** It matches a call
    whose argument list names the endpoint — `requests.get(SPARQL, ...)`,
    `requests.post(WDQS, ...)`. A regrowth that builds a `Request` object first and
    then passes the variable — `req = Request(SPARQL + "?" + ...)` followed by
    `urlopen(req)` — is NOT caught here. For the files in `MIGRATED` that shape is
    covered by the blanket urlopen ban; for the rest it is not covered at all. This
    narrows the gap, it does not close it.
    """
    root = os.path.dirname(MQ)
    offenders = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "__pycache__", "node_modules", "tests"}]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            if os.path.basename(path) == "wdqs_transport.py":
                continue
            src = open(path, encoding="utf-8", errors="replace").read()
            if "import wdqs_transport" not in src:
                continue
            body = COMMENT_RE.sub("", DOCSTRING_RE.sub("", src))
            # A request CONSTRUCTED against a SPARQL endpoint, by either verb.
            #
            # ⚠ Deliberately not `"wikidata.org/sparql" in body`. Several adopters
            # still hold a now-unused endpoint constant, or name the URL in passing,
            # and neither is a request — a first draft of this test flagged 27 files
            # on that alternative alone. What is banned is aiming a call at it.
            if re.search(r"(urlopen|requests\.(?:get|post))\s*\([^)]*\b"
                         r"(?:SPARQL|WDQS|SPARQL_ENDPOINT|ENDPOINT)\b", body):
                offenders.append(os.path.relpath(path, root))
    assert not offenders, (
        "these adopters aim a request at a SPARQL endpoint themselves again: "
        + ", ".join(sorted(offenders)))


def test_no_wdqs_caller_retries_a_429():
    """CLAUDE.md is unconditional: a 429 bails immediately, no retries.

    `generate_p958_qualifiers.sparql_query` did the opposite — 30/60/120/240s over
    four attempts — and said so in its own docstring: *"retry + exponential backoff
    on 429"*. It read as careful. The Wikidata API half of that same file, forty
    lines below, already bailed on the first 429, so the file disagreed with itself.

    The shape banned here is a 429 branch that loops round again. A 429 branch that
    raises, exits or returns is fine — that is the policy.

    ⛔ **Parsed with AST, not matched with a regex, and the first draft proves why.**
    A regex that took the 429 branch as "the indented lines after `== 429:`" ran
    straight past the end of that branch and flagged **fourteen** files whose 429
    branch raises immediately — the `sleep`/`continue` it found belonged to a
    ValueError handler further down the same function. CLAUDE.md already records
    three wrong regex answers over this exact population; this was the fourth.
    """
    import ast as _ast

    root = os.path.dirname(MQ)
    offenders = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "__pycache__", "node_modules", "tests"}]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            src = open(path, encoding="utf-8", errors="replace").read()
            if "wikidata.org/sparql" not in src and "import wdqs_transport" not in src:
                continue
            try:
                tree = _ast.parse(src)
            except SyntaxError:
                continue
            for node in _ast.walk(tree):
                if not isinstance(node, _ast.If):
                    continue
                if "429" not in _ast.unparse(node.test):
                    continue
                # the branch's OWN body only — nothing after the `if` closes
                if any(isinstance(x, (_ast.Continue,))
                       for x in _ast.walk(_ast.Module(body=node.body, type_ignores=[]))):
                    offenders.append(os.path.relpath(path, root))

            # ── The variant with NO 429 branch at all ────────────────────────
            # `raise_for_status()` turns a 429 into an HTTPError; `except
            # Exception` catches it; the loop sleeps and asks again. Nothing in
            # such a function mentions 429, so the check above cannot see it.
            # generate_multilang_quickstatements.run_sparql did exactly this —
            # three times per language, across 43 languages, nightly.
            #
            # A broad retry handler with no 429 branch retries 429s BY OMISSION.
            for fn in [n for n in _ast.walk(tree)
                       if isinstance(n, _ast.FunctionDef)]:
                seg = _ast.get_source_segment(src, fn) or ""
                # ⚠ The request must actually go to a SPARQL ENDPOINT. Gating on
                # "sparql appears in the function" flagged
                # fetch_p11250_from_wiki.fetch_redirect_qids, which calls the
                # Wikidata *API* and matched only because it paces itself with
                # `wd_pace(SPARQL_INTERVAL)`. Its chunk loop is not a retry loop
                # either. Second false positive from a loose gate in this test.
                if not re.search(r"(requests\.(?:get|post)|urlopen)\s*\(\s*[^)]*?"
                                 r"(SPARQL_ENDPOINT|SPARQL\b|WDQS\b|ENDPOINT\b"
                                 r"|wikidata\.org/sparql)", seg):
                    continue
                if "429" in seg:
                    continue                      # has SOME 429 handling; checked above
                loops = [x for x in _ast.walk(fn) if isinstance(x, (_ast.For, _ast.While))]
                if not loops:
                    continue                      # no retry at all is a different defect
                broad = False
                for t in [x for x in _ast.walk(fn) if isinstance(x, _ast.Try)]:
                    for h in t.handlers:
                        name = _ast.unparse(h.type) if h.type else "bare"
                        if "Exception" in name or name == "bare":
                            # does that handler go round again?
                            inner = _ast.Module(body=h.body, type_ignores=[])
                            if any(isinstance(x, _ast.Continue) for x in _ast.walk(inner)) \
                                    or not any(isinstance(x, _ast.Raise)
                                               for x in _ast.walk(inner)):
                                broad = True
                if broad:
                    offenders.append(os.path.relpath(path, root))
    assert not offenders, (
        "these WDQS callers retry a 429 instead of bailing: "
        + ", ".join(sorted(set(offenders))))


def test_no_wdqs_caller_paces_below_the_documented_floor():
    """CLAUDE.md sets `WDQS_THROTTLE = 2.5` as the FLOOR, after an unpaced sweep
    fired ~365 queries and drew repeated 503/504.

    Eight callers were pacing at 0.4s or 0.5s — under half the floor, and 0.5 is the
    exact figure CLAUDE.md cites from that incident. They are on the transport now.
    This walks the tree rather than trusting that: a bare `time.sleep(<2.5)` at the
    top of a retry loop around a WDQS request is the shape being banned.
    """
    root = os.path.dirname(MQ)
    offenders = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "__pycache__", "node_modules", "tests"}]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            src = open(path, encoding="utf-8", errors="replace").read()
            if "wikidata.org/sparql" not in src or "import wdqs_transport" in src:
                continue
            body = COMMENT_RE.sub("", DOCSTRING_RE.sub("", src))
            for m in re.finditer(
                    r"for \w+ in range\([^)]*\):\s*\n\s*time\.sleep\(\s*([0-9.]+)\s*\)", body):
                if float(m.group(1)) < 2.5:
                    offenders.append(f"{os.path.relpath(path, root)} ({m.group(1)}s)")
    assert not offenders, (
        "these WDQS callers pace below the 2.5s floor: " + ", ".join(sorted(offenders)))


def test_query_csv_asks_for_csv_and_never_for_json():
    """The CSV callers exist for a recorded reason and it must not be optimised away.

    Two of them said it in their own docstring: *"CSV, not JSON: the JSON body for
    these result sets comes back truncated."* So moving them to `query` would
    reintroduce, on the very result sets known to provoke it, the failure this
    module was written to survive. `query_csv` gives them the policy without
    touching that choice.
    """
    mod = _mod()
    seen = {}

    def fake(req, timeout=None):
        seen["accept"] = req.get_header("Accept")
        seen["url"] = req.full_url
        return _Resp(b"item,ja\r\nQ1,\xe7\xa5\x9e\xe7\xa4\xbe\r\n")

    mod.urllib.request.urlopen = fake
    mod.WDQS_THROTTLE = 0
    rows = mod.query_csv("SELECT * WHERE {}")
    assert seen["accept"] == "text/csv", seen
    assert "format=json" not in seen["url"], (
        "query_csv asked for JSON in the URL; the header and the query string "
        "would then disagree")
    assert rows == [{"item": "Q1", "ja": "神社"}], rows


def test_query_csv_bails_on_429_and_backs_off_like_query():
    """It shares `_run` with `query`, so the policy is the same object, not a
    second copy of it. Driven rather than read, because "it calls the same
    function" is exactly the claim that rots."""
    mod = _mod()
    calls = {"n": 0}

    def bail(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 429, "Too Many", {}, None)

    mod.urllib.request.urlopen = bail
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    with pytest.raises(SystemExit):
        mod.query_csv("SELECT * WHERE {}")
    assert calls["n"] == 1, f"429 was retried {calls['n']} times"

    waits = []
    calls["n"] = 0

    def gateway(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 504, "Gateway", {}, None)

    mod.urllib.request.urlopen = gateway
    mod.time.sleep = lambda s=0: waits.append(s)
    with pytest.raises(mod.urllib.error.HTTPError):
        mod.query_csv("SELECT * WHERE {}")
    assert calls["n"] == mod.RETRIES
    assert [w for w in waits if w] == [15, 45, 135], waits


def test_a_raw_newline_inside_a_literal_parses_instead_of_costing_195_seconds():
    """WDQS emits RAW control characters inside string literals — a label or
    description containing a real newline comes back unescaped. Python's JSON
    parser rejects that unless `strict=False`.

    This module used `json.load`, which is strict, and the failure mode was worse
    than a plain error: `JSONDecodeError` is in `TRANSIENT`, so a response that was
    perfectly readable got RETRIED on 15/45/135 and then re-raised. Three minutes
    to fail on data we could have parsed.

    Five callers in this repo already parsed with `strict=False` — one of them
    saying why in a comment — which also meant migrating any of them onto this
    module would have been a downgrade.
    """
    mod = _mod()
    calls = {"n": 0}
    raw = b'{"results": {"bindings": [{"l": {"value": "line one\nline two"}}]}}'

    def fake(req, timeout=None):
        calls["n"] += 1
        return _Resp(raw)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    rows = mod.query("SELECT * WHERE {}")
    assert rows == [{"l": {"value": "line one\nline two"}}], rows
    assert calls["n"] == 1, (
        f"the body was retried {calls['n']} times instead of parsed — strict=False "
        "is gone from _parse_bindings")


def test_a_truncated_body_still_raises_and_is_still_retried():
    """The counterpart to the test above: `strict=False` must forgive control
    characters WITHOUT forgiving a body that stops mid-token. If it did, the
    failure this whole module exists for would stop being detected at all."""
    mod = _mod()
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(b'{"results": {"bindings": [{"x": {"value": "tru')
        return _Resp(b'{"results": {"bindings": [{"x": {"value": "ok"}}]}}')

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    assert mod.query("SELECT * WHERE {}") == [{"x": {"value": "ok"}}]
    assert calls["n"] == 2, f"a truncated body was not retried ({calls['n']} call(s))"


def test_the_parse_happens_inside_the_retry_loop():
    """⛔ A truncated JSON body surfaces as a `JSONDecodeError` raised by the PARSE.
    If the parse moved outside the `with` — read the bytes in the loop, decode them
    after — the one failure this module was built for would land outside the thing
    retrying it. Asserted by driving a short read, not by reading the source."""
    mod = _mod()
    calls = {"n": 0}

    def short_then_whole(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp(b'{"results": {"bindings": [{"x": {"value": "tru')
        return _Resp(b'{"results": {"bindings": [{"x": {"value": "ok"}}]}}')

    mod.urllib.request.urlopen = short_then_whole
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    assert mod.query("SELECT * WHERE {}") == [{"x": {"value": "ok"}}]
    assert calls["n"] == 2, f"the short read was not retried ({calls['n']} call(s))"


def test_the_copy_pasted_transports_are_gone():
    """These three carried the same function with no retry at all. If one grows its
    own urlopen back, it has left the shared policy behind."""
    for name in MIGRATED:
        src = open(os.path.join(MQ, name), encoding="utf-8").read()
        assert "import wdqs_transport" in src, f"{name} no longer uses the transport"
        assert "urllib.request.urlopen" not in src, (
            f"{name} calls urlopen directly again, outside the retry policy")


def test_the_one_adopter_outside_this_directory_is_wired_and_stays_wired():
    """`shinto_miraheze/build_ronsha_ranking_queue.py` is the only WDQS caller
    outside `modern-quickstatements/`, so `MIGRATED` above cannot hold it — those
    paths are all resolved against `MQ`.

    It needs an explicit `sys.path` entry for this directory to import the
    transport at all. That reads like a new cross-subproject dependency and is not
    one: the file already writes its output straight into this directory. Pinned
    because an import that exists only through a hand-inserted path is exactly the
    kind that gets tidied away by someone who cannot see what it is for.
    """
    path = os.path.join(os.path.dirname(MQ), "shinto_miraheze",
                        "build_ronsha_ranking_queue.py")
    src = open(path, encoding="utf-8").read()
    assert "import wdqs_transport" in src, "it no longer uses the shared transport"
    assert 'path.insert(0, _uos.path.join(_uar, "modern-quickstatements"))' in src, (
        "the sys.path entry that makes `import wdqs_transport` resolve from "
        "shinto_miraheze/ is gone; the import above cannot work without it")
    assert "urllib.request.urlopen" not in src, (
        "it calls urlopen directly again, outside the retry policy")


def test_no_adopter_kept_the_unreachable_429_check():
    """The check that made this whole subclass migrate must not come back.

    `if r.status == 429` inside a `with urlopen(...)` block is unreachable — see
    `test_a_429_check_after_a_successful_urlopen_can_never_fire`. A `requests`
    caller testing `r.status_code` is a DIFFERENT and live thing, and is allowed;
    this asserts only on the dead form.
    """
    paths = [os.path.join(MQ, n) for n in MIGRATED]
    paths.append(os.path.join(os.path.dirname(MQ), "shinto_miraheze",
                              "build_ronsha_ranking_queue.py"))
    offenders = []
    for path in paths:
        src = open(path, encoding="utf-8").read()
        body = COMMENT_RE.sub("", DOCSTRING_RE.sub("", src))
        if re.search(r"\.status\s*==\s*429", body):
            offenders.append(os.path.basename(path))
    assert not offenders, (
        "these adopters carry the unreachable 429 check again: " + ", ".join(offenders))


def test_the_backoff_is_the_repo_pattern_not_the_one_it_was_lifted_from():
    """15/45/135, exponential — CLAUDE.md names it the floor and
    `generate_genbu_ids.py` implements it as `time.sleep(15 * (3 ** attempt))`.

    ⚠ This module shipped with 30/60/90 for its first day, copied from
    `generate_description_fixes.py` without checking it against the rule. Measured
    2026-09-14: **10 of the 69 WDQS callers already use 15/45/135**, so migrating any
    of them onto the linear version would have quietly downgraded it. A shared module
    has to carry the repo's pattern, not the pattern of whichever file it came from.
    """
    mod = _mod()
    waits = []
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 504, "Gateway", {}, None)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda s: waits.append(s)
    mod.WDQS_THROTTLE = 0
    try:
        mod.query("SELECT * WHERE {}")
    except mod.urllib.error.HTTPError:
        pass
    # The last attempt re-raises rather than sleeping, so RETRIES-1 waits. All three
    # documented steps must actually fire: at RETRIES=3 the 135 never happens, which
    # is what this module shipped with for a day.
    assert waits == [15, 45, 135], waits
    assert mod.RETRIES == 4, (
        "four attempts is what makes the backoff 15/45/135; generate_genbu_ids.py, "
        "the file CLAUDE.md points at as the floor, uses range(4)")


def test_a_deterministic_client_error_is_not_retried():
    """⛔ Observed 2026-09-15: a query with a 2,095-entry VALUES clause came back
    414 URI Too Long — this transport sends the query in the URL of a GET — and the
    loop backed off 15s, 45s and 135s before failing. Three minutes to re-learn a
    deterministic fact.

    The reasoning that makes 429 bail applies: the server has answered, and the
    answer does not change because we ask again. Only 5xx and transport failures are
    worth a second attempt.
    """
    mod = _mod()
    for code in (400, 403, 404, 414, 431):
        calls = {"n": 0}

        def fake(req, timeout=None, _c=code):
            calls["n"] += 1
            raise mod.urllib.error.HTTPError(req.full_url, _c, "no", {}, None)

        mod.urllib.request.urlopen = fake
        mod.time.sleep = lambda *_: None
        mod.WDQS_THROTTLE = 0
        try:
            mod.query("SELECT * WHERE {}")
        except mod.urllib.error.HTTPError:
            pass
        else:
            raise AssertionError(f"{code} should surface")
        assert calls["n"] == 1, f"{code} was retried {calls['n']} times"


def test_a_5xx_is_still_retried_after_that_change():
    """The narrowing must not have swept up the errors that ARE worth retrying."""
    mod = _mod()
    calls = {"n": 0}

    def fake(req, timeout=None):
        calls["n"] += 1
        raise mod.urllib.error.HTTPError(req.full_url, 503, "busy", {}, None)

    mod.urllib.request.urlopen = fake
    mod.time.sleep = lambda *_: None
    mod.WDQS_THROTTLE = 0
    try:
        mod.query("SELECT * WHERE {}")
    except mod.urllib.error.HTTPError:
        pass
    assert calls["n"] == mod.RETRIES, f"503 attempted {calls['n']} times"
