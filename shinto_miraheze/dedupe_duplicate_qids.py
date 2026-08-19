#!/usr/bin/env python3
"""
dedupe_duplicate_qids.py
========================
Resolves duplicate-QID pairs from ``orchestrators/duplicate_qids.state``
by moving the non-canonical title to a redirect pointing at the canonical
title.

Canonical-selection heuristics (applied in priority order):

  1. QID-stub name  vs  real name  →  real name is canonical.
     A QID-stub name matches ``(Q\\d+)`` in the title, e.g.
     ``Takanono Shrine (Q135040588)``.  The real name wins because it is
     the intended final title.

  2. ASCII / rōmaji title  vs  Japanese-script title  →  ASCII is canonical.
     The wiki's primary language is English-romanised Japanese; the
     kanji/kana pages are duplicates from an earlier import.

Groups that don't fit either rule (two different real names, two QID stubs,
encoding-variant disambiguations, template /doc pairs, etc.) are skipped and
printed as an ambiguous report at the end.

Standard flags: ``--apply`` (default dry-run), ``--max-edits`` (cap per run,
default 50), ``--run-tag`` (wiki edit-summary link back to CI run).
"""

import argparse
import io
import json
import os
import re
import sys
import time
from collections import defaultdict

import mwclient
from wiki_login import login_with_retry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

# Was a module-level hardcoded "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) ..."
# literal shadowing the canonical constant. Two problems: it pinned a version that is now three
# releases stale, and this file is wiki-side only, so the persona was RIGHT and only the
# version was wrong -- which is the quiet half of the same bug: a stale literal drifts
# silently while the canonical constant moves.
from shinto_miraheze.user_agent import USER_AGENT

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DUPES_STATE = os.path.join(SCRIPT_DIR, "orchestrators", "duplicate_qids.state")
DONE_STATE = os.path.join(SCRIPT_DIR, "dedupe_duplicate_qids.state")

JP_RE = re.compile(r"[぀-ヿ一-鿿＀-￯]")
QID_PAREN_RE = re.compile(r"\(Q\d+\)")


def load_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARNING: could not read {path}: {e}")
        return {}


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def build_move_plan(state: dict) -> tuple[list[dict], list[dict]]:
    """Return (auto_moves, ambiguous_groups) from the duplicate-QID state."""
    qid_to_pages: dict[str, list[str]] = defaultdict(list)
    for title, qid in state.items():
        qid_to_pages[qid].append(title)

    auto_moves: list[dict] = []
    ambiguous: list[dict] = []

    for qid, pages in sorted(qid_to_pages.items()):
        if len(pages) < 2:
            continue

        # Template /doc pairs — data-quality artifact, not a real duplicate
        if any("/doc" in p and p.startswith("Template:") for p in pages):
            ambiguous.append({"qid": qid, "pages": pages, "reason": "template/doc pair"})
            continue

        has_qid_stub = [p for p in pages if QID_PAREN_RE.search(p)]
        no_qid_stub = [p for p in pages if not QID_PAREN_RE.search(p)]

        # Rule 1: QID-stub title(s) + exactly one real-named title
        if has_qid_stub and len(no_qid_stub) == 1:
            canonical = no_qid_stub[0]
            for non_canon in has_qid_stub:
                auto_moves.append({
                    "qid": qid,
                    "from": non_canon,
                    "to": canonical,
                    "reason": "QID-stub → real name",
                })
            continue

        has_jp = [p for p in pages if JP_RE.search(p)]
        no_jp = [p for p in pages if not JP_RE.search(p)]

        # Rule 2: ASCII title(s) vs Japanese-script title(s) — no QID stubs
        if has_jp and len(no_jp) == 1 and not has_qid_stub:
            canonical = no_jp[0]
            for non_canon in has_jp:
                auto_moves.append({
                    "qid": qid,
                    "from": non_canon,
                    "to": canonical,
                    "reason": "JP-script → ASCII/rōmaji",
                })
            continue

        # Everything else is ambiguous
        reason = "both QID stubs" if not no_qid_stub and has_qid_stub else "unclear canonical"
        ambiguous.append({"qid": qid, "pages": pages, "reason": reason})

    return auto_moves, ambiguous


