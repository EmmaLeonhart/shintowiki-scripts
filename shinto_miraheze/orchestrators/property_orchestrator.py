#!/usr/bin/env python3
"""
property_orchestrator.py
========================
Cycles through every page in the Property namespace (ns=862). Content is
a Wikibase Property entity (JSON), not wikitext — only history_offload
runs.

State file: property_orchestrator.state.
"""

import argparse

from shinto_miraheze.orchestrators import common
from shinto_miraheze.orchestrators.ops import (
    canonicalize_template_case,
    duplicate_qids,
    history_offload,
    interlang_consolidate,
    strip_html_comments,
)

OPS = [strip_html_comments, canonicalize_template_case, interlang_consolidate, history_offload, duplicate_qids]


def main():
    parser = argparse.ArgumentParser(description="Property-namespace cleanup orchestrator.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max-edits", type=int, default=10)
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    common.run_orchestrator(
        namespace=862,
        ns_label="property",
        ops=OPS,
        state_name="property_orchestrator",
        apply=args.apply,
        max_edits=args.max_edits,
        run_tag=args.run_tag,
    )


if __name__ == "__main__":
    main()
