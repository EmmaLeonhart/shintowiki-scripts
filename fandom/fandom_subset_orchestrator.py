#!/usr/bin/env python3
"""
fandom_subset_orchestrator.py
=============================
All-namespace sweep of shinto.fandom.com that makes Fandom a strict
subset/mirror of shinto.miraheze.org.

For every Fandom page F, compare against the miraheze page S at the
*identical namespaced title* ("equivalent" = exact-title match):

  1. F's title is protected by a ``fandom_unique/<title>.wiki`` file
     → SKIP.
  2. F is the Fandom Main Page → SKIP.
  3. S does NOT exist               → DELETE F.
  4. S exists and is NOT a redirect → SKIP (real equivalent exists;
     content sync is the existing sync scripts' job, not ours).
  5. S exists and IS a redirect (a redirect IS a valid equivalent — it points
     at a real target on the miraheze side):
       * F is also a redirect        → SKIP (keep F; the miraheze redirect
         counts as the equivalent — do NOT orphan-delete it).
       * F is NOT a redirect         → COPY OVER: overwrite F's wikitext
         with S's redirect wikitext, so Fandom becomes the same redirect.

This is the literal rule from Emma (2026-06-18): "delete if there is no
equivalent on Shinto, including when the Shinto page is a redirect —
assuming the Fandom one is not a redirect, in which case copy it over
instead." Copy-over direction is Shinto redirect → Fandom (confirmed).

Design doc: docs/superpowers/specs/2026-06-18-fandom-subset-orchestrator-design.md

Namespace scope: ALL namespaces EXCEPT
  * ns 6  (File:)      — the SAME fandom-cleanup workflow imports Commons
                         files here; deleting them would fight the
                         importer. Deferred until we confirm miraheze
                         hosts local File: pages.
  * ns 8  (MediaWiki:) — interface/system messages; deleting them would
                         break the Fandom UI. Every miraheze orchestrator
                         excludes ns 8 too.
Virtual namespaces (Special -1, Media -2) are not walkable / out of scope.

Reads (both wikis) are batched 50 titles/call and lightly throttled;
only writes (deletes + copy-overs) pay the 2.5s wiki-load throttle.
Cursor state lets each run resume; --max-edits caps writes per run.
No-ops past FANDOM_SUNSET_DATE (all fandom writes stop).

Auth: writes to fandom via FANDOM_USERNAME / FANDOM_PASSWORD (bot
password). Reads are anonymous on both wikis. Dry-run needs no login.

Standard CLI: --apply (default dry-run), --max-edits, --run-tag.
"""

import argparse
import datetime
import io
import json
import os
import sys
import time
import urllib.parse
from pathlib import Path

import mwclient

# Standalone scripts run with their own dir on sys.path; this resolves
# to shinto_miraheze/wiki_login.py is NOT a sibling here (we're in
# fandom/), so add shinto_miraheze/ explicitly for the shared helper.
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "shinto_miraheze"))
from wiki_login import login_with_retry  # noqa: E402

# Force UTF-8 stdout without re-wrapping the buffer (wrapping closes it under
# pytest capture). reconfigure() is a no-op where unavailable.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

FANDOM_HOST = "shinto.fandom.com"
MIRAHEZE_HOST = "shinto.miraheze.org"
FANDOM_PATH = "/"
MIRAHEZE_PATH = "/w/"

FANDOM_USERNAME = os.getenv("FANDOM_USERNAME", "")
FANDOM_PASSWORD = os.getenv("FANDOM_PASSWORD", "")

THROTTLE = 2.5          # between writes (deletes + copy-overs)
READ_THROTTLE = 0.3     # between batched read calls
BATCH = 50              # titles per read query (anon read limit)

# FANDOM_SUNSET_DATE mirrors the canonical constant in
# shinto_miraheze/orchestrators/ops/fandom_mirror.py. Inlined here for
# the same sys.path reason as bootstrap_seed_fandom_unique_from_miraheze.py
# (we run as `python3 fandom/X.py`). Keep the two in sync.
FANDOM_SUNSET_DATE = datetime.date(2027, 1, 1)

# Namespaces never swept (see module docstring).
EXCLUDED_NAMESPACES = {6, 8}

