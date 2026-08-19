#!/usr/bin/env python3
"""
import_commons_wantedfiles_to_fandom.py
========================================
Drains the first N entries of [[Special:WantedFiles]] on shinto.fandom.com
by attempting to import each from Wikimedia Commons.

The per-run limit is BOUNDED by design (default 500). The wanted-files
list on a MediaWiki wiki is a periodically-regenerated query page — it
does not refresh every page view. So if we just process the first N
entries each run, successive fires of the workflow see roughly the same
prefix until the wiki rebuilds the list (typically every few days),
at which point the entries we already imported drop off and a new prefix
appears. This keeps each individual run fast (we never iterate the whole
list) at the cost of slow gradual progress on the wiki — a trade-off
the user explicitly chose.

For each wanted-file title:

  1. Look it up on commons.wikimedia.org via the imageinfo API.
     - If the file doesn't exist on Commons, SKIP.
     - If it's not actually a file (some entries on WantedFiles can be
       non-file references), SKIP.

  2. Download the original file bytes from Commons.

  3. Upload to shinto.fandom.com via mwclient.upload(), with:
       - Edit summary noting attribution to Commons + the run tag.
       - File description that begins with a "From Wikimedia Commons"
         attribution header linking back to the Commons file page, then
         the original Commons description wikitext below it.

No persistent state file. The wiki's WantedFiles generator IS the state.
Files we successfully upload disappear from the list within a few days
as the wiki rebuilds it; runs in between either re-attempt them (no-op
because they now exist on fandom — we skip in step 1's check) or move
on to other entries.

Standard CLI flags (matches the rest of the repo):
  --apply         actually upload to fandom (default: dry-run)
  --max-edits N   per-run cap on entries CONSIDERED from WantedFiles
                  (default 500). Many will fail Commons lookup; only the
                  ones that succeed actually upload. Honors a separate
                  --max-uploads soft cap if you want to bound writes too.
  --max-uploads N optional cap on successful uploads (default = unlimited
                  within the --max-edits batch).
  --run-tag STR   wiki-formatted run tag appended to upload summary.
"""

import argparse
import io
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from urllib.parse import quote

import mwclient
import requests

# wiki_login lives in the sibling shinto_miraheze/ package; this script runs as
# a top-level `python3 fandom/X.py`, so add the repo root to sys.path before the
# package import (same shim as sync_fandom_unique_pages.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shinto_miraheze.wiki_login import login_with_retry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

THROTTLE = 2.5  # seconds between fandom uploads
COMMONS_THROTTLE = 0.3  # seconds between Commons read-only API calls

DST_HOST = "shinto.fandom.com"
COMMONS_HOST = "commons.wikimedia.org"
COMMONS_API_URL = f"https://{COMMONS_HOST}/w/api.php"
FANDOM_API_URL = f"https://{DST_HOST}/api.php"

# This file is the one that genuinely talks to BOTH sides, so it cannot have a single UA at all.
# It read commons.wikimedia.org and wrote shinto.fandom.com through ONE hardcoded
# "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot)" literal -- so every Commons read
# carried the wiki-side persona onto a Wikimedia project. Resolve per URL instead; ua_for() already
# routes Wikimedia projects to the Wikidata identity for exactly this reason.
from shinto_miraheze.ua_for import ua_for
from shinto_miraheze.user_agent import USER_AGENT


def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── FANDOM: WANTED FILES ──────────────────────────────────────────────

