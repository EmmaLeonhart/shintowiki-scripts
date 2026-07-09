#!/usr/bin/env python3
"""Rebuild only the "Duplicate Properties on Shikinai Ronsha" section of the
shrine-ranking page, in place.

`generate_modern_shrine_ranking_qualifiers.py` rebuilds the whole page, which
also regenerates every atomic QuickStatements `.txt` file — fine in CI, wrong to
run on a dev box where those files would be committed half-built. This refreshes
just the review tables, so the counts and the per-item detail can be re-queried
as fast as Emma fixes items instead of once a day.

Rewrites both `modern-quickstatements/_site/index.html` and the copy published
at `_site/shrine-ranking.html` (the workflow keeps them identical).

    python refresh_duplicates_section.py [--open]
"""
import argparse
import io
import os
import sys
import webbrowser

import generate_modern_shrine_ranking_qualifiers as gen

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TARGETS = [
    os.path.join(HERE, "_site", "index.html"),
    os.path.join(ROOT, "_site", "shrine-ranking.html"),
]

START = "  <h2>Duplicate Properties on Shikinai Ronsha</h2>"
# The section runs to the page's closing rule.
END = "\n  <hr>"


def splice(html, section):
    start = html.index(START)
    end = html.index(END, start)
    return html[:start] + section.lstrip("\n") + html[end:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", action="store_true", help="open the refreshed page in a browser")
    args = ap.parse_args()

    section = gen.generate_duplicates_section()

    written = []
    for path in TARGETS:
        if not os.path.exists(path):
            print(f"skip (missing): {path}")
            continue
        html = io.open(path, encoding="utf-8").read()
        if START not in html:
            print(f"skip (no duplicates section): {path}")
            continue
        io.open(path, "w", encoding="utf-8", newline="\n").write(splice(html, section))
        print(f"refreshed: {path}")
        written.append(path)

    if not written:
        print("nothing refreshed", file=sys.stderr)
        return 1
    if args.open:
        webbrowser.open("file:///" + written[-1].replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