# Never deleted regardless of equivalence. The Fandom main page title is
# discovered from siteinfo at runtime and added to this set.
HARD_EXCLUDES = {"Main Page"}

FANDOM_DIR = REPO_ROOT / "fandom_unique"
STATE_FILE = SCRIPT_DIR / "fandom_subset_orchestrator.state"
ERRORS_FILE = SCRIPT_DIR / "fandom_subset_orchestrator.errors"

# API error codes that mean "the bot is not allowed to delete" rather
# than a transient/per-page problem. If we see these, the bot password
# almost certainly lacks the "Delete pages" grant (the account itself
# IS a sysop, confirmed 2026-06-18). We record them to a committed
# .errors file so the blocker is durable in git rather than lost in a
# CI log — there is no automatic path from a CI script to
# [[Open questions]].
PERMISSION_DENIED_CODES = {"permissiondenied", "cantdelete", "protectedpage"}

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

_FORBIDDEN = set('<>:"/\\|?*')


def title_to_filename(title: str) -> str:
    """Match the encoding used by sync_fandom_unique_pages.py."""
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


def load_protected_titles() -> set:
    """Titles backed by a fandom_unique/<title>.wiki file (protect guard)."""
    if not FANDOM_DIR.exists():
        return set()
    return {
        filename_to_title(p.name)
        for p in FANDOM_DIR.iterdir()
        if p.is_file() and p.name.endswith(".wiki")
    }


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def sunset_passed() -> bool:
    return datetime.datetime.utcnow().date() >= FANDOM_SUNSET_DATE


def swept_namespaces(fandom_site) -> list:
    """Ordered list of namespace ids to sweep: all content/talk
    namespaces >= 0 except the excluded set."""
    ns_ids = []
    for ns_id_str in fandom_site.namespaces:
        try:
            ns_id = int(ns_id_str)
        except (TypeError, ValueError):
            continue
        if ns_id < 0:
            continue  # virtual (Special/Media) — not walkable
        if ns_id in EXCLUDED_NAMESPACES:
            continue
        ns_ids.append(ns_id)
    return sorted(ns_ids)


def fetch_main_page_title(fandom_site) -> str:
    try:
        data = fandom_site.api(
            "query", meta="siteinfo", siprop="general", formatversion="2"
        )
        return data.get("query", {}).get("general", {}).get("mainpage", "")
    except Exception:
        return ""


def fandom_chunk(fandom_site, ns, gapfrom):
    """One generator=allpages page of up to BATCH Fandom titles in ns.

    Returns (entries, continue_params) where entries is a list of
    {"title": str, "redirect": bool} and continue_params is the dict to
    merge for the next call (empty dict when the namespace is exhausted).
    """
    params = {
        "generator": "allpages",
        "gapnamespace": ns,
        "gaplimit": BATCH,
        "prop": "info",
        "formatversion": "2",
    }
    if gapfrom:
        params["gapfrom"] = gapfrom
    data = fandom_site.api("query", **params)
    pages = data.get("query", {}).get("pages", [])
    entries = [
        {"title": p["title"], "redirect": bool(p.get("redirect", False))}
        for p in pages
        if "title" in p
    ]
    # allpages returns alphabetical; keep stable order.
    entries.sort(key=lambda e: e["title"])
    cont = data.get("continue", {})
    return entries, cont


def miraheze_status(miraheze_site, titles):
    """Batched miraheze lookup. Returns {title: ("missing"|"redirect"|"article")}
    keyed by the ORIGINAL queried title (normalization handled here)."""
    if not titles:
        return {}
    data = miraheze_site.api(
        "query",
        titles="|".join(titles),
        prop="info",
        formatversion="2",
    )
    q = data.get("query", {})
    norm = {n["from"]: n["to"] for n in q.get("normalized", [])}
    by_title = {}
    for p in q.get("pages", []):
        t = p.get("title")
        if t is None:
            continue
        if p.get("missing") or p.get("invalid"):
            by_title[t] = "missing"
        elif p.get("redirect"):
            by_title[t] = "redirect"
        else:
            by_title[t] = "article"
    out = {}
    for t in titles:
        key = norm.get(t, t)
        out[t] = by_title.get(key, "missing")
    return out


