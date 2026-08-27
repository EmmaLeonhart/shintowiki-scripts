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

import urllib.parse
import urllib.request

import mwclient
from wiki_login import login_with_retry

# Force UTF-8 so Japanese titles survive a cp1252 Windows console. Guarded on
# the current encoding: under pytest, stdout is an already-UTF-8 capture object
# with no .buffer, and rewrapping it made the module unimportable -- the wrapper
# outlived the captured file and teardown died on a closed handle. Anything that
# is already UTF-8 needs no help.
if getattr(sys.stdout, "encoding", "").lower().replace("-", "") != "utf8":
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

GIT_SYNCED_RE = re.compile(r"\[\[\s*Category\s*:\s*Git synced pages\s*\]\]",
                           re.IGNORECASE)
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


WD_API = "https://www.wikidata.org/w/api.php"
WD_BATCH = 40


def resolve_qid_redirects(qids, user_agent: str) -> dict:
    """Map each QID to the QID Wikidata actually serves for it.

    ``wbgetentities`` keys its response by the id you ASKED for, while the
    entity's own ``id`` field is the id you LANDED on. Requested != returned
    therefore means the requested QID is a redirect into the returned one.

    ⛔ Do NOT add ``redirects=no``. It suppresses the resolution, every pair
    comes back looking like two distinct live items, and the caller draws the
    exact opposite conclusion. That mistake was made on 2026-08-26 and caught
    only because the two "distinct" items had byte-identical claims.

    A QID that is missing/deleted maps to None. On a network error the batch is
    dropped rather than guessed — an unresolved QID simply fails the redirect
    test, which is the safe direction.
    """
    out: dict = {}
    ids = sorted({q for q in qids if q})
    for i in range(0, len(ids), WD_BATCH):
        batch = ids[i:i + WD_BATCH]
        url = WD_API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(batch),
            "format": "json", "props": "info",
        })
        try:
            req = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(req, timeout=60) as fh:
                data = json.load(fh)
        except Exception as e:
            print(f"  Wikidata resolve failed for batch {i // WD_BATCH}: {e}; "
                  f"{len(batch)} QIDs left unresolved this run")
            time.sleep(1.0)
            continue
        for key, ent in (data.get("entities") or {}).items():
            out[key] = None if "missing" in ent else ent.get("id")
        time.sleep(0.25)
    return out


def pick_canonical(qid: str, pages: list[str]) -> str | None:
    """The page that OWNS the group's QID, else the sole page with no QID stub.

    Returns None when neither test picks exactly one page — two real names, two
    unrelated stubs, a three-page group with two candidates. Ambiguous groups are
    reported, never guessed.
    """
    exact = [p for p in pages if QID_PAREN_RE.search(p)
             and QID_PAREN_RE.search(p).group(0)[1:-1] == qid]
    if len(exact) == 1:
        return exact[0]
    no_stub = [p for p in pages if not QID_PAREN_RE.search(p)]
    if len(no_stub) == 1 and not exact:
        return no_stub[0]
    return None


def title_qid(title: str) -> str | None:
    m = QID_PAREN_RE.search(title)
    return m.group(0)[1:-1] if m else None


