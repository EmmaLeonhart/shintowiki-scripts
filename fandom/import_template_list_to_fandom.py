"""
Batch-import a fixed list of templates from shinto.miraheze.org into
shinto.fandom.com via Special:Export -> action=import.

Driven by ``templates to import to fandom.txt`` (one template per line,
formatted ``Template:Name (NNN links)``). Unlike the orchestrator's
``fandom_mirror`` op (which is a sub-stage of ``history_offload`` and
explicitly refuses redirects), this script imports every listed page
including redirects. The bulk of the missing-on-fandom templates ARE
redirects, which is why the routine mirror skipped them.

State is kept in ``shinto_miraheze/import_template_list_to_fandom.state``
(JSON) so the script resumes where it left off across runs and the
GitHub Actions workflow can budget a small number of imports per run.

Standard CLI flags (matches the rest of the repo):
  --apply         actually POST to fandom (default: dry-run)
  --max-edits N   cap successful imports per run
  --run-tag STR   wiki-formatted run tag for edit/import summaries
"""

import argparse
import io
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone

import mwclient
import requests

# wiki_login lives in the sibling shinto_miraheze/ package; this script runs as
# a top-level `python3 fandom/X.py`, so add the repo root to sys.path before the
# package import (same shim as sync_fandom_unique_pages.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shinto_miraheze.wiki_login import login_with_retry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

THROTTLE = 2.5

SRC_HOST = "shinto.miraheze.org"
SRC_EXPORT_URL = f"https://{SRC_HOST}/w/index.php"
DST_HOST = "shinto.fandom.com"
DST_API_URL = f"https://{DST_HOST}/api.php"
INTERWIKI_PREFIX = "shintowiki"
USER_AGENT = (
    "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) "
    "import_template_list_to_fandom (shintowiki-scripts)"
)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # fandom action=import hard cap

# Input list lives next to this script (fandom/); resolve relative to __file__
# so the cwd doesn't matter. State stays under shinto_miraheze/ (cwd-relative,
# repo root in CI) because commit_state.sh globs *.state there.
INPUT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates to import to fandom.txt"
)
STATE_FILE = os.path.join(
    "shinto_miraheze", "import_template_list_to_fandom.state"
)

LINE_RE = re.compile(r"^(Template:.+?)\s+\(\s*[\d,]+\s+links?\)\s*$")


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"WARN: could not parse state file ({e}); starting fresh.")
    return {}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, STATE_FILE)


def parse_titles(path: str) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            m = LINE_RE.match(line)
            if not m:
                # Tolerate plain-title lines too, in case the file is
                # ever simplified.
                if line.startswith("Template:"):
                    title = line
                else:
                    print(f"WARN: skipping unparseable line: {line!r}")
                    continue
            else:
                title = m.group(1).strip()
            if title in seen:
                continue
            seen.add(title)
            titles.append(title)
    return titles