def fetch_wanted_files(fandom: mwclient.Site, limit: int) -> list[str]:
    """Return the first `limit` entries from Special:WantedFiles on
    fandom. We query the cached querypage directly via api.php rather
    than scraping the rendered Special: page so the result is structured
    JSON we can iterate."""
    titles: list[str] = []
    params = {
        "action": "query",
        "format": "json",
        "list": "querypage",
        "qppage": "Wantedfiles",
        "qplimit": min(limit, 500),  # API cap is 500 per request
    }
    seen: set[str] = set()
    cont: dict = {}
    while len(titles) < limit:
        q = dict(params)
        q.update(cont)
        resp = fandom.connection.get(
            FANDOM_API_URL,
            params=q,
            headers={"User-Agent": USER_AGENT},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = (
            data.get("query", {})
            .get("querypage", {})
            .get("results", []) or []
        )
        for row in rows:
            title = row.get("title")
            if not title or title in seen:
                continue
            seen.add(title)
            titles.append(title)
            if len(titles) >= limit:
                break
        cont = data.get("continue") or {}
        if not cont:
            break
        # querypage is a list endpoint — be polite between continue rounds
        time.sleep(COMMONS_THROTTLE)
    return titles


# ─── COMMONS: LOOKUP + DOWNLOAD ────────────────────────────────────────

def commons_imageinfo(filename: str) -> dict | None:
    """Fetch imageinfo + the latest description revision for a file on
    Commons. Returns None if the file does not exist there."""
    params = {
        "action": "query",
        "format": "json",
        "titles": filename,  # already includes "File:" prefix
        "prop": "imageinfo|revisions",
        "iiprop": "url|size|sha1|mime|user|timestamp|extmetadata",
        "rvprop": "content",
        "rvslots": "main",
        "rvlimit": 1,
    }
    resp = requests.get(
        COMMONS_API_URL,
        params=params,
        headers={"User-Agent": ua_for(COMMONS_API_URL)},
        timeout=120,
    )
    resp.raise_for_status()
    pages = resp.json().get("query", {}).get("pages", {}) or {}
    if not pages:
        return None
    page = next(iter(pages.values()))
    if page.get("missing") is not None:
        return None
    iinfo_list = page.get("imageinfo") or []
    if not iinfo_list:
        return None
    revs = page.get("revisions") or []
    desc_wikitext = ""
    if revs:
        slot = revs[0].get("slots", {}).get("main", {})
        desc_wikitext = slot.get("*") or slot.get("content") or ""
    iinfo = iinfo_list[0]
    return {
        "url": iinfo.get("url"),
        "size": iinfo.get("size"),
        "sha1": iinfo.get("sha1"),
        "mime": iinfo.get("mime"),
        "uploader": iinfo.get("user"),
        "timestamp": iinfo.get("timestamp"),
        "extmetadata": iinfo.get("extmetadata") or {},
        "description": desc_wikitext,
    }


def download_file(url: str) -> bytes:
    # The URL is whatever Commons handed back -- upload.wikimedia.org -- so it is a Wikimedia
    # request and must not carry the wiki-side persona.
    resp = requests.get(
        url,
        headers={"User-Agent": ua_for(url)},
        timeout=300,
        stream=True,
    )
    resp.raise_for_status()
    return resp.content


# ─── FANDOM: UPLOAD ────────────────────────────────────────────────────

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


def file_exists_on_fandom(fandom: mwclient.Site, filename: str) -> bool:
    """Cheap existence probe — avoids re-uploading something already on
    fandom (the wanted-files list can lag actual page state)."""
    try:
        page = fandom.pages[filename]
        return bool(page.exists)
    except Exception:
        return False


def build_description(commons_filename: str, info: dict, run_tag: str) -> str:
    """Compose the file-page wikitext we save on fandom: an attribution
    header + a verbatim copy of the Commons description below it."""
    bare = commons_filename
    if bare.startswith("File:"):
        bare = bare[len("File:"):]
    commons_url = f"https://{COMMONS_HOST}/wiki/File:{quote(bare.replace(' ', '_'))}"
    extm = info.get("extmetadata") or {}
    license_short = (
        extm.get("LicenseShortName", {}).get("value")
        or extm.get("License", {}).get("value")
        or ""
    )
    artist = (
        extm.get("Artist", {}).get("value")
        or info.get("uploader")
        or "unknown"
    )
    header_lines = [
        "<!-- Imported from Wikimedia Commons by EmmaBot. -->",
        f"''This file was imported from [[commons:File:{bare}|Wikimedia Commons]] "
        f"({commons_url})''",
        "",
        f"'''Original uploader on Commons:''' {artist}<br/>",
        f"'''License (per Commons metadata):''' {license_short or 'see Commons file page for details'}",
        "",
        "----",
        "",
    ]
    body = info.get("description") or ""
    return "\n".join(header_lines) + body


def upload_to_fandom(
    fandom: mwclient.Site,
    filename: str,
    content: bytes,
    description: str,
    summary: str,
) -> dict:
    """Use mwclient.upload(). Returns the API response dict."""
    bare = filename[len("File:"):] if filename.startswith("File:") else filename
    fobj = io.BytesIO(content)
    result = fandom.upload(
        file=fobj,
        filename=bare,
        description=description,
        comment=summary,
        ignore=False,
    )
    return result if isinstance(result, dict) else {"raw": str(result)}


# ─── PER-FILE PROCESSING ───────────────────────────────────────────────

def process_one(
    title: str,
    fandom: mwclient.Site,
    apply: bool,
    run_tag: str,
) -> dict:
    if not title.startswith("File:"):
        return {"status": "skip", "reason": "not a File: title", "ts": now_iso()}

    if file_exists_on_fandom(fandom, title):
        return {
            "status": "skip",
            "reason": "already exists on fandom",
            "ts": now_iso(),
        }

    try:
        info = commons_imageinfo(title)
    except Exception as e:
        return {
            "status": "error",
            "reason": f"commons lookup: {e}",
            "ts": now_iso(),
        }
    time.sleep(COMMONS_THROTTLE)

    if info is None:
        return {
            "status": "skip",
            "reason": "not on Commons",
            "ts": now_iso(),
        }

    url = info.get("url")
    if not url:
        return {
            "status": "skip",
            "reason": "Commons returned no URL",
            "ts": now_iso(),
        }

    if not apply:
        return {
            "status": "dryrun",
            "size": info.get("size"),
            "mime": info.get("mime"),
            "ts": now_iso(),
        }

    try:
        data = download_file(url)
    except Exception as e:
        return {
            "status": "error",
            "reason": f"download: {e}",
            "ts": now_iso(),
        }

    description = build_description(title, info, run_tag)
    bare = title[len("File:"):]
    summary = (
        f"Imported from Wikimedia Commons "
        f"(commons:File:{bare})"
    )
    if run_tag:
        summary = f"{summary} {run_tag}"

    try:
        body = upload_to_fandom(
            fandom, title, data, description, summary,
        )
    except Exception as e:
        return {
            "status": "error",
            "reason": f"upload: {e}",
            "ts": now_iso(),
        }

    result = body.get("result") if isinstance(body, dict) else None
    if result and result.lower() == "success":
        return {
            "status": "ok",
            "size": info.get("size"),
            "ts": now_iso(),
        }
    if isinstance(body, dict) and "error" in body:
        err = body["error"]
        return {
            "status": "error",
            "reason": f"api: {err.get('code')} - {err.get('info')}",
            "ts": now_iso(),
        }
    return {
        "status": "error",
        "reason": f"unexpected upload response: {body!r}",
        "ts": now_iso(),
    }


# ─── MAIN ──────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually upload to fandom (default: dry-run).",
    )
    parser.add_argument(
        "--max-edits", type=int, default=500,
        help=(
            "Per-run cap on entries CONSIDERED from Special:WantedFiles "
            "(default 500). Bounds work per-run; the WantedFiles list "
            "regenerates on the wiki side every few days, so successive "
            "runs see different prefixes."
        ),
    )
    parser.add_argument(
        "--max-uploads", type=int, default=0,
        help=(
            "Optional cap on successful uploads per run (default 0 = no "
            "extra cap beyond --max-edits)."
        ),
    )
    parser.add_argument(
        "--run-tag", default="",
        help="Wiki-formatted run tag appended to upload summary.",
    )
    args = parser.parse_args()

    # FANDOM_SUNSET_DATE mirrors the canonical constant in
    # shinto_miraheze/orchestrators/ops/fandom_mirror.py. Inlined here
    # because this script runs as a top-level `python3 X.py` (no
    # shinto_miraheze package on sys.path), so the package import
    # raised ModuleNotFoundError and crashed every run. Keep in sync.
    import datetime as _dt
    FANDOM_SUNSET_DATE = _dt.date(2027, 1, 1)
    if _dt.datetime.utcnow().date() >= FANDOM_SUNSET_DATE:
        print(
            f"import_commons_wantedfiles_to_fandom disabled: past "
            f"FANDOM_SUNSET_DATE ({FANDOM_SUNSET_DATE.isoformat()}). "
            f"No uploads."
        )
        return 0

    load_env()

    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Considering up to {args.max_edits} entries from Special:WantedFiles")
    if args.max_uploads:
        print(f"Cap on successful uploads: {args.max_uploads}")

    try:
        print(f"Logging in to {DST_HOST}...")
        fandom = fandom_login()
        print("  OK.")
    except Exception as e:
        print(f"FATAL: fandom login failed: {e}")
        traceback.print_exc()
        return 1

    try:
        titles = fetch_wanted_files(fandom, args.max_edits)
    except Exception as e:
        print(f"FATAL: could not fetch WantedFiles list: {e}")
        traceback.print_exc()
        return 1

    print(f"Got {len(titles)} entries from Special:WantedFiles")

    successes = 0
    skipped = 0
    failures = 0
    not_on_commons = 0

    for i, title in enumerate(titles, 1):
        if args.max_uploads and successes >= args.max_uploads:
            print(f"Hit --max-uploads cap ({args.max_uploads}); stopping.")
            break
        print(f"[{i}/{len(titles)}] {title}")
        rec = process_one(title, fandom, args.apply, args.run_tag)
        st = rec.get("status")
        if st == "ok":
            successes += 1
            print(f"  OK ({rec.get('size', '?')} bytes)")
            time.sleep(THROTTLE)
        elif st == "dryrun":
            successes += 1
            print(
                f"  DRY-RUN: would upload "
                f"{rec.get('size', '?')} bytes "
                f"({rec.get('mime', '?')})"
            )
        elif st == "skip":
            skipped += 1
            reason = rec.get("reason", "")
            if "Commons" in reason or "commons" in reason:
                not_on_commons += 1
            print(f"  SKIP: {reason}")
        else:
            failures += 1
            print(f"  ERROR: {rec.get('reason')}")

    print()
    print("=== Summary ===")
    print(f"  considered:      {len(titles)}")
    print(f"  uploaded:        {successes}")
    print(f"  skipped:         {skipped}")
    print(f"    (not on Commons: {not_on_commons})")
    print(f"  errors:          {failures}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
