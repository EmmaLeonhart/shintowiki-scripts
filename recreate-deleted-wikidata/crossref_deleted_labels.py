#!/usr/bin/env python3
"""
crossref_deleted_labels.py
==========================
Backlog #8 enrichment — recover recreation content for the deleted
Immanuelle-created Wikidata items by cross-referencing them against the
**fandom wiki** (shinto.fandom.com).

Why fandom, not miraheze (Emma 2026-07-05):
  * The authoritative list of *which* QIDs were deleted + their English labels
    comes from the public Wikidata deletion logs (``rag_deleted_logs.py`` →
    ``deleted_log_rag.json``): 273 items carry a clean recovered label.
  * The deleted-item CONTENT (per-language labels, the page it belongs to) lives
    in the shinto ``{{ill}}`` templates. On BOTH miraheze and fandom the current
    ill has had its QID overwritten to the literal ``qid=DELETED_QID`` by the
    ``deleted_qids_in_ill`` op — but the ill's positional **langlinks survive**,
    and the ORIGINAL QID is preserved in fandom's **page history** (proven: the
    pre-overwrite revision of ``Niwa-tsume no Mikoto`` carried ``Q135579706``,
    matching the RAG). Fandom also is NOT Cloudflare-blocked, so this is
    verifiable from a dev session — unlike miraheze.

For each recovered label this finds the fandom page carrying the matching
``{{ill|<label>|…}}`` and pulls:
  * the ill's per-language langlinks (recreation labels, present even after the
    QID overwrite);
  * the current ill QID (``qid=``/``dd=`` — usually ``DELETED_QID`` or, when
    preserved, a real Q that should match the RAG);
  * the host page + whether that page carries a live ``{{wikidata link|Q…}}``.

``--deep`` additionally walks the fandom page history to recover the ORIGINAL
QID and validate it against the RAG (expensive — one content fetch per revision).

Outputs (``--apply``): ``shinto_wiki_crossref.md`` + ``.json``. READ-ONLY (no
writes). Bails on HTTP 429. Pure ill-matching / extraction logic is unit-tested
(``tests/``). Default is a dry-run summary. ``--run-tag`` accepted for template
consistency (unused).
"""
import argparse
import io
import json
import os
import re
import sys
import time
from collections import Counter

import requests

FANDOM_API = "https://shinto.fandom.com/api.php"
USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
READ_THROTTLE = 0.3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAG_JSON = os.path.join(SCRIPT_DIR, "deleted_log_rag.json")
OUT_MD = os.path.join(SCRIPT_DIR, "shinto_wiki_crossref.md")
OUT_JSON = os.path.join(SCRIPT_DIR, "shinto_wiki_crossref.json")

_ILL_RE = re.compile(r"\{\{\s*ill\s*\|([^{}]*)\}\}", re.IGNORECASE)
_WD_LINK_RE = re.compile(r"\{\{\s*wikidata link\s*\|\s*(Q\d+)", re.IGNORECASE)
_JA_SITELINK_RE = re.compile(r"\[\[\s*:?\s*ja\s*:\s*([^\]|]+)", re.IGNORECASE)
_CAT_RE = re.compile(r"\[\[\s*Category\s*:\s*([^\]|]+)", re.IGNORECASE)
_QID_PARAM_RE = re.compile(r"^(?:qid|wd|dd)$", re.IGNORECASE)
_QID_RE = re.compile(r"^Q\d+$")
_LANG_RE = re.compile(r"^[a-z][a-z-]{1,11}$")


# ─────────────────────────── pure logic (unit-tested) ───────────────────────────

def parse_ill(inner: str) -> dict:
    """Parse an ``{{ill|…}}`` body into {label, langlinks{lang:title}, qid}.

    ``label`` = positional arg 0 (or the ``lt=`` display override if present);
    ``qid`` = the value of any ``qid``/``WD``/``dd`` param that is a real Q
    (``DELETED_QID`` and other non-Q values are ignored → qid="")."""
    parts = [p.strip() for p in inner.split("|")]
    positional, langlinks, qid, lt = [], {}, "", ""
    for p in parts:
        if "=" in p:
            k, _, v = p.partition("=")
            k, v = k.strip().lower(), v.strip()
            if _QID_PARAM_RE.match(k) and _QID_RE.match(v):
                qid = v
            elif k == "lt":
                lt = v
            continue
        positional.append(p)
    label = lt or (positional[0] if positional else "")
    rest = positional[1:]
    j = 0
    while j < len(rest) - 1:
        lang, title = rest[j], rest[j + 1]
        if _LANG_RE.match(lang) and title:
            langlinks[lang] = title
            j += 2
        else:
            j += 1
    return {"label": label, "langlinks": langlinks, "qid": qid}


