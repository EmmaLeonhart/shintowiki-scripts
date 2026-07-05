#!/usr/bin/env python3
"""
generate_recreate_quickstatements.py
====================================
Backlog #8 — "recreate deleted Wikidata items". Generates QuickStatements
``CREATE`` blocks for the ``{{ill}}`` targets in
``[[Category:Pages with deleted QID in ill template]]`` whose Wikidata item was
deleted, so they can be recreated after **human review**.

ISOLATED + NOT AUTO-SUBMITTED — by design (confirmed by Emma 2026-07-05). Output
lands in *this* directory (``recreate-deleted-wikidata/``), which no submitter
reads: ``modern-quickstatements/submit_daily_batch.py`` consumes a fixed
filename allowlist, and ``select_label_proposals.py`` globs only
``shinto-label-generator/quickstatements/*.txt``. Recreation is deliberately
human-gated — Wikidata item creation is off-limits autonomously (CLAUDE.md), and
these targets (minor medieval figures / small shrines) were plausibly deleted
for non-notability, so each needs a human's notability call before submission.

Data model (investigated 2026-07-05):
  * The category's *pages* already have their OWN ``{{wikidata link|Q…}}``. The
    deleted QIDs belong to the ill *targets* (sub-topics), NOT the pages — so
    this does NOT emit ``P11250|"shinto:<PageName>"`` (that would duplicate the
    page's existing item — the "re-deleted" failure the task warns against).
  * Each deleted ill preserves the original deleted QID in its ``dd=`` param
    (added after an earlier bug overwrote the QID into the link target and lost
    it). We carry that QID as a ``#`` provenance comment only — a deleted QID
    can't be reused; ``CREATE`` mints a new one.

Each ``CREATE`` block carries only AUTHORITATIVE, on-page facts — English label,
per-language labels, and a jawiki sitelink when the ill's ja link is present and
NOT flagged invalid (the sitelink is the notability anchor that keeps the item
from being re-deleted). No P31/type claims are guessed. Targets with no valid
sitelink are still emitted but flagged in the companion review, since they are
the ones most at risk of re-deletion and most need a human's eye.

Outputs (``--apply``): ``recreate_quickstatements.txt`` (the CREATE blocks) and
``review.md`` (human-readable). Default dry-run prints a summary. ``--run-tag``
accepted for template consistency (unused — no wiki write).
"""

import argparse
import io
import os
import re
import sys
import time

import requests

WIKI_API = "https://shinto.miraheze.org/w/api.php"
USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
READ_THROTTLE = 0.25

SOURCE_CATEGORY = "Pages with deleted QID in ill template"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
QS_PATH = os.path.join(SCRIPT_DIR, "recreate_quickstatements.txt")
REVIEW_PATH = os.path.join(SCRIPT_DIR, "review.md")

_DELETED_ILL_RE = re.compile(r"\{\{\s*ill\s*\|([^{}]*DELETED_QID[^{}]*)\}\}", re.IGNORECASE)
_LANG_RE = re.compile(r"^[a-z][a-z-]{1,11}$")
_QID_RE = re.compile(r"^Q\d+$")