def fetch_xml(title: str) -> str:
    """Full-history XML for one page from shintowiki's Special:Export.

    `curonly` must be OMITTED (not set to "0") because SpecialExport.php
    uses getCheck(), which treats any present value as truthy.
    """
    resp = requests.post(
        SRC_EXPORT_URL,
        data={
            "title": "Special:Export",
            "pages": title,
            "history": "1",
            "wpDownload": "1",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=300,
    )
    resp.raise_for_status()
    xml = resp.text
    if "<mediawiki" not in xml:
        raise RuntimeError(
            f"Source export didn't return MediaWiki XML. "
            f"First 200 chars: {xml[:200]!r}"
        )
    return xml


def fandom_login() -> mwclient.Site:
    user = os.getenv("FANDOM_USERNAME")
    pw = os.getenv("FANDOM_PASSWORD")
    if not user or not pw:
        raise RuntimeError(
            "FANDOM_USERNAME / FANDOM_PASSWORD env vars are required."
        )
    site = mwclient.Site(DST_HOST, path="/", clients_useragent=USER_AGENT)
    login_with_retry(site, user, pw)
    return site


def import_xml(site: mwclient.Site, token: str, xml_text: str,
               run_tag: str) -> dict:
    summary = "Batch import of redirect/missing templates from shintowiki"
    if run_tag:
        summary = f"{summary} {run_tag}"
    resp = site.connection.post(
        DST_API_URL,
        data={
            "action": "import",
            "format": "json",
            "token": token,
            "summary": summary,
            "interwikiprefix": INTERWIKI_PREFIX,
        },
        files={
            "xml": ("export.xml", xml_text.encode("utf-8"), "application/xml"),
        },
        headers={"User-Agent": USER_AGENT},
        timeout=300,
    )
    status = resp.status_code
    snippet = (resp.text or "")[:200].replace("\n", "\\n")
    try:
        return resp.json()
    except Exception as e:
        raise RuntimeError(
            f"non-JSON import response (HTTP {status}, body[:200]={snippet!r}): {e}"
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def process_one(title: str, fandom: mwclient.Site, csrf_token: str,
                run_tag: str, apply: bool) -> dict:
    """Import a single title. Returns the state-record dict to store."""
    try:
        xml = fetch_xml(title)
    except Exception as e:
        return {"status": "error", "reason": f"export: {e}", "ts": now_iso()}

    rev_count = xml.count("<revision>")
    if rev_count == 0:
        return {
            "status": "skip",
            "reason": "source has no revisions (page missing on shintowiki)",
            "ts": now_iso(),
        }

    size = len(xml.encode("utf-8"))
    if size > MAX_UPLOAD_BYTES:
        return {
            "status": "skip",
            "reason": (
                f"XML {size} bytes exceeds fandom 10MB import cap"
            ),
            "ts": now_iso(),
        }

    if not apply:
        return {
            "status": "dryrun",
            "revisions": rev_count,
            "bytes": size,
            "ts": now_iso(),
        }

    try:
        body = import_xml(fandom, csrf_token, xml, run_tag)
    except Exception as e:
        return {
            "status": "error",
            "reason": f"import POST: {e}",
            "ts": now_iso(),
        }

    if "error" in body:
        err = body["error"]
        return {
            "status": "error",
            "reason": f"api: {err.get('code')} - {err.get('info')}",
            "ts": now_iso(),
        }

    imported = body.get("import", []) or []
    if not imported:
        # Idempotent no-op: every revision already exists on fandom.
        return {
            "status": "ok",
            "revisions": 0,
            "note": "already mirrored",
            "ts": now_iso(),
        }
    entry = imported[0]
    return {
        "status": "ok",
        "revisions": entry.get("revisions", 0),
        "title_imported": entry.get("title"),
        "ns": entry.get("ns"),
        "bytes": size,
        "ts": now_iso(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Actually import to fandom (default: dry-run).")
    parser.add_argument("--max-edits", type=int, default=25,
                        help="Cap on successful imports per run (default 25).")
    parser.add_argument("--run-tag", default="",
                        help="Wiki-formatted run tag appended to import summary.")
    parser.add_argument("--input", default=INPUT_FILE,
                        help=f"Path to template list (default {INPUT_FILE!r}).")
    parser.add_argument("--retry-errors", action="store_true",
                        help="Re-attempt titles previously recorded as error.")
    args = parser.parse_args()

    load_env()

    if not os.path.exists(args.input):
        print(f"FATAL: input file not found: {args.input}")
        return 2

    titles = parse_titles(args.input)
    state = load_state()

    pending: list[str] = []
    for title in titles:
        rec = state.get(title)
        if rec is None:
            pending.append(title)
            continue
        st = rec.get("status")
        if st == "ok" or st == "skip":
            continue
        if st == "error" and not args.retry_errors:
            continue
        # dryrun records are always re-attempted on a real run
        if st == "dryrun" and not args.apply:
            continue
        pending.append(title)

    print(f"Loaded {len(titles)} titles from {args.input}")
    print(f"State has {len(state)} records; {len(pending)} pending this run.")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}, cap={args.max_edits}")

    if not pending:
        print("Nothing to do.")
        return 0

    fandom = None
    csrf_token = ""
    if args.apply:
        try:
            print(f"Logging in to {DST_HOST}...")
            fandom = fandom_login()
            csrf_token = fandom.get_token("csrf")
            print("  OK.")
        except Exception as e:
            print(f"FATAL: fandom login failed: {e}")
            traceback.print_exc()
            return 1

    successes = 0
    failures = 0
    skipped = 0
    try:
        for i, title in enumerate(pending, 1):
            if successes >= args.max_edits:
                print(f"Reached --max-edits cap ({args.max_edits}); stopping.")
                break
            print(f"[{i}/{len(pending)}] {title}")
            rec = process_one(title, fandom, csrf_token, args.run_tag, args.apply)
            state[title] = rec
            st = rec.get("status")
            if st == "ok":
                successes += 1
                print(f"  OK ({rec.get('revisions')} revs, "
                      f"{rec.get('bytes', '?')} bytes)")
            elif st == "skip":
                skipped += 1
                print(f"  SKIP: {rec.get('reason')}")
            elif st == "dryrun":
                successes += 1
                print(f"  DRY-RUN: would import "
                      f"{rec.get('revisions')} revs / {rec.get('bytes')} bytes")
            else:
                failures += 1
                print(f"  ERROR: {rec.get('reason')}")
            # Persist after every page so a mid-run crash doesn't lose
            # progress (matters for cap-bounded GH Actions runs).
            save_state(state)
            time.sleep(THROTTLE)
    finally:
        save_state(state)

    print()
    print("=== Summary ===")
    print(f"  successes: {successes}")
    print(f"  skipped:   {skipped}")
    print(f"  failures:  {failures}")
    print(f"  state:     {STATE_FILE}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
