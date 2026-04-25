#!/usr/bin/env python3
"""
template_orchestrator.py
=========================
Cycles through every page in the Template namespace (ns=10), running all
registered per-page operations whose NAMESPACES includes 10.

State file: template_orchestrator.state. See common.py for loop semantics.
"""

import argparse

from shinto_miraheze.orchestrators import common
from shinto_miraheze.orchestrators.ops import (
    duplicate_qids,
    history_offload,
    interlang_consolidate,
    noinclude_wrap,
    strip_html_comments,
    template_mainspace_usage,
    wikidata_link,
)

# history_offload is first and runs in a pre-pass; it is a no-op unless
# ENABLE_HISTORY_OFFLOAD=1 is set in the environment.
# strip_html_comments and interlang_consolidate are PRE_HEAVY light ops:
# they run before history_offload so the cleaned text is what the
# fandom mirror and XML archive capture. interlang_consolidate is a
# no-op unless ENABLE_INTERLANG_CONSOLIDATE=1.
# template_mainspace_usage is a no-op unless ENABLE_TEMPLATE_USAGE_CHECK=1.
OPS = [
    strip_html_comments,
    interlang_consolidate,
    history_offload,
    duplicate_qids,
    noinclude_wrap,
    template_mainspace_usage,
    wikidata_link,
]


def main():
    parser = argparse.ArgumentParser(description="Template per-page cleanup orchestrator.")
    parser.add_argument("--apply", action="store_true", help="Actually save edits.")
    parser.add_argument("--max-edits", type=int, default=100)
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    common.run_orchestrator(
        namespace=10,
        ns_label="template",
        ops=OPS,
        state_name="template_orchestrator",
        apply=args.apply,
        max_edits=args.max_edits,
        run_tag=args.run_tag,
    )


if __name__ == "__main__":
    main()
