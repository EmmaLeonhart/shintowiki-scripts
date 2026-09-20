"""No generator paces itself faster than the repo's WDQS floor (2026-09-20).

CLAUDE.md: *"DO NOT HAMMER WIKIDATA … never issue a large batched SPARQL sweep"*,
and `wdqs_transport.WDQS_THROTTLE = 2.5` is the floor — that module describes it
as "no caller can ask to be FASTER than the floor", which is true of callers that
USE it and was not true of the ones that hand-roll their own transport.

⛔ `generate_identical_name_en_labels.py` paced itself at **0.5s**, five times
faster, across ~70 batched POSTs a run. `Generate shrines-missing-en-label list`
failed 5 of its last 6 runs — 09-16, 09-17, 09-18, 09-19, 09-20 — every one
`RateLimitError: 429` from both Stage 2 steps, and the two atomic files it
produces had not regenerated since 09-17.

⚠ This test does not assert that the 429s stopped. It asserts that no module-level
throttle is below the floor, which is the thing that was under our control.
"""
import io
import os
import re
import sys


HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from wdqs_transport import WDQS_THROTTLE  # noqa: E402

# A module-level `THROTTLE = <number>` or `WDQS_THROTTLE = <number>`.
_ASSIGN = re.compile(r"^(?:WDQS_)?THROTTLE\s*=\s*([0-9.]+)\s*(?:#.*)?$", re.M)
# A file that talks to the query service directly rather than through the module.
_ENDPOINT = re.compile(r"query(?:-main)?\.wikidata\.org/sparql")


def _sources():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "__pycache__", "node_modules",
                                    "_site", "tests", ".github"}]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _hand_rolled_wdqs_callers():
    """Files that hit the query service WITHOUT `wdqs_transport`.

    ⛔ The distinction is the whole test. A caller that USES the transport may
    declare `THROTTLE = 0.4` quite safely — the module applies
    `max(throttle, WDQS_THROTTLE)` and the floor wins. Three files do exactly
    that. A caller that rolls its own loop has nothing applying the floor, and
    that is the population this guards.

    ⚠ A sub-floor throttle is also fine when it paces something else entirely:
    `generate_religious_building_multilang.py` sits at 1.0 for `wbgetentities`,
    the READ API, which is not the query service and has its own limits.
    """
    for path in _sources():
        if os.path.basename(path) == "wdqs_transport.py":
            continue
        text = io.open(path, encoding="utf-8", errors="replace").read()
        if not _ENDPOINT.search(text):
            continue
        if "import wdqs_transport" in text or "from wdqs_transport" in text:
            continue
        yield path, text


def test_no_hand_rolled_wdqs_caller_paces_itself_under_the_floor():
    bad = []
    for path, text in _hand_rolled_wdqs_callers():
        for m in _ASSIGN.finditer(text):
            if float(m.group(1)) < WDQS_THROTTLE:
                bad.append("%s (%s)" % (
                    os.path.relpath(path, ROOT).replace("\\", "/"), m.group(1)))
    assert not bad, (
        "these hit WDQS with their own transport and pace faster than "
        "WDQS_THROTTLE=%s, which is what 429'd the en-label workflow for five "
        "consecutive days: %s" % (WDQS_THROTTLE, "; ".join(bad)))


def test_a_transport_user_may_declare_a_lower_number_safely():
    """⚠ Three files declare 0.4 or 1.0 and are NOT offenders: they pass it to
    `wdqs_transport`, which applies `max(throttle, WDQS_THROTTLE)`. A test that
    flagged them would be reporting the floor working."""
    names = {os.path.basename(p) for p, _ in _hand_rolled_wdqs_callers()}
    for safe in ("match_kokugakuin_ids.py", "build_name_in_kana_queue.py",
                 "analyze_layers.py"):
        assert safe not in names, safe


def test_the_file_that_caused_it_is_at_the_floor():
    import generate_identical_name_en_labels as g
    assert g.THROTTLE >= WDQS_THROTTLE


def test_it_is_derived_from_the_floor_not_copied():
    """⛔ A copied `2.5` drifts when the floor moves. The value is imported."""
    src = io.open(os.path.join(HERE, "generate_identical_name_en_labels.py"),
                  encoding="utf-8").read()
    assert "from wdqs_transport import WDQS_THROTTLE" in src
    assert "THROTTLE = max(" in src


def test_a_caller_may_still_be_slower():
    """The floor is a floor. Four callers pace at 3s by choice and moving them to
    a bare 2.5 would have made them less polite than their authors decided."""
    assert max(0.5, WDQS_THROTTLE) == WDQS_THROTTLE
    assert max(3.0, WDQS_THROTTLE) == 3.0


def test_the_transient_backoff_is_the_documented_one():
    """⛔ 15/45/135, not 10/20.

    The 2026-09-20 dispatch measured what a tight retry buys. In order, from the
    step log:

        Stage 2 targets (no-kana, no-en): 4082 shrines, 3041 distinct ja labels.
        SPARQL 502 transient (attempt 1/3)
        FATAL: 429 Too Many Requests from SPARQL endpoint — bailing

    The endpoint said it was struggling, the generator waited ten seconds, asked
    again, and was told to go away. CLAUDE.md: *"503/504 → back off hard, do not
    retry tightly"*, and the floor it names comes *"with exponential backoff
    (15/45/135s)"*.

    ⚠ This does NOT assert the 429s stop. It asserts the retry follows the written
    policy, which it did not, and which raising THROTTLE earlier that day did not
    touch — the retry path never consulted THROTTLE at all.
    """
    import generate_identical_name_en_labels as g
    assert [g._backoff(a) for a in (1, 2, 3)] == [15, 45, 135]


def test_four_attempts_or_the_third_step_never_fires():
    """`wdqs_transport`: "FOUR attempts, because that is what makes the backoff
    15/45/135. At three, only 15 and 45 ever fire and the documented third step is
    decoration." The sleep is guarded by `attempt < retries`, so retries=3 would
    stop after 45s."""
    import generate_identical_name_en_labels as g
    from wdqs_transport import RETRIES
    assert RETRIES == 4
    import inspect
    sig = inspect.signature(g.fetch_batch)
    assert sig.parameters["retries"].default == RETRIES, (
        "fetch_batch pins its own retry count instead of the transport's")


def test_no_tight_retry_is_left_in_the_file():
    """⚠ Asserted against the CODE, with docstrings stripped by `ast`.

    The first version filtered `#` lines only and failed on `_backoff`'s own
    docstring, which quotes the retired backoff to explain why it went.
    `tests/test_workflow_commit_steps_can_commit.py` names the same trap in its
    own words: assert against the code, not against its explanation of itself.
    """
    import ast
    src = io.open(os.path.join(HERE, "generate_identical_name_en_labels.py"),
                  encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)) and ast.get_docstring(node):
            node.body = node.body[1:]
    code = ast.unparse(tree)
    assert "10 * attempt" not in code, (
        "a retry path still sleeps 10s and then re-asks an endpoint that just "
        "returned 5xx; that is the sequence that produced the 429")
