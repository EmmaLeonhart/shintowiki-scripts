#!/usr/bin/env python3
"""
talk_orchestrator.py
====================
Sweeps every Talk-side namespace under one shared edit budget. Talk
pages are low-stakes content (discussion threads, signed posts), so
they get a single combined orchestrator rather than 12 individual ones.

Cycle order: Talk (ns=1), User talk, Project talk, File talk, MediaWiki
talk, Template talk, Help talk, Category talk, GeoJson talk, Module
talk, Item talk, Property talk.

Cursor file `talk_orchestrator_cursor.state` tracks resume point;
combined state file `talk_orchestrator.state` holds every visited title
during the current cycle. Both files are cleared/rewound when the cycle
fully completes.

Modeled on the deleted miscellaneous_orchestrator's cycler design, but
restricted to talk namespaces only — subject-side namespaces each have
their own dedicated orchestrator now.
"""

import argparse
import os

from shinto_miraheze.orchestrators import common
from shinto_miraheze.orchestrators.ops import (
    canonicalize_template_case,
    categories_to_bottom,
    duplicate_qids,
    history_offload,
    ill_category_to_link,
    interlang_consolidate,
    straggler_link_to_ill,
    strip_html_comments,
    wikidata_lookup,
)

# Odd-numbered talk namespaces, swept in order. ns=11 (Template talk) and
# ns=15 (Category talk) are talk-side counterparts of namespaces handled
# elsewhere; they belong to talk too.
TALK_NAMESPACES: list[tuple[int, str]] = [
    (1,   "talk"),
    (3,   "user_talk"),
    (5,   "project_talk"),
    (7,   "file_talk"),
    (9,   "mediawiki_talk"),
    (11,  "template_talk"),
    (13,  "help_talk"),
    (15,  "category_talk"),
    (421, "geojson_talk"),
    (829, "module_talk"),
    (861, "item_talk"),
    (863, "property_talk"),
]

OPS = [strip_html_comments, canonicalize_template_case, ill_category_to_link, straggler_link_to_ill, interlang_consolidate, wikidata_lookup, history_offload, duplicate_qids, categories_to_bottom]

STATE_NAME = "talk_orchestrator"
CURSOR_NAME = "talk_orchestrator_cursor"


def _load_cursor() -> int:
    path = common.state_path(CURSOR_NAME)
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            return int(f.read().strip() or "0") % len(TALK_NAMESPACES)
    except ValueError:
        return 0


def _save_cursor(idx: int) -> None:
    path = common.state_path(CURSOR_NAME)
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(idx % len(TALK_NAMESPACES)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Talk-namespace cleanup orchestrator.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--max-edits",
        type=int,
        default=10,
        help="Shared edit budget across the entire talk sweep.",
    )
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    cursor = _load_cursor()
    remaining = args.max_edits
    state_path = common.state_path(STATE_NAME)

    print(f"Talk sweep starting at cursor={cursor} "
          f"(ns={TALK_NAMESPACES[cursor][0]} "
          f"{TALK_NAMESPACES[cursor][1]}); shared budget={remaining}")

    while remaining > 0 and cursor < len(TALK_NAMESPACES):
        ns, label = TALK_NAMESPACES[cursor]
        print(f"\n{'=' * 60}")
        print(f"Talk orchestrator: ns={ns} ({label}) "
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
            break
        cursor += 1

    if cursor >= len(TALK_NAMESPACES):
        print("\nAll talk namespaces exhausted — clearing shared state and "
              "rewinding cursor to 0.")
        if args.apply:
            common.clear_state(state_path)
        cursor = 0

    if args.apply:
        _save_cursor(cursor)


if __name__ == "__main__":
    main()
