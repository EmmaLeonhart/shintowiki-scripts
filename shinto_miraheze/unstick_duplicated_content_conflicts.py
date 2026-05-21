#!/usr/bin/env python3
"""
unstick_duplicated_content_conflicts.py
========================================
One-shot unstick for the 135 (and counting) pages in
``[[Category:Pages with duplicated content]]`` that ``sync_duplicated_content.py``
has been permanently skipping with ``CONFLICT`` because both sides
diverged from the last known base.

For every ``duplicated_content/<title>.wiki`` file:

1. Fetch the current wiki revision of that title.
2. Build a merged body: wiki text, then a separator, then local text.
3. Ensure ``[[Category:Pages with duplicated content]]`` is present in
   the merged body (so the page legitimately stays in the queue for
   normal Claude-driven dedup).
4. Push the merged body to the wiki (so wiki == local after this step).
5. Write the merged body to the local file.
6. Update ``sync_duplicated_content.state`` so ``base.revid`` = the
   wiki's new revid and ``base.sha`` = sha1(merged). Next sync sees
   wiki == local and skips the page cleanly. Normal queue processing
   takes over from there.

Standard flags: ``--apply`` (default dry-run), ``--max-edits``,
``--run-tag``. Requires ``WIKI_USERNAME`` + ``WIKI_PASSWORD`` env vars.
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

CATEGORY = "Pages with duplicated content"
CAT_TAG = f"[[Category:{CATEGORY}]]"
CAT_RE = re.compile(r"\[\[\s*Category\s*:\s*Pages with duplicated content\s*\]\]", re.IGNORECASE)

USER_AGENT = "DuplicatedContentUnstickBot/1.0 (User:EmmaBot; shinto.miraheze.org)"

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WIKI_DIR = REPO_ROOT / "duplicated_content"
STATE_FILE = SCRIPT_DIR / "sync_duplicated_content.state"

_FORBIDDEN = set('<>:"/\\|?*')

SEPARATOR = "\n\n<!-- ─── unstick merge: wiki content above, local content below ─── -->\n\n"


def title_to_filename(title: str) -> str:
    out = []
    for c in title:
        if c in _FORBIDDEN or c == "%":
            out.append(f"%{ord(c):02X}")
        else:
            out.append(c)
    return "".join(out) + ".wiki"


def filename_to_title(filename: str) -> str:
    name = filename[:-5] if filename.endswith(".wiki") else filename
    return urllib.parse.unquote(name)


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def load_state() -> dict:
    if not STATE_FILE.is_file():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_category(text: str) -> str:
    if CAT_RE.search(text):
        return text
    if not text.endswith("\n"):
        text += "\n"
    return text + CAT_TAG + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max-edits", type=int, default=200)
    ap.add_argument("--run-tag", default="")
    args = ap.parse_args()

    if not PASSWORD:
        print("ERROR: WIKI_PASSWORD env var is not set. Cannot push.", file=sys.stderr)
        return 2

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH, clients_useragent=USER_AGENT)
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}")

    state = load_state()
    local_files = sorted(WIKI_DIR.glob("*.wiki"))
    print(f"Found {len(local_files)} local files in {WIKI_DIR.name}/")

    edits = pushed = wrote = skipped = errors = 0

    for local_path in local_files:
        if edits >= args.max_edits:
            print(f"max-edits cap ({args.max_edits}) reached")
            break
        title = filename_to_title(local_path.name)
        try:
            local_text = local_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"ERROR reading {title}: {e}")
            errors += 1
            continue

        try:
            page = site.pages[title]
            if not page.exists:
                print(f"SKIP (wiki page missing): {title}")
                skipped += 1
                continue
            wiki_text = page.text()
            wiki_revid = int(page.revision) if hasattr(page, "revision") else None
        except Exception as e:
            print(f"ERROR fetching wiki {title}: {e}")
            errors += 1
            continue

        if wiki_text.strip() == local_text.strip():
            entry = state.get(title) or {}
            if entry.get("revid") != wiki_revid or entry.get("sha") != sha1_text(local_text):
                state[title] = {"revid": wiki_revid, "sha": sha1_text(local_text)}
                if args.apply:
                    save_state(state)
            print(f"NO-MERGE (identical): {title}")
            continue

        merged = wiki_text.rstrip() + SEPARATOR + local_text.lstrip()
        merged = ensure_category(merged)

        if not args.apply:
            print(f"[DRY] MERGE+PUSH: {title}  (wiki {wiki_revid}, local sha {sha1_text(local_text)[:8]} -> merged sha {sha1_text(merged)[:8]})")
            edits += 1
            continue

        try:
            result = page.save(
                merged,
                summary=f"Unstick merge: append local-side changes after wiki content; keep in queue {args.run_tag}",
            )
            new_revid = (result or {}).get("newrevid") or wiki_revid
            pushed += 1
            time.sleep(THROTTLE)
        except Exception as e:
            print(f"ERROR pushing {title}: {e}")
            errors += 1
            continue

        try:
            local_path.write_text(merged, encoding="utf-8", newline="\n")
            wrote += 1
        except Exception as e:
            print(f"ERROR writing local {title}: {e}")
            errors += 1
            continue

        state[title] = {"revid": new_revid, "sha": sha1_text(merged)}
        save_state(state)
        edits += 1
        print(f"MERGE+PUSH  {title}  (new rev {new_revid})")

    print(f"\nPushed:   {pushed}")
    print(f"Wrote:    {wrote}")
    print(f"Skipped:  {skipped}")
    print(f"Errors:   {errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