def ill_matches_label(inner: str, label: str) -> bool:
    """True if this ill's target/display label equals the wanted label."""
    parsed = parse_ill(inner)
    if parsed["label"] == label:
        return True
    # also allow the raw positional[0] to match (lt= may differ from target)
    first = next((p.strip() for p in inner.split("|")[:1]), "")
    return first == label


def find_ill(text: str, label: str) -> "dict|None":
    for m in _ILL_RE.finditer(text or ""):
        if ill_matches_label(m.group(1), label):
            return parse_ill(m.group(1))
    return None


def page_wikidata_qid(text: str) -> "str|None":
    m = _WD_LINK_RE.search(text or "")
    return m.group(1) if m else None


def page_signals(text: str) -> dict:
    """Host-page context for a recreated item: does it already have a live item,
    its jawiki sitelink (notability anchor), and its categories (type signal)."""
    text = text or ""
    ja = _JA_SITELINK_RE.search(text)
    return {
        "page_wikidata_qid": page_wikidata_qid(text),
        "ja_sitelink": ja.group(1).strip() if ja else None,
        "categories": [c.strip() for c in _CAT_RE.findall(text)],
    }


def md_cell(s) -> str:
    return str(s if s is not None else "").replace("|", "\\|")


# ─────────────────────────── fandom I/O ───────────────────────────

