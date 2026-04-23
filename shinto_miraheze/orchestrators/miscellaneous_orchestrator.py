#!/usr/bin/env python3
"""
miscellaneous_orchestrator.py
==============================
Cycles through every wikitext namespace that isn't already owned by the
three main orchestrators (mainspace ns=0, template ns=10, category ns=14).
Canonical order: Talk (ns=1), User, User talk, Project, Project talk,
File, File talk, MediaWiki, MediaWiki talk, Template talk, Help, Help
talk, Category talk, GeoJson talk, Module talk, Item talk, Property talk.

Goal: the same space-efficiency work (history offload, revdel) that runs
on the three main namespaces, applied to everything else — so the XML
export burden is reduced wiki-wide, not just in the three primary
content namespaces.

Budgeting (matches the three main orchestrators):
  * `--max-edits` is a single shared budget across the whole sweep.
  * ONE combined state file `misc_orchestrator.state` holds every title
    visited during the current cycle (titles carry namespace prefixes,
    so there are no collisions). This is a bit chaotic but keeps us
    from repeating work as we move between namespaces.
  * `misc_orchestrator_cursor.state` tracks which namespace to resume.
  * Each run picks up at the cursor and tries to spend up to `--max-edits`
    edits. Most runs will only hit one namespace (100 edits × 2.5s
    throttle ≈ 4 min of edits + walk time).
  * When the current namespace is exhausted AND budget remains, the
    cursor advances and the sweep continues into the next namespace
    under the same state file.
  * When the final namespace in the list is exhausted, the cycle is
    complete: state is cleared and cursor resets to 0.

Previously this orchestrator gave each namespace its own 100-edit cap
and its own state file, so every run paid 17× the walk/edit cost of the
three main orchestrators (~2h vs ~11min).

Omitted namespaces (wikitext edits don't apply to their content model):
  * -2 Media, -1 Special     (virtual, not real pages)
  *  420 GeoJson              (JSON content)
  *  828 Module               (Lua/Scribunto)
  *  860 Item, 862 Property   (Wikibase entities, JSON)

Usage:
    python -m shinto_miraheze.orchestrators.miscellaneous_orchestrator \\
        --apply --max-edits 100 --run-tag "[[...]]"
"""

import argparse
import os

from shinto_miraheze.orchestrators import common
from shinto_miraheze.orchestrators.ops import (
    duplicate_qids,
    history_offload,
    interlang_consolidate,
)

# (namespace_id, state_file_label) — swept in this exact order starting
# from the persisted cursor. ns=1 (Talk = mainspace talk pages) leads.
MISC_NAMESPACES: list[tuple[int, str]] = [
    (1,   "talk"),
    (2,   "user"),
    (3,   "user_talk"),
    (4,   "project"),
    (5,   "project_talk"),
    (6,   "file"),
    (7,   "file_talk"),
    (8,   "mediawiki"),
    (9,   "mediawiki_talk"),
    (11,  "template_talk"),
    (12,  "help"),
    (13,  "help_talk"),
    (15,  "category_talk"),
    (421, "geojson_talk"),
    (829, "module_talk"),
    (861, "item_talk"),
    (863, "property_talk"),
]

OPS = [history_offload, duplicate_qids, interlang_consolidate]

STATE_NAME = "misc_orchestrator"
CURSOR_NAME = "misc_orchestrator_cursor"


def _load_cursor() -> int:
    path = common.state_path(CURSOR_NAME)
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip() or "0") % len(MISC_NAMESPACES)
    except ValueError:
        return 0


def _save_cursor(idx: int) -> None:
    path = common.state_path(CURSOR_NAME)
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(idx % len(MISC_NAMESPACES)))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Miscellaneous-namespace cleanup orchestrator."
    )
    parser.add_argument("--apply", action="store_true", help="Actually save edits.")
    parser.add_argument(
        "--max-edits",
        type=int,
        default=100,
        help="Shared edit budget across the entire sweep (all namespaces combined).",
    )
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    cursor = _load_cursor()
    remaining = args.max_edits
    state_path = common.state_path(STATE_NAME)

    print(f"Misc sweep starting at cursor={cursor} "
          f"(ns={MISC_NAMESPACES[cursor][0]} "
          f"{MISC_NAMESPACES[cursor][1]}); shared budget={remaining}")

    while remaining > 0 and cursor < len(MISC_NAMESPACES):
        ns, label = MISC_NAMESPACES[cursor]
        print(f"\n{'=' * 60}")
        print(f"Miscellaneous orchestrator: ns={ns} ({label}) "
              f"[remaining budget={remaining}]")
        print(f"{'=' * 60}")
        edited, exhausted = common.run_orchestrator(
            namespace=ns,
            ns_label=label,
            ops=OPS,
            state_name=STATE_NAME,
            apply=args.apply,
            max_edits=remaining,
            run_tag=args.run_tag,
            clear_on_exhaust=False,
        )
        remaining -= edited
        if not exhausted:
            # Budget hit before finishing this namespace — stay on it next run.
            break
        cursor += 1

    # Full cycle complete: clear shared state and rewind cursor.
    if cursor >= len(MISC_NAMESPACES):
        print("\nAll misc namespaces exhausted — clearing shared state and "
              "rewinding cursor to 0.")
        if args.apply:
            common.clear_state(state_path)
        cursor = 0

    if args.apply:
        _save_cursor(cursor)


if __name__ == "__main__":
    main()
