"""The shinto.miraheze lockout must gate steps that EDIT the wiki, and only those.

`wiki_edit_allowed.py` exists to stop the bot hammering a wiki that is refusing
it. Applied to a step that never touches the wiki, it does something else
entirely: it silently stops local work for as long as the wiki is unavailable.

That happened. `collect_category_translations.py` imports no `mwclient`, opens no
site, saves no page and needs no credentials — `--apply` means "append rows to
`category_moves.csv` and delete the finished work-files", entirely local. It was
gated on the lockout anyway, and because it also runs only on the 1st of the
month, a lockout falling on the 1st meant that month's cloud answers were never
collected at all. Miraheze has been locked since 2026-09-06.

The distinction this pins, both directions:

* `move_categories` CONSUMES the CSV and does edit the wiki — it keeps its gate.
* the collector that FILLS the CSV does not — it must not have one.

Collecting during a lockout is strictly better than not: the CSV is simply ready
when the wiki reopens.
"""

import os
import re

WORKFLOW = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".github", "workflows", "wiki-cleanup.yml",
)

GATE = "steps.lockout.outputs.locked != 'true'"


def _step_condition(name_fragment):
    """The `if:` line belonging to the step whose name contains the fragment."""
    with open(WORKFLOW, encoding="utf-8") as fh:
        lines = fh.readlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("- name:") and name_fragment in line:
            for follow in lines[i + 1:i + 4]:
                if follow.lstrip().startswith("if:"):
                    return follow.strip()
            return ""
    raise AssertionError(f"no step named like {name_fragment!r} in {WORKFLOW}")


def test_the_local_only_collector_is_not_lockout_gated():
    cond = _step_condition("cat-translation: collect RAG answers")
    assert GATE not in cond, (
        "collect_category_translations.py touches no wiki — gating it on the wiki "
        "lockout stops local collection for the whole month whenever Miraheze is "
        f"down on the 1st. Condition was: {cond}")


def test_committing_that_csv_is_not_lockout_gated_either():
    cond = _step_condition("Commit: category_moves.csv")
    assert GATE not in cond, (
        "committing a local CSV to git has nothing to do with whether the wiki "
        f"accepts edits. Condition was: {cond}")


def test_the_csv_generator_is_not_lockout_gated_either():
    """The other half of the same monthly pair, found by sweeping all 52 gated
    steps rather than by stumbling on it. Verified read-only: a single
    `requests.get`, no POST, no token, no mwclient, and its docstring says
    "--run-tag accepted for template consistency (unused — no wiki write)"."""
    cond = _step_condition("Deprecated: generate_category_translation_moves")
    assert GATE not in cond, (
        "generate_category_translation_moves.py reads pages and writes a local CSV; "
        f"gating it wastes the monthly slot whenever the wiki is down. Was: {cond}")


def test_the_step_that_actually_edits_the_wiki_keeps_its_gate():
    """The other direction. move_categories moves pages on shinto.miraheze; if
    this ever loses its gate the bot edits straight through a lockout."""
    cond = _step_condition("Deprecated: move_categories")
    assert GATE in cond, (
        f"move_categories edits the wiki and MUST stay gated. Condition was: {cond}")


def test_the_collector_still_has_no_way_to_edit_the_wiki():
    """The reason the gate was removed. If this script ever grows a wiki client,
    the gate has to come back — so the claim is asserted rather than remembered."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("collect_category_translations.py",
                 "generate_category_translation_moves.py"):
        src = open(os.path.join(root, "shinto_miraheze", name), encoding="utf-8").read()
        for forbidden in ("mwclient", "WIKI_PASSWORD", "login_with_retry",
                          ".save(", "requests.post"):
            assert forbidden not in src, (
                f"{forbidden} appeared in {name} — it can now reach the wiki, so "
                "restore the lockout gate on its workflow step")
