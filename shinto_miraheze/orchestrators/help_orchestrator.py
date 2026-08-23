#!/usr/bin/env python3
"""
help_orchestrator.py
====================
Cycles through every page in the Help namespace (ns=12). Subject-side
sweep only.

State file: help_orchestrator.state.
"""

import argparse

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

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

OPS = [strip_html_comments, canonicalize_template_case, ill_category_to_link, straggler_link_to_ill, interlang_consolidate, wikidata_lookup, history_offload, duplicate_qids, categories_to_bottom]


def main():
    parser = argparse.ArgumentParser(description="Help-namespace cleanup orchestrator.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max-edits", type=int, default=10)
    parser.add_argument("--run-tag", required=True)
    args = parser.parse_args()

    common.run_orchestrator(
        namespace=12,
        ns_label="help",
        ops=OPS,
        state_name="help_orchestrator",
        apply=args.apply,
        max_edits=args.max_edits,
        run_tag=args.run_tag,
    )


if __name__ == "__main__":
    main()
