#!/usr/bin/env python3
"""
strip_ns8_offload_banners.py
=============================
Removes the history_offload banner comment from every MediaWiki-namespace
(ns8) page. 113/176 ns8 pages carry it (scan 2026-07-07) from the era before
ns8 was excluded from the orchestrators; on interface messages the comment
renders into the UI (Sitenotice, Histlegend, cite link labels, …), which is
the corruption Emma flagged on [[Open questions]] 2026-07-07.

Strips ONLY the leading banner comment (same logic as
orchestrators/ops/history_offload._strip_existing_banner) — nothing else on
these sensitive pages is touched. Idempotent: no-ops once the banners are
gone. ns8 stays excluded from all orchestrators; the offload op itself has
been inert since the 2026-06-01 cutoff, so there is no reintroduction path.

Usage: strip_ns8_offload_banners.py [--apply] [--max-edits N] [--run-tag TAG]
"""
import argparse
import io
import os
import sys
import time

import mwclient

THROTTLE = 2.5
COMMENT_MARKER = "<!-- History offloaded:"


def strip_banner(text: str):
    """(new_text or None). Same shape as history_offload's stripper, but only
    returns a change when a well-formed leading banner exists."""
    if not text or not text.startswith(COMMENT_MARKER):
        return None
    end = text.find("-->", len(COMMENT_MARKER))
    if end == -1:
        return None  # malformed; leave alone
    rest_start = end + len("-->")
    if rest_start < len(text) and text[rest_start] == "\n":
        rest_start += 1
    return text[rest_start:]


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-edits", type=int, default=200)
    ap.add_argument("--run-tag", default="")
    args = ap.parse_args()

    site = mwclient.Site("shinto.miraheze.org", path="/w/",
                         clients_useragent="EmmaBot strip_ns8_offload_banners/1.0 "
                                           "(immanuelleleonhart@gmail.com)")
    user = os.environ.get("WIKI_USERNAME")
    password = os.environ.get("WIKI_PASSWORD")
    if args.apply:
        if not (user and password):
            raise SystemExit("WIKI_USERNAME/WIKI_PASSWORD required with --apply")
        site.login(user, password)

    summary = "Strip history-offload banner comment from interface message (ns8 UI cleanup)"
    if args.run_tag:
        summary += f" {args.run_tag}"

    edits = 0
    for page in site.allpages(namespace=8):
        if edits >= args.max_edits:
            print(f"max-edits {args.max_edits} reached; stopping")
            break
        text = page.text()
        new = strip_banner(text)
        if new is None:
            continue
        if args.apply:
            page.save(new, summary=summary)
            time.sleep(THROTTLE)
        edits += 1
        print(f"{'EDIT' if args.apply else 'DRY'} {page.name}")
    print(f"Done. {'Edits' if args.apply else 'Would edit'}: {edits}")


if __name__ == "__main__":
    main()
