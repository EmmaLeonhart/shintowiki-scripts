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
from shinto_miraheze.orchestrators.ops import history_offload, wikidata_link

# history_offload is first and runs in a pre-pass; it is a no-op unless
# ENABLE_HISTORY_OFFLOAD=1 is set in the environment.
OPS = [history_offload, wikidata_link]


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
