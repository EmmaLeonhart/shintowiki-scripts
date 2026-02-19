#!/usr/bin/env python3
"""
cat_move_scanner.py
───────────────────
For every bare title in pages.txt …

  1. Undelete the matching Category:<title>  (if possible / needed)
  2. Look through its logevents; if it was ever *moved*, write a line to
     commands.txt:

       py merge.py "Category:OLD" "Category:NEW"

     (NEW = most-recent ‘target_title’ in the move log)

Nothing is written for categories that have never been moved.
"""

# ── BASIC CONFIG ─────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"   # domain
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.4          # seconds between edits / API posts

PAGES_TXT  = "pages.txt"
CMD_TXT    = "commands_2.txt"

# ── imports ─────────────────────────────────────────────────
import os, time, json, mwclient
from mwclient.errors import APIError
from pathlib import Path

# ── helpers ────────────────────────────────────────────────
def load_titles(path:str) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

def try_undelete(site, full_title:str):
    """Attempt to undelete; ignore all errors (page already exists, no rights…)."""
    try:
        site.api(
            "undelete",
            title = full_title,
            reason = "Bot: restore to inspect move log",
            token  = site.get_token("csrf")
        )
        time.sleep(THROTTLE)
    except APIError as e:
        # cantundelete = nothing to undelete / no rights / already restored
        if e.code not in ("cantundelete", "permissiondenied"):
            print(f"  ! undelete failed on {full_title}: {e.code}")

def latest_move_target(site, full_title:str) -> str|None:
    """Return newest ‘target_title’ from move log – or None."""
    data = site.api(
        action="query",
        list="logevents",
        letitle=full_title,
        leaction="move/move",
        lelimit="max",
        format="json",
        leprop="timestamp|details"
    )
    moves = data.get("query", {}).get("logevents", [])
    if not moves:
        return None
    # logevents are newest→oldest already, so first entry is latest
    tgt = moves[0].get("params", {}).get("target_title")
    return tgt

# ── main ───────────────────────────────────────────────────
def main():
    if not Path(PAGES_TXT).exists():
        raise SystemExit(f"{PAGES_TXT} not found")

    titles = load_titles(PAGES_TXT)

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in – {len(titles)} categories to check")

    out_lines = []

    for bare in titles:
        full = f"Category:{bare}"
        print(f"→ {full}")

        try_undelete(site, full)
        dest = latest_move_target(site, full)

        if dest:
            line = f'py merge.py "{full}" "{dest}"'
            out_lines.append(line)
            print(f"   • move found → {dest}")
        else:
            print("   • never moved")

    if out_lines:
        with open(CMD_TXT, "a", encoding="utf-8") as fh:   # append; change to "w" to overwrite
            fh.write("\n".join(out_lines) + "\n")
        print(f"\nWrote {len(out_lines)} command(s) to {CMD_TXT}")
    else:
        print("\nNo moved categories detected; commands.txt unchanged")

if __name__ == "__main__":
    main()