def build_move_plan(state: dict, resolved: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Return (auto_moves, ambiguous_groups) from the duplicate-QID state.

    PRIMARY RULE (Emma, 2026-08-26): *"if one redirects into another on wikidata
    then that's clear evidence you can just redirect it on the shintowiki too."*
    When a page's own title QID resolves to the group's QID, the two pages are two
    pages for one Wikidata item and the non-canonical one is redirected.

    This OUTRANKS the old title heuristics, which guessed from title shape and got
    it wrong in both directions: 29 of 43 stubs checked on 2026-08-26 were filed
    under a QID other than the one in their own title, and 8 pairs carried visibly
    different shrine names (the historical Engishiki name beside the modern shrine
    name) that the heuristics would have refused or mis-ordered.

    The heuristics remain as a FALLBACK for titles carrying no QID at all
    (Japanese-script vs rōmaji), where there is nothing for Wikidata to resolve.

    ``resolved`` maps QID -> the QID Wikidata serves for it. Pass None to skip the
    primary rule entirely (offline/unit-test use) and fall back to heuristics.
    """
    resolved = resolved or {}
    qid_to_pages: dict[str, list[str]] = defaultdict(list)
    for title, qid in state.items():
        qid_to_pages[qid].append(title)

    auto_moves: list[dict] = []
    ambiguous: list[dict] = []

    for qid, pages in sorted(qid_to_pages.items()):
        if len(pages) < 2:
            continue

        # Template /doc pairs — the doc subpage inherits its parent's
        # {{wikidata link}}. Never a duplicate; the fix is stripping the
        # template from the subpage, not merging the two.
        if any("/doc" in p and p.startswith("Template:") for p in pages):
            ambiguous.append({"qid": qid, "pages": pages, "reason": "template/doc pair"})
            continue

        # ── PRIMARY: proven Wikidata redirect ──────────────────────
        canonical = pick_canonical(qid, pages)
        if canonical is not None:
            proven = [p for p in pages
                      if p != canonical and resolved.get(title_qid(p)) == qid]
            if proven:
                for non_canon in proven:
                    auto_moves.append({
                        "qid": qid, "from": non_canon, "to": canonical,
                        "reason": "Wikidata redirect → same item",
                    })
                unproven = [p for p in pages if p != canonical and p not in proven]
                if unproven:
                    ambiguous.append({"qid": qid, "pages": unproven,
                                      "reason": "no Wikidata redirect into the group QID"})
                continue

        # ── FALLBACK: title heuristics, QID-less titles only ───────
        has_qid_stub = [p for p in pages if QID_PAREN_RE.search(p)]
        no_qid_stub = [p for p in pages if not QID_PAREN_RE.search(p)]

        has_jp = [p for p in pages if JP_RE.search(p)]
        no_jp = [p for p in pages if not JP_RE.search(p)]

        if has_jp and len(no_jp) == 1 and not has_qid_stub:
            for non_canon in has_jp:
                auto_moves.append({
                    "qid": qid, "from": non_canon, "to": no_jp[0],
                    "reason": "JP-script → ASCII/rōmaji",
                })
            continue

        if has_qid_stub:
            reason = ("both QID stubs" if not no_qid_stub
                      else "QID stub with no Wikidata redirect into the group QID")
        else:
            reason = "unclear canonical"
        ambiguous.append({"qid": qid, "pages": pages, "reason": reason})

    return auto_moves, ambiguous


def perform_move(site, src: str, dst: str, run_tag: str, apply: bool,
                 proven: bool = False) -> str:
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
        if not proven:
            # ⛔ Content overwrite is allowed ONLY for a proven Wikidata redirect.
            # The JP-script heuristic was safe for as long as this branch just
            # skipped: a move cannot clobber a live page, so a wrong guess cost
            # nothing. Adding the redirect-over-content path below turned that
            # same heuristic into a content-destroying one -- measured 2026-08-27,
            # its 45 pending moves include 健磐龍命 (19,095 b, with Nihon Shoki and
            # Fudoki sections) redirecting onto a 13,161 b page that does not
            # contain them. Two titles sharing a QID is not evidence that one
            # article contains the other.
            return "skipped:dst exists as real page (heuristic move, unproven)"
        # Both pages exist as real pages. A MediaWiki move REFUSES this, which
        # is why every duplicate-QID group came back "skipped:dst exists as real
        # page": the move path could only ever help when the canonical title was
        # still free, and for a duplicate it never is. Replacing the
        # non-canonical page's content with a redirect is the merge that
        # actually applies. Only reachable once the caller has proven
        # same-entity via the Wikidata redirect.
        summary = (f"Bot: redirect duplicate QID page to canonical title "
                   f"(same Wikidata item) {run_tag}").strip()
        if not apply:
            return "dry:would redirect over content"
        try:
            new_text = f"#REDIRECT [[{dst}]]\n"
            # git_synced/ membership is load-bearing: dropping the category makes
            # the next sync treat the page as removed-from-repo and untrack it.
            if GIT_SYNCED_RE.search(src_text):
                new_text += "\n[[Category:Git synced pages]]\n"
            src_page.save(new_text, summary=summary)
            return "redirected"
        except Exception as e:
            return f"error:{e}"

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

    # Resolve every QID appearing in a duplicate group against Wikidata. A
    # requested id that comes back as a DIFFERENT id is a redirect, which is
    # the evidence the planner needs to call two pages one entity.
    qid_to_pages_m: dict[str, list[str]] = defaultdict(list)
    for _t, _q in state.items():
        qid_to_pages_m[_q].append(_t)
    dup_qids = {q for q, ps in qid_to_pages_m.items() if len(ps) > 1}
    to_resolve = set(dup_qids)
    for q in dup_qids:
        for pg in qid_to_pages_m[q]:
            tq = title_qid(pg)
            if tq:
                to_resolve.add(tq)
    print(f"Resolving {len(to_resolve)} QIDs against Wikidata...")
    resolved = resolve_qid_redirects(to_resolve, USER_AGENT)
    n_red = sum(1 for k, v in resolved.items() if v and v != k)
    print(f"  {n_red} of {len(resolved)} resolve to a different QID (redirects)")

    auto_moves, ambiguous = build_move_plan(state, resolved)
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

        result = perform_move(site, src, dst, args.run_tag, args.apply,
                              proven=reason.startswith("Wikidata redirect"))
        print(f"  → {result}")

        if result.startswith(("moved", "redirected", "dry")):
            if result.startswith(("moved", "redirected")):
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