def perform_move(site, src: str, dst: str, run_tag: str, apply: bool) -> str:
    """Move src → dst (leave redirect). Returns: 'moved', 'skipped', or 'error:<msg>'."""
    try:
        src_page = site.pages[src]
    except Exception as e:
        return f"error:fetch src: {e}"

    if not src_page.exists:
        return "skipped:src missing"

    src_text = src_page.text()
    if re.match(r"^\s*#redirect\b", src_text, re.IGNORECASE):
        return "skipped:src already redirect"

    try:
        dst_page = site.pages[dst]
        dst_exists = dst_page.exists
    except Exception as e:
        return f"error:fetch dst: {e}"

    if dst_exists:
        dst_text = dst_page.text()
        if re.match(r"^\s*#redirect\b", dst_text, re.IGNORECASE):
            return "skipped:dst is a redirect (title collision)"
        return "skipped:dst exists as real page"

    summary = f"Bot: redirect duplicate QID title to canonical page {run_tag}".strip()

    if not apply:
        return "dry:would move"

    try:
        src_page.move(dst, reason=summary, no_redirect=False)
        return "moved"
    except Exception as e:
        return f"error:{e}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Actually perform moves (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=50,
                        help="Maximum page moves per run (default 50).")
    parser.add_argument("--run-tag", required=True,
                        help="Edit-summary suffix linking back to the CI run.")
    args = parser.parse_args()

    state = load_json(DUPES_STATE)
    if not state:
        print(f"No state loaded from {DUPES_STATE} — nothing to do.")
        return

    done: dict = load_json(DONE_STATE)  # {"from_title": "to_title"}
    print(f"Loaded {len(state)} tracked titles; {len(done)} moves already recorded.")

    auto_moves, ambiguous = build_move_plan(state)
    pending = [m for m in auto_moves if m["from"] not in done]

    print(f"Move plan: {len(auto_moves)} total auto-picks, "
          f"{len(pending)} pending (not yet done), "
          f"{len(ambiguous)} ambiguous (skipped).")
    print()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.connection.timeout = 120
    login_with_retry(site, USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")
    print()

    moved = skipped = errors = 0
    budget = args.max_edits

    for i, move in enumerate(pending, 1):
        if moved >= budget:
            print(f"Budget of {budget} moves reached, stopping.")
            break

        src, dst, reason, qid = move["from"], move["to"], move["reason"], move["qid"]
        print(f"[{i}/{len(pending)}] {reason} | {qid}")
        print(f"  MOVE  {repr(src)}")
        print(f"    →   {repr(dst)}")

        result = perform_move(site, src, dst, args.run_tag, args.apply)
        print(f"  → {result}")

        if result.startswith("moved") or result.startswith("dry"):
            if result.startswith("moved"):
                moved += 1
                done[src] = dst
            print()
            time.sleep(THROTTLE)
        elif result.startswith("skipped"):
            skipped += 1
            done[src] = f"skipped:{result}"
            print()
        else:
            errors += 1
            print()

    if args.apply and (moved or skipped):
        save_json(DONE_STATE, done)
        print(f"Saved {DONE_STATE} ({len(done)} entries).")

    print()
    print("=" * 60)
    print(f"Moves performed:  {moved}")
    print(f"Skipped:          {skipped}")
    print(f"Errors:           {errors}")
    print(f"Budget remaining: {max(0, budget - moved)}")
    print()
    if ambiguous:
        print(f"Ambiguous groups not auto-resolved ({len(ambiguous)}):")
        for g in ambiguous:
            print(f"  {g['qid']} ({g['reason']}):")
            for p in g["pages"]:
                print(f"    - {p}")


if __name__ == "__main__":
    main()