def parse_deleted_ill(inner: str) -> dict:
    """Parse the inside of a DELETED_QID ``{{ill|…}}`` into recreation facts.
    Pure — no network.

    Returns ``{"label", "langlinks": [(lang, title)], "deleted_qid", "notes",
    "ja_invalid"}``. ``label`` = positional arg 0 (English display name);
    ``langlinks`` = alternating positional ``lang|title`` pairs; ``deleted_qid``
    = original QID from ``dd=`` (or ""); ``notes`` = ``*_comment=`` annotations;
    ``ja_invalid`` = True if a comment marks the jawiki link invalid."""
    parts = [p.strip() for p in inner.split("|")]
    positional: list[str] = []
    deleted_qid = ""
    notes: list[str] = []
    ja_invalid = False
    for i, p in enumerate(parts):
        if "=" in p:
            key, _, val = p.partition("=")
            key = key.strip().lower()
            val = val.strip()
            if key == "dd" and _QID_RE.match(val):
                deleted_qid = val
            elif key.endswith("comment") and val:
                notes.append(val)
                if "invalid" in val.lower():
                    ja_invalid = True
            continue
        if i == 0 or p:
            positional.append(p)

    label = positional[0] if positional else ""
    # Data-integrity recovery: an earlier bug wrote the DELETED QID into the link
    # TITLE slot (positional[0]), destroying the English name. If the label slot
    # is a bare QID, it is NOT a name — it is the recovered original deleted QID;
    # the English name is lost (other-language labels below may survive).
    if _QID_RE.match(label):
        if not deleted_qid:
            deleted_qid = label
        label = ""
    langlinks: list[tuple[str, str]] = []
    rest = positional[1:]
    j = 0
    while j < len(rest) - 1:
        lang, title = rest[j], rest[j + 1]
        if _LANG_RE.match(lang) and title:
            langlinks.append((lang, title))
            j += 2
        else:
            j += 1
    return {"label": label, "langlinks": langlinks, "deleted_qid": deleted_qid,
            "notes": notes, "ja_invalid": ja_invalid}


def _qs_str(value: str) -> str:
    """QuickStatements string literal. Collapse embedded double-quotes (QS has no
    robust escape) and strip pipes/newlines that would break the TSV line."""
    v = value.replace('"', "'").replace("|", "/").replace("\n", " ").strip()
    return f'"{v}"'


def render_create_block(target: dict, source_page: str,
                        ja_article_exists: "bool | None" = None,
                        existing_qid: str = "") -> list[str]:
    """Render one ``CREATE`` block (list of QuickStatements lines) for a deleted
    ill target. Pure — no network.

    A ``#`` provenance comment records the original deleted QID (from ``dd=``) +
    source page. The jawiki sitelink (the notability anchor) is emitted only when
    the ja link is present, NOT flagged invalid, and the article is not known to
    be missing (``ja_article_exists`` False suppresses it; None = unknown, keep).
    If ``existing_qid`` is set, the ja article is already linked to a LIVE item —
    a ``# ⚠ ALREADY …`` note is prepended so the reviewer skips a duplicate.
    Comments are for the human reviewer; this file is never auto-submitted."""
    lines: list[str] = []
    prov = f"was {target['deleted_qid']}" if target["deleted_qid"] else "original QID lost"
    lines.append(f"# recreate deleted ill target ({prov}) — from [[{source_page}]]")
    if existing_qid:
        lines.append(f"# ⚠ ALREADY: ja article is linked to live {existing_qid} — "
                     "likely a DUPLICATE; verify before creating.")
    lines.append("CREATE")
    if target["label"]:
        lines.append(f"LAST\tLen\t{_qs_str(target['label'])}")
    ja_title = ""
    for lang, title in target["langlinks"]:
        lines.append(f"LAST\tL{lang}\t{_qs_str(title)}")
        if lang == "ja":
            ja_title = title
    if ja_title and not target["ja_invalid"] and ja_article_exists is not False \
            and not existing_qid:
        lines.append(f"LAST\tSjawiki\t{_qs_str(ja_title)}")
    return lines


def _get_json(url: str, params: dict, retries: int = 4):
    last = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params,
                                headers={"User-Agent": USER_AGENT}, timeout=60)
            if resp.status_code >= 500:
                last = f"HTTP {resp.status_code}"
                time.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last = str(e)
            time.sleep(2 * (attempt + 1))
    print(f"  [warn] request failed after {retries} retries: {last}")
    return None


def get_category_pages() -> "tuple[list[str], bool]":
    members: list[str] = []
    cont: dict = {}
    complete = True
    while True:
        params = {
            "action": "query", "list": "categorymembers",
            "cmtitle": "Category:" + SOURCE_CATEGORY, "cmtype": "page",
            "cmlimit": "500", "format": "json",
        }
        params.update(cont)
        r = _get_json(WIKI_API, params)
        if r is None:
            complete = False
            break
        members += [m["title"] for m in
                    r.get("query", {}).get("categorymembers", [])]
        if "continue" in r:
            cont = r["continue"]
            time.sleep(READ_THROTTLE)
        else:
            break
    return members, complete


