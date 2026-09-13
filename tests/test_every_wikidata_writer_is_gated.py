"""Anything that can write to Wikidata must consult the lockout in its own code.

CLAUDE.md: the lockout lives in ONE state file, and the three scripts holding
`MW_BOTNAME`/`BOT_TOKEN` check it "as the first thing in `main()`, so a **local or
manual** run is covered, not just CI."

The reason that is in code and not only in the workflows is a real incident: the
freeze used to be a date pasted into each workflow, `create-items.yml` never
consulted it, and on 2026-08-16 it was hours from creating two items straight
through the 2026-08-06 freeze. A gate that lives only in one caller is a gate the
next caller misses.

So the invariant is not "the workflows are gated" — it is **"a script that can
authenticate a Wikidata edit gates itself"**. This test finds those scripts by
their credentials rather than by a hand-kept list, so a fourth one cannot appear
without turning it red.

Measured 2026-09-13: exactly three qualify and all three are gated. Two things
that look like writers and are not, checked so the next sweep does not re-chase
them:

* `submit_daily_batch.py` names `QS_TOKEN`, but the QuickStatements path was
  retired 2026-07-04. It has four functions, imports no HTTP client, and its
  docstring says "No network calls; the QS_TOKEN/QS_USERNAME secrets are no
  longer used." It writes a report and exits 1 so the direct path fires.
* ~30 generators contain `requests.post` alongside the string "wikidata.org", but
  the POST goes to the SPARQL endpoint — a read — or to shinto.miraheze's API.
  Property names like `wbsetqualifier` appear in their docstrings describing what
  the QuickStatements they emit will eventually do.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Holding either of these means the script can authenticate an edit as the bot.
WRITE_CREDENTIALS = ("MW_BOTNAME", "BOT_TOKEN")

# The in-code gate, however it is spelled at the call site.
GATE_MARKERS = ("wikidata_edit_allowed", "wikidata_editing_allowed")

SKIP_DIRS = {".git", "__pycache__", "node_modules", "_site", "tests"}


def _python_sources():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                path = os.path.join(dirpath, name)
                yield os.path.relpath(path, ROOT).replace("\\", "/")


def _credential_holders():
    out = {}
    for rel in _python_sources():
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        # A mention inside a comment or docstring is not possession. Require the
        # name to appear in an environment lookup.
        if re.search(r"(?:environ(?:\.get)?\s*\(|getenv\s*\()\s*[\"'](?:%s)[\"']"
                     % "|".join(WRITE_CREDENTIALS), src):
            out[rel] = src
    return out


def test_every_wikidata_credential_holder_gates_itself():
    holders = _credential_holders()
    assert holders, (
        "no script reads MW_BOTNAME/BOT_TOKEN any more — if the write path moved, "
        "this test has to move with it rather than passing vacuously")
    ungated = sorted(rel for rel, src in holders.items()
                     if not any(m in src for m in GATE_MARKERS))
    assert not ungated, (
        "these can authenticate a Wikidata edit and do not check the lockout in "
        f"their own code: {ungated}. A workflow-level gate is not enough — that is "
        "how create-items.yml came hours from creating items through the 2026-08-06 "
        "freeze.")


def test_the_gate_is_the_first_thing_main_does():
    """Gating after the work has started is not gating. Each holder must reach the
    check before it reaches an edit — pinned as "before any API call in main"."""
    for rel, src in sorted(_credential_holders().items()):
        idx_main = src.find("def main(")
        assert idx_main != -1, f"{rel} has no main() to gate"
        body = src[idx_main:]
        gate_at = min((body.find(m) for m in GATE_MARKERS if m in body), default=-1)
        assert gate_at != -1, f"{rel} does not consult the lockout inside main()"
        for call in ("wbcreateclaim", "wbeditentity", "wbsetclaim", "page.save("):
            at = body.find(call)
            if at != -1:
                assert gate_at < at, (
                    f"{rel} reaches {call} at {at} before the lockout check at {gate_at}")


def test_the_retired_quickstatements_submitter_still_cannot_reach_the_network():
    """It names QS_TOKEN only to say the secret is unused. If it ever regrows an
    HTTP client it becomes a write path and needs the gate like the others."""
    path = os.path.join(ROOT, "modern-quickstatements", "submit_daily_batch.py")
    src = open(path, encoding="utf-8").read()
    for forbidden in ("import requests", "urllib.request", "http.client"):
        assert forbidden not in src, (
            f"submit_daily_batch.py imports {forbidden} — the QuickStatements path "
            "is back, so it needs the lockout check that the other writers have")
