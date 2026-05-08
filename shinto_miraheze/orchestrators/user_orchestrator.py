#!/usr/bin/env python3
"""
user_orchestrator.py
====================
Cycles through every page in the User namespace (ns=2). Subject-side
sweep only — the Talk side (ns=3 User talk) lives in talk_orchestrator.

State file: user_orchestrator.state.
"""

import argparse

from shinto_miraheze.orchestrators import common
from shinto_miraheze.orchestrators.ops import (
    duplicate_qids,
    history_offload,
    interlang_consolidate,
    strip_html_comments,
)

OPS = [strip_html_comments, interlang_consolidate, history_offload, duplicate_qids]


def main():
    parser = argparse.ArgumentParser(description="User-namespace cleanup orchestrator.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max-edits", type=int, default=10)
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    common.run_orchestrator(
        namespace=2,
        ns_label="user",
        ops=OPS,
        state_name="user_orchestrator",
        apply=args.apply,
        max_edits=args.max_edits,
        run_tag=args.run_tag,
    )


if __name__ == "__main__":
    main()