def fetch_page_texts(titles: "list[str]") -> dict:
    out: dict = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        r = _get_json(WIKI_API, {
            "action": "query", "titles": "|".join(batch), "prop": "revisions",
            "rvprop": "content", "rvslots": "main", "formatversion": "2",
            "format": "json",
        })
        if r is None:
            time.sleep(READ_THROTTLE)
            continue
        for pg in r.get("query", {}).get("pages", []):
            if pg.get("missing"):
                continue
            revs = pg.get("revisions") or []
            if revs:
                out[pg["title"]] = revs[0]["slots"]["main"]["content"]
        time.sleep(READ_THROTTLE)
    return out


WD_API = "https://www.wikidata.org/w/api.php"


def fetch_ja_enrichment(ja_titles: "list[str]") -> "dict":
    """For each ja article title, look up (to the extent Wikidata allows) whether
    a LIVE Wikidata item is already linked to it. Returns {ja_title: live_qid}
    for titles whose jawiki article is currently sitelinked to an existing item
    (i.e. probable duplicates — do NOT recreate). Titles absent from the result
    are either unlinked (safe to sitelink) or non-existent."""
    out: dict = {}
    uniq = sorted(set(t for t in ja_titles if t))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get_json(WD_API, {
            "action": "wbgetentities", "sites": "jawiki",
            "titles": "|".join(batch), "props": "sitelinks", "format": "json",
        })
        if r is None:
            time.sleep(READ_THROTTLE)
            continue
        for qid, e in r.get("entities", {}).items():
            if qid.startswith("-") or "missing" in e:
                continue
            ja = (e.get("sitelinks", {}).get("jawiki", {}) or {}).get("title", "")
            if ja:
                out[ja] = qid
        time.sleep(READ_THROTTLE)
    return out


def fetch_ja_article_existence(ja_titles: "list[str]") -> "set":
    """Return the set of ja titles whose jawiki article currently exists (so a
    sitelink would resolve). Uses the jawiki API `query` (missing flag)."""
    exists: set = set()
    uniq = sorted(set(t for t in ja_titles if t))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get_json("https://ja.wikipedia.org/w/api.php", {
            "action": "query", "titles": "|".join(batch),
            "formatversion": "2", "format": "json",
        })
        if r is None:
            time.sleep(READ_THROTTLE)
            continue
        for pg in r.get("query", {}).get("pages", []):
            if not pg.get("missing"):
                exists.add(pg.get("title", ""))
        time.sleep(READ_THROTTLE)
    return exists