def _get_json(params: dict, retries: int = 4):
    params = {**params, "format": "json"}
    for attempt in range(retries):
        try:
            resp = requests.get(FANDOM_API, params=params,
                                headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code == 429:
                print("HTTP 429 from fandom — bailing (CLAUDE.md policy).")
                sys.exit(2)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def search_pages(label: str, limit: int = 5):
    d = _get_json({"action": "query", "list": "search",
                   "srsearch": f'"{label}"', "srlimit": limit})
    return [h["title"] for h in d.get("query", {}).get("search", [])]


def fetch_content(title: str, revid: "int|None" = None) -> str:
    params = {"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main"}
    if revid:
        params["revids"] = revid
    else:
        params["titles"] = title
    d = _get_json(params)
    for p in d.get("query", {}).get("pages", {}).values():
        revs = p.get("revisions")
        if revs:
            return revs[0].get("slots", {}).get("main", {}).get("*", "") or ""
    return ""


def recover_original_qid(title: str, label: str, batch: int = 40):
    """Recover the pre-overwrite QID from fandom history for the ill on `title`.

    Optimised: fetches a batch of revisions WITH content in one API call
    (newest→oldest) and scans locally for the newest revision where the ill for
    `label` still carried a real qid — rather than one call per revision.
    Returns (qid, timestamp) or (None, None)."""
    d = _get_json({"action": "query", "prop": "revisions", "titles": title,
                   "rvprop": "content|timestamp|ids", "rvslots": "main",
                   "rvlimit": batch})
    for p in d.get("query", {}).get("pages", {}).values():
        for r in p.get("revisions", []):
            txt = r.get("slots", {}).get("main", {}).get("*", "") or ""
            parsed = find_ill(txt, label)
            if parsed and parsed["qid"]:
                return parsed["qid"], r.get("timestamp")
    return None, None


# ─────────────────────────── driver ───────────────────────────

def load_labels():
    recs = json.load(open(RAG_JSON, encoding="utf-8"))
    seen, out = set(), []
    for r in recs:
        label = r.get("content_was") or ""
        if not label and r.get("ill_labels"):
            label = next((v for v in r["ill_labels"]), "")
        if label and label not in seen:
            seen.add(label)
            out.append({"qid": r["qid"], "label": label,
                        "size": r.get("size"), "bucket": r.get("bucket")})
    return out


def crossref_one(item, deep=False):
    """Gather as-thorough-as-possible info for one deleted item (Emma 2026-07-05):
    aggregate langlinks across EVERY fandom page whose ill matches the label, plus
    the primary host page's categories / jawiki sitelink / existing-item check, and
    (deep) the original QID from history."""
    label = item["label"]
    langlinks, host_pages = {}, []
    current_qid = ""
    primary = None
    for title in search_pages(label):
        text = fetch_content(title)
        time.sleep(READ_THROTTLE)
        parsed = find_ill(text, label)
        if parsed is None:
            continue
        host_pages.append(title)
        langlinks.update(parsed["langlinks"])       # union across pages
        current_qid = current_qid or parsed["qid"]
        if primary is None:
            primary = {"title": title, "signals": page_signals(text)}

    if primary is None:
        return {**item, "fandom_page": None, "host_pages": [], "langlinks": {},
                "current_ill_qid": "", "recovered_qid": None, "qid_source": None,
                "page_wikidata_qid": None, "ja_sitelink": None, "categories": [],
                "matched": False, "qid_matches_rag": False}

    rec = {**item,
           "fandom_page": primary["title"], "host_pages": host_pages,
           "langlinks": langlinks, "current_ill_qid": current_qid,
           "recovered_qid": current_qid or None,
           "qid_source": "current-ill" if current_qid else None,
           "page_wikidata_qid": primary["signals"]["page_wikidata_qid"],
           "ja_sitelink": primary["signals"]["ja_sitelink"],
           "categories": primary["signals"]["categories"],
           "matched": True}
    if not rec["recovered_qid"] and deep:
        rq, ts = recover_original_qid(primary["title"], label)
        time.sleep(READ_THROTTLE)
        if rq:
            rec["recovered_qid"] = rq
            rec["qid_source"] = f"history({ts})"
    rec["qid_matches_rag"] = bool(rec["recovered_qid"]) and rec["recovered_qid"] == item["qid"]
    return rec


def render(results):
    matched = [r for r in results if r["matched"]]
    with_ll = [r for r in matched if r["langlinks"]]
    validated = [r for r in matched if r["qid_matches_rag"]]
    with_ja = [r for r in matched if r.get("ja_sitelink")]
    lines = ["# Deleted-item labels × fandom wiki — cross-reference\n",
             "Auto-generated by `crossref_deleted_labels.py`. Recovers as-thorough-as-possible "
             "recreation info per deleted Immanuelle Wikidata item from the fandom `{{ill}}` "
             "templates + host pages (read-only). The RAG gives QID+label+deletion-reason; "
             "fandom gives per-language langlinks (union across all referencing pages), the host "
             "page's categories + jawiki sitelink + the host page's own item (context — the "
             "deleted entity is a sub-topic *on* that page, not the page itself), and "
             "(`--deep`) the original QID from page history.\n",
             f"- Labels cross-referenced: **{len(results)}**",
             f"- Matched a fandom ill: **{len(matched)}**",
             f"- With per-language langlinks (recreation content): **{len(with_ll)}**",
             f"- With a jawiki sitelink (notability anchor): **{len(with_ja)}**",
             f"- Original QID recovered AND matches the RAG deleted QID: **{len(validated)}**\n",
             "## Per-item (sorted by richest first)\n",
             "Columns: `host item` = the fandom page's OWN wikidata item (context for the "
             "relationship/sitelink, NOT the deleted entity — that entity is the ill target).\n",
             "| deleted QID | label | del reason | fandom page | langs | ja sitelink | host item | recovered QID | src | ✓RAG | categories |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(results, key=lambda r: (-len(r["langlinks"]), not r["matched"])):
        langs = ",".join(sorted(r["langlinks"])) if r["langlinks"] else ""
        cats = "; ".join(r.get("categories", [])[:4])
        lines.append(
            f"| {r['qid']} | {md_cell(r['label'])} | {md_cell(r.get('bucket'))} "
            f"| {md_cell(r['fandom_page'])} | {md_cell(langs)} | {md_cell(r.get('ja_sitelink'))} "
            f"| {md_cell(r.get('page_wikidata_qid'))} | {md_cell(r['recovered_qid'])} "
            f"| {md_cell(r['qid_source'])} | {'✓' if r['qid_matches_rag'] else ''} | {md_cell(cats)} |")
    return "\n".join(lines) + "\n"


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the report (default: dry-run summary)")
    ap.add_argument("--deep", action="store_true", help="walk fandom history to recover original QIDs (slow)")
    ap.add_argument("--max", type=int, default=0, help="cap labels processed (0 = all)")
    ap.add_argument("--run-tag", default="", help="accepted for template consistency (unused)")
    args = ap.parse_args()

    labels = load_labels()
    if args.max:
        labels = labels[:args.max]
    print(f"Cross-referencing {len(labels)} recovered labels against fandom (deep={args.deep})...")

    results = []
    for i, item in enumerate(labels, 1):
        results.append(crossref_one(item, deep=args.deep))
        if i % 25 == 0:
            m = sum(1 for r in results if r["matched"])
            print(f"  ...{i}/{len(labels)}  (matched {m})")

    matched = sum(1 for r in results if r["matched"])
    with_ll = sum(1 for r in results if r["langlinks"])
    print(f"Matched {matched}; with langlinks {with_ll}.")
    if not args.apply:
        print("(dry-run — pass --apply to write the report)")
        return
    open(OUT_MD, "w", encoding="utf-8").write(render(results))
    json.dump(results, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Wrote {OUT_MD} and {OUT_JSON}")


if __name__ == "__main__":
    main()
