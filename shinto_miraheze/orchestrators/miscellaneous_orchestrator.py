#!/usr/bin/env python3
"""
miscellaneous_orchestrator.py
==============================
Cycles through every wikitext namespace that isn't already owned by the
three main orchestrators (mainspace ns=0, template ns=10, category ns=14).
Visits: Talk, User, User talk, Project, Project talk, File, File talk,
MediaWiki, MediaWiki talk, Template talk, Help, Help talk, Category talk,
GeoJson talk, Module talk, Item talk, Property talk.

Goal: the same space-efficiency work (history offload, revdel) that runs
on the three main namespaces, applied to everything else — so the XML
export burden is reduced wiki-wide, not just in the three primary
content namespaces.

Budgeting: `--max-edits` is a SHARED budget across the whole sweep (matches
the other three orchestrators). Each namespace has its own state file
(`misc_orchestrator_<ns>.state`), and the starting namespace rotates each
run via `misc_orchestrator_cursor.state` — so if the budget gets spent
early, different namespaces lead on the next run. No namespace starves.

This was previously per-namespace (100 edits × 17 namespaces = up to 1700
edits + 17 full iter_allpages walks per run), which made this orchestrator
take ~2h while the three main orchestrators each took ~11 min.

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

# (namespace_id, state_file_label) — rotated each run, but iterated in
# this canonical order starting from the persisted cursor.
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

    start = _load_cursor()
    ordered = MISC_NAMESPACES[start:] + MISC_NAMESPACES[:start]
    print(f"Misc sweep starting at index {start} "
          f"(ns={ordered[0][0]} {ordered[0][1]}); shared budget={args.max_edits}")

    remaining = args.max_edits
    for ns, label in ordered:
        print(f"\n{'=' * 60}")
        print(f"Miscellaneous orchestrator: ns={ns} ({label}) "
              f"[remaining budget={remaining}]")
        print(f"{'=' * 60}")
        if remaining <= 0:
            print("Global edit budget exhausted; skipping remaining namespaces.")
            break
        edited = common.run_orchestrator(
            namespace=ns,
            ns_label=label,
            ops=OPS,
            state_name=f"misc_orchestrator_{ns}",
            apply=args.apply,
            max_edits=remaining,
            run_tag=args.run_tag,
        )
        remaining -= edited

    # Advance cursor so next run leads with a different namespace — this
    # is what prevents the first namespace in the list from hogging the
    # shared budget every run.
    if args.apply:
        _save_cursor(start + 1)


if __name__ == "__main__":
    main()