def decide(title, f_is_redirect, s_status, protected, main_page_titles):
    """Return (action, reason) where action is 'skip'|'delete'|'copyover'."""
    if title in protected:
        return "skip", "protected (fandom_unique/)"
    if title in main_page_titles or title in HARD_EXCLUDES:
        return "skip", "main page / hard-exclude"
    if s_status == "missing":
        return "delete", "no Shinto equivalent"
    if s_status == "article":
        return "skip", "Shinto equivalent exists (article)"
    # s_status == "redirect": miraheze HAS the page — a redirect pointing at a
    # real target — so it counts as a valid equivalent. Never delete the fandom
    # page for "no equivalent" just because both sides are redirects (Emma
    # 2026-07-06: count/follow the miraheze redirect before deleting; this was
    # wrongly orphaning Template:Ill every few days).
    if f_is_redirect:
        return "skip", "Shinto redirect is a valid equivalent"
    return "copyover", "Shinto is redirect, Fandom is real content"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="actually delete/copy-over; default is dry-run (report only)",
    )
    parser.add_argument(
        "--max-edits", type=int, default=100,
        help="per-run cap on WRITES (deletes + copy-overs); default 100",
    )
    parser.add_argument(
        "--run-tag", required=True,
        help="wiki-formatted run tag link for edit/delete-summary attribution",
    )
    args = parser.parse_args()

    if sunset_passed():
        print(
            f"fandom_subset_orchestrator disabled: past FANDOM_SUNSET_DATE "
            f"({FANDOM_SUNSET_DATE.isoformat()}). No fandom writes."
        )
        return 0

    protected = load_protected_titles()
    print(f"Loaded {len(protected)} protected fandom_unique/ titles")

    # Reads are anonymous on both wikis; login to fandom only when applying.
    fandom_site = mwclient.Site(
        FANDOM_HOST, path=FANDOM_PATH, clients_useragent=USER_AGENT
    )
    miraheze_site = mwclient.Site(
        MIRAHEZE_HOST, path=MIRAHEZE_PATH, clients_useragent=USER_AGENT
    )

    if args.apply:
        if not FANDOM_USERNAME or not FANDOM_PASSWORD:
            print("FATAL: --apply requires FANDOM_USERNAME / FANDOM_PASSWORD.",
                  file=sys.stderr)
            return 2
        login_with_retry(fandom_site, FANDOM_USERNAME, FANDOM_PASSWORD)
        print(f"Logged in to {FANDOM_HOST} as {FANDOM_USERNAME}")
    else:
        print("DRY RUN — no login, no writes")

    main_page = fetch_main_page_title(fandom_site)
    main_page_titles = {main_page} if main_page else set()

    ns_list = swept_namespaces(fandom_site)
    print(f"Sweeping namespaces: {ns_list}")

    state = load_state()
    start_ns = state.get("ns", ns_list[0] if ns_list else 0)
    start_from = state.get("from_title", "")
    if start_ns not in ns_list:
        start_ns = ns_list[0] if ns_list else 0
        start_from = ""

    # Build the walk order: from start_ns to the end of the list. (The
    # cursor wraps to ns_list[0] when the whole list is exhausted.)
    start_idx = ns_list.index(start_ns) if start_ns in ns_list else 0
    walk_order = ns_list[start_idx:]

    writes = checked = deleted = copied = skipped = errors = 0
    perm_denied = []  # [(title, code)] — bot lacks the delete grant
    completed_walk = True  # cleared if we stop early on the write cap

    for i, ns in enumerate(walk_order):
        gapfrom = start_from if i == 0 else ""
        while True:
            try:
                entries, cont = fandom_chunk(fandom_site, ns, gapfrom)
            except Exception as e:
                print(f"  [ns {ns}] allpages error from {gapfrom!r}: {e}")
                errors += 1
                break
            time.sleep(READ_THROTTLE)

            if entries:
                titles = [e["title"] for e in entries]
                try:
                    status = miraheze_status(miraheze_site, titles)
                except Exception as e:
                    print(f"  [ns {ns}] miraheze lookup error: {e}")
                    errors += 1
                    status = {t: None for t in titles}
                time.sleep(READ_THROTTLE)

                for e in entries:
                    title = e["title"]
                    checked += 1
                    s_status = status.get(title)
                    if s_status is None:
                        print(f"  SKIP {title} (lookup failed)")
                        skipped += 1
                        continue
                    action, reason = decide(
                        title, e["redirect"], s_status,
                        protected, main_page_titles,
                    )
                    if action == "skip":
                        skipped += 1
                        continue

                    if not args.apply:
                        verb = "would delete" if action == "delete" else "would copy-over"
                        print(f"  DRY {verb}: {title} ({reason})")
                        writes += 1
                    else:
                        try:
                            page = fandom_site.pages[title]
                            if action == "delete":
                                page.delete(
                                    reason=f"Bot: no Shinto equivalent {args.run_tag}"
                                )
                                deleted += 1
                                print(f"  DELETED {title} ({reason})")
                            else:  # copyover
                                s_text = miraheze_site.pages[title].text()
                                page.save(
                                    s_text,
                                    summary=f"Bot: mirror Shinto redirect {args.run_tag}",
                                )
                                copied += 1
                                print(f"  COPIED-OVER {title} ({reason})")
                            writes += 1
                            time.sleep(THROTTLE)
                        except Exception as ex:
                            code = getattr(ex, "code", "") or ""
                            if code in PERMISSION_DENIED_CODES:
                                perm_denied.append((title, code))
                            print(f"  ERROR {action} {title}: {ex}")
                            errors += 1

                    if writes >= args.max_edits:
                        # Resume from this title next run (gapfrom is
                        # inclusive; re-checking it is idempotent).
                        save_state({"ns": ns, "from_title": title})
                        completed_walk = False
                        print(f"\nReached max-edits ({args.max_edits}); "
                              f"saved cursor ns={ns} from={title!r}.")
                        _write_errors_file(perm_denied)
                        _summary(args, checked, deleted, copied, skipped, errors, writes)
                        return 0

            if "continue" in {**cont}:  # more pages in this namespace
                gapfrom = cont.get("gapcontinue", "")
                if not gapfrom:
                    break
            else:
                break

    if completed_walk:
        # Whole sweep finished without hitting the cap — wrap to start.
        save_state({"ns": ns_list[0] if ns_list else 0, "from_title": ""})
        print("\nCompleted full sweep; cursor wrapped to start.")

    _write_errors_file(perm_denied)
    _summary(args, checked, deleted, copied, skipped, errors, writes)
    return 0


