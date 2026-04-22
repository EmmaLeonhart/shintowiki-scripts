#!/usr/bin/env python3
"""
miscellaneous_orchestrator.py
==============================
Cycles through every wikitext namespace that isn't already owned by the
three main orchestrators (mainspace ns=0, template ns=10, category ns=14).
Runs in order: Talk, User, User talk, Project, Project talk, File, File
talk, MediaWiki, MediaWiki talk, Template talk, Help, Help talk, Category
talk, GeoJson talk, Module talk, Item talk, Property talk.

Goal: the same space-efficiency work (history offload, revdel) that runs
on the three main namespaces, applied to everything else — so the XML
export burden is reduced wiki-wide, not just in the three primary
content namespaces.

Each namespace has its own state file (`misc_orchestrator_<ns>.state`)
so progress on one doesn't affect the others. The `--max-edits` budget
is shared across the entire miscellaneous sweep, not per-namespace; once
exhausted, the remaining namespaces are skipped until the next run.

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

from shinto_miraheze.orchestrators import common
from shinto_miraheze.orchestrators.ops import history_offload

# (namespace_id, state_file_label) — processed in this order.
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

OPS = [history_offload]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Miscellaneous-namespace cleanup orchestrator."
    )
    parser.add_argument("--apply", action="store_true", help="Actually save edits.")
    parser.add_argument(
        "--max-edits",
        type=int,
        default=100,
        help="TOTAL edits across all miscellaneous namespaces per run.",
    )
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    remaining = args.max_edits
    for ns, label in MISC_NAMESPACES:
        if args.apply and remaining <= 0:
            print(f"\nEdit budget exhausted; skipping ns={ns} ({label}) and beyond.")
            break
        print(f"\n{'=' * 60}")
        print(f"Miscellaneous orchestrator: ns={ns} ({label}) [budget remaining={remaining}]")
        print(f"{'=' * 60}")
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


if __name__ == "__main__":
    main()
