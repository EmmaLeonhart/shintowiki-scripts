#!/usr/bin/env python3
"""Relink the `{{ill|…|qid=DELETED_QID}}` templates whose target is actually a LIVE
Wikidata item (a duplicate, not a deletion to recreate) — edit them in-place in the
git_synced/ page copies so the ill points at the existing item. Emma 2026-07-06:
recreation is off (jawiki-sitelink items already have items; redlink items have no
anchor), so fix the duplicates by article editing here.

Source of truth: every recreate-deleted-wikidata/items/Q*.json that carries
``enrichment.possible_existing`` (the dedup passes). For each such target, find its
`{{ill|…DELETED_QID…}}` on each host page's git_synced/<title>.wiki (matched by the
ja langlink or English label) and rewrite ``qid=DELETED_QID`` → ``qid=<live QID>``,
dropping the now-redundant ``dd=`` provenance param. The git_synced sync (repo-wins)
pushes the edit to the wiki. Dry-run by default; ``--apply`` writes the files.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.title_filename import title_to_filename  # noqa: E402

import argparse
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ITEMS = os.path.join(HERE, "items")
GIT_SYNCED = os.path.join(REPO, "git_synced")
_ILL = re.compile(r"\{\{\s*ill\s*\|([^{}]*)\}\}", re.IGNORECASE)




def targets():
    """[(ja, en, live_qid, [host_pages])] for every duplicate-flagged candidate."""
    out = []
    for f in sorted(glob.glob(os.path.join(ITEMS, "Q*.json"))):
        r = json.load(open(f, encoding="utf-8"))
        pe = (r.get("enrichment") or {}).get("possible_existing")
        if not pe:
            continue
        fa = r.get("fandom") or {}
        out.append((
            (fa.get("langlinks") or {}).get("ja") or "",
            r.get("recovered_label") or fa.get("label") or "",
            pe[0].get("qid"),
            fa.get("host_pages") or [],
        ))
    return out


def relink_ill(inner, live_qid):
    """Rewrite one ill's inner: qid=DELETED_QID → qid=<live>, drop dd=. Pure."""
    new = re.sub(r"(qid\s*=\s*)DELETED_QID", r"\g<1>" + live_qid, inner)
    new = re.sub(r"\s*\|\s*dd\s*=\s*Q\d+", "", new)
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the files (default: dry-run)")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    edits = 0
    for ja, en, live, hosts in targets():
        if not live:
            continue
        for host in hosts:
            path = os.path.join(GIT_SYNCED, title_to_filename(host))
            if not os.path.exists(path):
                print(f"  [skip] no git_synced file for host [[{host}]]")
                continue
            text = open(path, encoding="utf-8").read()
            changed = text

            def _sub(m):
                inner = m.group(1)
                if "DELETED_QID" not in inner:
                    return m.group(0)
                if (ja and ja in inner) or (en and en in inner):
                    return "{{ill|" + relink_ill(inner, live) + "}}"
                return m.group(0)

            changed = _ILL.sub(_sub, text)
            if changed != text:
                edits += 1
                print(f"  RELINK {en} ({ja}) → {live}  in [[{host}]]")
                if args.apply:
                    open(path, "w", encoding="utf-8", newline="\n").write(changed)
    print(f"\n{'APPLIED' if args.apply else 'DRY-RUN'}: {edits} ill(s) relinked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