def _write_errors_file(perm_denied):
    """Write/clear the committed .errors file for permission-denied deletes.

    Non-empty → the bot password lacks the 'Delete pages' grant; record a
    durable, git-committed note (commit_state.sh globs *.errors). Empty →
    remove any stale file from a previous run so a fixed grant clears it.
    """
    if not perm_denied:
        try:
            ERRORS_FILE.unlink()
        except FileNotFoundError:
            pass
        return
    sample = perm_denied[:10]
    lines = [
        "fandom_subset_orchestrator: DELETE PERMISSION DENIED.",
        "",
        f"{len(perm_denied)} delete(s) were rejected with a permission "
        "error code.",
        "The 'Their Eminence' account IS a sysop, so this means the BOT "
        "PASSWORD used in CI (FANDOM_PASSWORD) was created without the "
        "'Delete pages' grant.",
        "",
        "ACTION (Emma): edit the bot password at "
        "https://shinto.fandom.com/wiki/Special:BotPasswords and enable "
        "the 'Delete pages' grant, then re-save the FANDOM_PASSWORD secret.",
        "",
        "Sample rejected titles (code):",
    ]
    lines += [f"  - {t}  ({code})" for t, code in sample]
    ERRORS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n!! Wrote {ERRORS_FILE.name}: {len(perm_denied)} delete(s) "
          f"denied — bot password likely lacks the Delete grant.")


def _summary(args, checked, deleted, copied, skipped, errors, writes):
    print()
    print("=" * 60)
    print(f"Mode:        {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Checked:     {checked}")
    if args.apply:
        print(f"Deleted:     {deleted}")
        print(f"Copied-over: {copied}")
    else:
        print(f"Writes (would): {writes}")
    print(f"Skipped:     {skipped}")
    print(f"Errors:      {errors}")


if __name__ == "__main__":
    sys.exit(main())
