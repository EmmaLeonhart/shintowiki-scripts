#!/usr/bin/env python3
"""
miscellaneous_orchestrator.py
==============================
Cycles through every subject-side namespace that isn't already owned by
the three main orchestrators (mainspace ns=0, template ns=10,
category ns=14).
Canonical order: User (ns=2), Project, File, MediaWiki, Help, GeoJson,
Module, Item, Property.

Talk namespaces (odd-numbered: ns=1, 3, 5, 7, 9, 11, 13, 15, 421, 829,
861, 863) are intentionally excluded — the orchestrator only runs on
subject-side namespaces.

GeoJson (420), Module (828), Item (860), and Property (862) carry
non-wikitext content, so only the history_offload op runs on them
(and it skips the wikitext banner for those — see
history_offload.NON_WIKITEXT_NAMESPACES). The wikitext ops
(duplicate_qids, interlang_consolidate) self-exclude via their own
NAMESPACES tuples.

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

Omitted namespaces:
  * -2 Media, -1 Special     (virtual, not real pages)
  * All odd-numbered talk namespaces (subject-side sweep only)

Included non-wikitext namespaces (history_offload only; no banner):
  *  420 GeoJson              (JSON content)
  *  828 Module               (Lua/Scribunto)
  *  860 Item, 862 Property   (Wikibase entities, JSON)

Usage:
    python -m shinto_miraheze.orchestrators.miscellaneous_orchestrator \\
        --apply --max-edits 100 --run-tag "[[...]]"
"""

import argparse
import glob
import os

from shinto_miraheze.orchestrators import common
from shinto_miraheze.orchestrators.ops import (
    duplicate_qids,
    history_offload,
    interlang_consolidate,
)

# (namespace_id, state_file_label) — swept in this exact order starting
# from the persisted cursor. Only even-numbered (subject-side) namespaces;
# talk namespaces are excluded. The last four carry non-wikitext content
# (JSON / Lua / Wikibase) — only history_offload runs on them.
MISC_NAMESPACES: list[tuple[int, str]] = [
    (2,   "user"),
    (4,   "project"),
    (6,   "file"),
    (8,   "mediawiki"),
    (12,  "help"),
    (420, "geojson"),
    (828, "module"),
    (860, "item"),
    (862, "property"),
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


def _migrate_legacy_per_namespace_state() -> None:
    """One-time merge of legacy per-namespace misc state files.

    The previous version wrote misc_orchestrator_<ns>.state (one per
    namespace). The new version uses a single misc_orchestrator.state.
    Any legacy files we find get their titles appended (de-duped) into
    the combined file, then the legacy files are deleted so titles
    already processed in the current cycle aren't redone.
    """
    combined = common.state_path(STATE_NAME)
    legacy_dir = os.path.dirname(combined)
    # Match misc_orchestrator_<number>.state but NOT misc_orchestrator.state
    # or misc_orchestrator_cursor.state.
    legacy_paths = [
        p for p in glob.glob(os.path.join(legacy_dir, "misc_orchestrator_*.state"))
        if os.path.basename(p) != f"{CURSOR_NAME}.state"
        and os.path.basename(p).removeprefix("misc_orchestrator_").removesuffix(".state").isdigit()
    ]
    if not legacy_paths:
        return

    existing = common.load_state(combined)
    merged = set(existing)
    for path in legacy_paths:
        merged |= common.load_state(path)

    new_titles = merged - existing
    if new_titles:
        with open(combined, "a", encoding="utf-8") as f:
            for title in sorted(new_titles):
                f.write(title + "\n")

    for path in legacy_paths:
        try:
            os.remove(path)
        except OSError as e:
            print(f"WARN: could not delete legacy state file {path}: {e}")

    print(
        f"Migrated {len(legacy_paths)} legacy per-namespace state file(s) "
        f"into {os.path.basename(combined)} "
        f"(+{len(new_titles)} new titles, total {len(merged)})."
    )


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

    _migrate_legacy_per_namespace_state()
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