def deleted_targets_for_page(text: str) -> "list[dict]":
    seen: set = set()
    targets: list[dict] = []
    for inner in _DELETED_ILL_RE.findall(text):
        t = parse_deleted_ill(inner)
        if not t["label"] and not t["langlinks"]:
            continue  # nothing recoverable (no name in any language)
        key = (t["label"], tuple(t["langlinks"]))
        if key in seen:
            continue
        seen.add(key)
        targets.append(t)
    return targets


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="Write recreate_quickstatements.txt + review.md "
                             "(default: dry-run summary).")
    parser.add_argument("--run-tag", default="",
                        help="Accepted for template consistency; unused.")
    args = parser.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    pages, complete = get_category_pages()
    print(f"Pages in [[Category:{SOURCE_CATEGORY}]]: {len(pages)}"
          f"{'' if complete else '  (PARTIAL)'}")
    texts = fetch_page_texts(pages)
    if len(texts) < len(pages):
        complete = False

    # (page, target) pairs, globally deduped by (label, langlinks).
    seen: set = set()
    entries: "list[tuple[str, dict]]" = []
    for p in sorted(pages):
        for t in deleted_targets_for_page(texts.get(p, "")):
            key = (t["label"], tuple(sorted(t["langlinks"])), t["deleted_qid"])
            if key in seen:
                continue
            seen.add(key)
            entries.append((p, t))

    # Enrichment (Wikidata, to the extent possible): which ja articles are
    # already linked to a LIVE item (probable duplicates → don't recreate), and
    # which ja articles exist at all (gate the sitelink to real ones).
    ja_titles = [ti for _, t in entries for l, ti in t["langlinks"] if l == "ja"]
    existing = fetch_ja_enrichment(ja_titles) if ja_titles else {}
    ja_exists = fetch_ja_article_existence(ja_titles) if ja_titles else set()
    print(f"  ja links: {len(set(ja_titles))}  |  already linked to a live item: "
          f"{len(existing)}  |  ja article exists: {len(ja_exists)}")

    def _enrich(t):
        ja = next((ti for l, ti in t["langlinks"] if l == "ja"), "")
        return {"existing_qid": existing.get(ja, ""),
                "ja_article_exists": (ja in ja_exists) if ja else None}

    with_qid = sum(1 for _, t in entries if t["deleted_qid"])
    safe_sitelink = sum(1 for _, t in entries
                        if (e := _enrich(t))["ja_article_exists"] and not e["existing_qid"]
                        and not t["ja_invalid"])
    dup = sum(1 for _, t in entries if _enrich(t)["existing_qid"])
    print(f"Distinct deleted targets: {len(entries)}  |  with original QID "
          f"(dd=): {with_qid}  |  safe jawiki sitelink: {safe_sitelink}  |  "
          f"probable duplicates: {dup}")
    print("Sample CREATE:")
    for p, t in entries[:3]:
        e = _enrich(t)
        for ln in render_create_block(t, p, **e):
            print("  " + ln)

    if not args.apply:
        print(f"\n[DRY] would write {len(entries)} CREATE blocks to "
              f"{os.path.relpath(QS_PATH, SCRIPT_DIR)} + review.md")
        return

    with open(QS_PATH, "w", encoding="utf-8") as f:
        f.write("# Recreate deleted-QID ill targets — QuickStatements (HUMAN-GATED, "
                "NOT auto-submitted). See generate_recreate_quickstatements.py.\n")
        if not complete:
            f.write("# ⚠ PARTIAL PASS — enumeration/fetch truncated; incomplete.\n")
        for p, t in entries:
            f.write("\n".join(render_create_block(t, p, **_enrich(t))) + "\n\n")
    print(f"Wrote {QS_PATH} ({len(entries)} CREATE blocks)")

    with open(REVIEW_PATH, "w", encoding="utf-8") as f:
        f.write("# Deleted-QID ill targets — recreation review\n\n")
        f.write(f"Distinct targets: **{len(entries)}** · with original QID "
                f"(`dd=`): **{with_qid}** · safe jawiki sitelink (notability "
                f"anchor): **{safe_sitelink}** · probable duplicates (ja already "
                f"linked to a live item): **{dup}**. QuickStatements in "
                "`recreate_quickstatements.txt` — human-gated, not auto-submitted."
                "\n\n")
        if not complete:
            f.write("> **⚠ PARTIAL PASS** — incomplete.\n\n")
        f.write("Targets **without** a notability anchor (no existing ja article "
                "to sitelink, and not already a live item) are most at risk of "
                "re-deletion — do per-item research before submitting:\n\n")
        for p, t in entries:
            e = _enrich(t)
            if e["existing_qid"] or (e["ja_article_exists"] and not t["ja_invalid"]):
                continue
            links = ", ".join(f"{l}:{ti}" for l, ti in t["langlinks"]) or "—"
            name = t["label"] or "(en name lost)"
            f.write(f"- **{name}** ({links}) · `{t['deleted_qid'] or 'QID lost'}` "
                    f"· from [[{p}]]\n")
    print(f"Wrote {REVIEW_PATH}")


if __name__ == "__main__":
    main()
