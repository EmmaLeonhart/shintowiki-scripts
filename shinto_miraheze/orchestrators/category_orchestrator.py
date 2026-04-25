#!/usr/bin/env python3
"""
category_orchestrator.py
=========================
Cycles through every page in the Category namespace (ns=14), running all
registered per-page operations whose NAMESPACES includes 14.

State file: category_orchestrator.state. See common.py for loop semantics.
"""

import argparse

from shinto_miraheze.orchestrators import common
from shinto_miraheze.orchestrators.ops import (
    duplicate_qids,
    history_offload,
    interlang_consolidate,
    normalize_category_page,
    remove_legacy_cat_templates,
    strip_html_comments,
    wikidata_link,
)

# history_offload is first and runs in a pre-pass; it is a no-op unless
# ENABLE_HISTORY_OFFLOAD=1 is set in the environment.
# strip_html_comments and interlang_consolidate are PRE_HEAVY light ops:
# they run before history_offload so the cleaned text is what the
# fandom mirror and XML archive capture. interlang_consolidate is a
# no-op unless ENABLE_INTERLANG_CONSOLIDATE=1.
# remove_legacy_cat_templates runs before normalize_category_page so the
# stripped templates don't end up in the normalized output.
OPS = [
    strip_html_comments,
    interlang_consolidate,
    history_offload,
    duplicate_qids,
    remove_legacy_cat_templates,
    normalize_category_page,
    wikidata_link,
]


def main():
    parser = argparse.ArgumentParser(description="Category per-page cleanup orchestrator.")
    parser.add_argument("--apply", action="store_true", help="Actually save edits.")
    parser.add_argument("--max-edits", type=int, default=100)
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    common.run_orchestrator(
        namespace=14,
        ns_label="category",
        ops=OPS,
        state_name="category_orchestrator",
        apply=args.apply,
        max_edits=args.max_edits,
        run_tag=args.run_tag,
    )


if __name__ == "__main__":
    main()
