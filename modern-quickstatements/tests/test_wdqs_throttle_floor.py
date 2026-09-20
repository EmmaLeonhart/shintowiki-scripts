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
