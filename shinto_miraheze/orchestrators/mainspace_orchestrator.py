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
    deleted_qids_in_ill,
    duplicate_qids,
    history_offload,
    interlang_consolidate,
    remove_defaultsort,
    shikinaisha_talk,
    strip_char_count_cats,
    strip_html_comments,
    untranslated_japanese,
    wikidata_link,
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
OPS = [
    strip_html_comments,
    interlang_consolidate,
    history_offload,
    shikinaisha_talk,
    duplicate_qids,
    remove_defaultsort,
    deleted_qids_in_ill,
    untranslated_japanese,
    strip_char_count_cats,
    wikidata_link,
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
