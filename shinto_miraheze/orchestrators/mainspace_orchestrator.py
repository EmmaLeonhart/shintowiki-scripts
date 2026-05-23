#!/usr/bin/env python3
"""
mainspace_orchestrator.py
==========================
Cycles through every page in mainspace (ns=0), running all registered
per-page operations whose NAMESPACES includes 0.

State file: mainspace_orchestrator.state (shared across all ops for ns=0).
Processes up to --max-edits pages per run. When the allpages iterator is
exhausted, the state file resets so the next run starts a fresh sweep.

Usage:
    python mainspace_orchestrator.py --run-tag "[[...]]"
    python mainspace_orchestrator.py --apply --run-tag "[[...]]"
"""

import argparse

from shinto_miraheze.orchestrators import common
from shinto_miraheze.orchestrators.ops import (
    categories_to_bottom,
    deleted_qids_in_ill,
    duplicate_qids,
    history_offload,
    ill_category_to_link,
    interlang_consolidate,
    normalize_ill_positional,
    normalize_ill_wikidata,
    remove_defaultsort,
    shikinaisha_talk,
    straggler_link_to_ill,
    strip_afc_templates,
    strip_char_count_cats,
    strip_html_comments,
    untranslated_japanese,
    wikidata_link,
    wikidata_lookup,
)

# history_offload is first and runs in a pre-pass; it is a no-op unless
# ENABLE_HISTORY_OFFLOAD=1 is set in the environment.
# strip_html_comments and interlang_consolidate are PRE_HEAVY light ops:
# they run before history_offload so the cleaned text is what the
# fandom mirror and XML archive capture. interlang_consolidate is a
# no-op unless ENABLE_INTERLANG_CONSOLIDATE=1.
# shikinaisha_talk is also a heavy op — it edits the corresponding talk
# page when the visited mainspace page is in the shikinaisha-generated
# category; returns no-op for every other page.
# straggler_link_to_ill is a PRE_HEAVY light op (placed next to
# ill_category_to_link) that converts raw straggler wikilinks into {{ill}}
# templates via Wikidata resolution; no-op unless
# ENABLE_STRAGGLER_LINK_TO_ILL=1.
OPS = [
    strip_html_comments,
    strip_afc_templates,
    ill_category_to_link,
    straggler_link_to_ill,
    normalize_ill_positional,
    normalize_ill_wikidata,
    interlang_consolidate,
    wikidata_lookup,
    history_offload,
    shikinaisha_talk,
    duplicate_qids,
    remove_defaultsort,
    deleted_qids_in_ill,
    untranslated_japanese,
    strip_char_count_cats,
    wikidata_link,
    categories_to_bottom,
]


def main():
    parser = argparse.ArgumentParser(description="Mainspace per-page cleanup orchestrator.")
    parser.add_argument("--apply", action="store_true", help="Actually save edits.")
    parser.add_argument("--max-edits", type=int, default=100)
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    common.run_orchestrator(
        namespace=0,
        ns_label="mainspace",
        ops=OPS,
        state_name="mainspace_orchestrator",
        apply=args.apply,
        max_edits=args.max_edits,
        run_tag=args.run_tag,
    )


if __name__ == "__main__":
    main()
