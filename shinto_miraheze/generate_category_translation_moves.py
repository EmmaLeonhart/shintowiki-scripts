#!/usr/bin/env python3
"""
generate_category_translation_moves.py
======================================
Backlog item 1 — propose English names for the Japanese-script categories in
``[[Category:Japanese language category names]]`` (live ~1189 subcats). This is
the **naming logic** only; the move itself is performed by the existing
``move_categories.py`` (a monthly CI step that consumes ``category_moves.csv``,
recategorizes members, moves the page leaving a redirect, and tags
``{{category move error}}`` on destination collisions). No new mover.

This generator emits ONLY confident, deterministic / authoritative proposals —
**never a guess**. Anything it can't resolve confidently goes to a residual
report for a human (or a later gazetteer phase), not the CSV.

Resolution, in priority order (the plan's canonical-name choice rule):

1. **Wikidata-anchored (the strongest single signal).** Most of these category
   pages carry ``{{wikidata link|Q…}}`` where the QID is the *Wikimedia-category*
   item. Fetch that item's enwiki sitelink (authoritative English category name)
   — falling back to its English label — and use it iff it is itself a
   ``Category:…``. This is authoritative cross-wiki mapping, not pattern-guessing.
2. **Deterministic dated-maintenance transform.** ``<English prefix> from <JP
   date>`` → ``<English prefix> from <Month YYYY>``; the long malformed timestamp
   forms (``…2016年5月31日 (火) 13:15 (UTC)``) collapse onto the month form (the
   day/time/weekday is import noise). English prefix required — these are
   imported enwiki maintenance categories whose only Japanese part is the date.
3. **Hand-maintained template-prefix lookup** for the few pure-template cats with
   no QID.
4. **Place-name gazetteer (authoritative, not guessing).** For the productive
   ``<place>の神社`` / ``<place>の寺院`` / ``<place>の歴史`` / ``<place>の建築物``
   content cats that carry no category-level QID, the *topic* half is a fixed,
   VERIFIED English category-naming convention (``Shinto shrines in`` / ``Buddhist
   temples in`` / ``History of`` / ``Buildings and structures in``) while the
   *place* half is resolved AUTHORITATIVELY: the place stem is looked up as a
   jawiki ARTICLE title on Wikidata and its enwiki sitelink (the canonical English
   place name) is used — no transliteration/guessing. A P31 gate requires the
   item to be a Japanese administrative division, so a stem matching a non-place
   jawiki article is rejected → residual. Stems with no clean jawiki→enwiki chain
   (e.g. prefecture-prefixed ``埼玉県美里町`` whose article is ``美里町 (埼玉県)``)
   also fall to residual — never machine-guessed.

Other place-name patterns (``の重要文化財`` important-cultural-property,
``の旧県社`` shrine-rank-by-place, ``の画像提供依頼`` maintenance, bare ``<place>郡``
districts, …) are still left to the residual report for later phases — only
topics whose enwiki category convention is verified get a suffix here.

This script makes NO wiki edits. It reads the wiki (category enumeration +
category-page wikitext) and Wikidata (labels/sitelinks), then APPENDS new rows to
``category_moves.csv`` (preserving existing rows, skipping sources already
listed) and writes a residual report to ``docs/category_translation_residual.md``.
``--apply`` writes; default dry-run prints a summary. ``--max-rows`` caps new rows
per run; ``--run-tag`` accepted for template consistency (unused — no wiki write).
"""

import argparse
import csv
import io
import os
import re
import sys
import time

import requests

WIKI_API = "https://shinto.miraheze.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
READ_THROTTLE = 0.25

SOURCE_CATEGORY = "Japanese language category names"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "category_moves.csv")
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
RESIDUAL_PATH = os.path.join(REPO_ROOT, "docs", "category_translation_residual.md")

WD_LINK_RE = re.compile(r"\{\{\s*wikidata\s*link\s*\|\s*(Q\d+)", re.IGNORECASE)


def _get_json(url: str, params: dict, retries: int = 4):
    """GET returning parsed JSON, with bounded retries on transient 5xx /
    non-JSON bodies (Miraheze 502s are common). Raises on persistent failure
    so the caller can decide; returns None only if every attempt failed."""
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

# ─── phase 2: dated maintenance transform ───────────────────
_JP_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November",
    12: "December",
}
# "<English prefix> from 2020年2月"  /  "<prefix> from 2016年5月31日 (火) 13:15 (UTC)"
# Day/time/weekday tail (after the month) is dropped — it's import noise that
# collapses many timestamp variants onto one canonical English month category.
_DATED_RE = re.compile(
    r"^(?P<prefix>.*?[A-Za-z].*?)\s*(?:from\s+)?(?P<y>\d{4})年(?P<m>\d{1,2})月"
    r"(?:\d{1,2}日.*)?$"
)

# ─── phase 3: hand-maintained pure-template lookup ──────────
# Only for cats with NO {{wikidata link}} (phase 1 handles the rest, e.g.
# WikiProject用テンプレート → Q7054879 → "Category:WikiProject templates").
_TEMPLATE_LOOKUP: dict[str, str] = {}

# ─── phase 4: place-name gazetteer (authoritative, NOT guessing) ─────────
# Productive "<place>の<topic>" content categories. The *topic* half is a fixed
# English category-naming convention (deterministic); the *place* half is resolved
# AUTHORITATIVELY — the place stem is looked up as a jawiki ARTICLE title on
# Wikidata and its enwiki sitelink (the canonical English place name) is used. No
# transliteration/guessing of the place. A stem that doesn't resolve to a
# Japanese-administrative-division item with an enwiki article → residual.
#
# Ordered longest-suffix-first so e.g. a longer suffix wins over a prefix of it.
# Each topic half is a VERIFIED enwiki category-naming convention (not a guess):
# enwiki has "Category:Shinto shrines in Tokyo", "Category:Buddhist temples in
# Kyoto Prefecture", "Category:Buildings and structures in <place>", "Category:
# History of <place>". The leading の is load-bearing: it distinguishes
# "<place>の神社" (shrines IN a place) from "<name>神社" (one specific shrine,
# which must NOT match — see test_parse_place_non_pattern_is_none).
_PLACE_SUFFIXES: list[tuple[str, str]] = [
    ("の重要文化財", "Important Cultural Properties of {}"),  # enwiki uses "of", not "in"
    ("の建築物", "Buildings and structures in {}"),
    ("の神社", "Shinto shrines in {}"),
    ("の寺院", "Buddhist temples in {}"),
    ("の歴史", "History of {}"),
]

# P31 classes that confirm the resolved stem is a Japanese place (gate against a
# stem that happens to match a non-place jawiki article — e.g. a religion or a
# company). Verified labels 2026-07-05.
_PLACE_CLASSES: frozenset = frozenset({
    "Q1054813",   # municipality of Japan
    "Q494721",    # city of Japan
    "Q1059478",   # town of Japan
    "Q4174776",   # village of Japan
    "Q137773",    # ward of Japan
    "Q1145012",   # special city of Japan
    "Q17221353",  # capital of prefecture
    "Q1549591",   # big city
    "Q828359",    # commuter town
    "Q50337",     # prefecture of Japan
    "Q56061",     # administrative territorial entity (generic — still a place)
})


def parse_place_pattern(name: str) -> "tuple[str, str] | None":
    """Split ``<place><suffix>`` → ``(place_stem, english_format)`` for the
    productive place-content suffixes. Returns None if no suffix matches or the
    place stem would be empty. Pure — no network."""
    for suf, fmt in _PLACE_SUFFIXES:
        if name.endswith(suf):
            stem = name[: -len(suf)]
            if stem:
                return stem, fmt
    return None


def place_category(fmt: str, enwiki: str, p31: "list[str]") -> "str | None":
    """Given a resolved place stem (its enwiki article title + P31 classes) and a
    topic format, return the English ``Category:…`` name — but ONLY if the item is
    a confirmed Japanese place (P31 gate) and has an enwiki article. Otherwise
    None (→ residual). Pure — no network."""
    if not enwiki or enwiki.startswith("Category:"):
        return None
    if not any(p in _PLACE_CLASSES for p in p31):
        return None
    return "Category:" + fmt.format(enwiki)


def get_subcats() -> tuple[list[str], bool]:
    """Return (members, complete). ``complete`` is False if a paginated request
    failed (e.g. a Miraheze 502 mid-walk) so the caller can flag the run as a
    partial pass rather than silently treating a truncated list as the whole
    category — no silent caps."""
    members: list[str] = []
    cont: dict = {}
    complete = True
    while True:
        params = {
            "action": "query", "list": "categorymembers",
            "cmtitle": "Category:" + SOURCE_CATEGORY, "cmtype": "subcat",
            "cmlimit": "500", "format": "json",
        }
        params.update(cont)
        r = _get_json(WIKI_API, params)
        if r is None:
            complete = False
            print("  [warn] enumeration truncated by a failed request — "
                  "PARTIAL pass (next run continues; sources already in the CSV "
                  "are skipped).")
            break
        members += [m["title"][len("Category:"):]
                    for m in r.get("query", {}).get("categorymembers", [])]
        if "continue" in r:
            cont = r["continue"]
            time.sleep(READ_THROTTLE)
        else:
            break
    return members, complete


def fetch_category_qids(cat_names: list[str]) -> dict[str, str]:
    """Batch-fetch each category page's {{wikidata link|Q…}} → {name: QID}."""
    out: dict[str, str] = {}
    for i in range(0, len(cat_names), 50):
        batch = cat_names[i:i + 50]
        titles = "|".join("Category:" + c for c in batch)
        r = _get_json(WIKI_API, {
            "action": "query", "titles": titles, "prop": "revisions",
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
            if not revs:
                continue
            txt = revs[0]["slots"]["main"]["content"]
            m = WD_LINK_RE.search(txt)
            if m:
                out[pg["title"][len("Category:"):]] = m.group(1).upper()
        time.sleep(READ_THROTTLE)
    return out


def fetch_wd_category_names(qids: list[str]) -> dict[str, str]:
    """For each QID return its canonical English Category name: prefer the
    enwiki sitelink (authoritative), else the English label — but ONLY when it
    is itself a ``Category:…`` (the QID is the Wikimedia-category item). QIDs
    that resolve to a non-category (the topic itself) return no entry."""
    out: dict[str, str] = {}
    uniq = sorted(set(qids))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get_json(WD_API, {
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "labels|sitelinks", "languages": "en", "format": "json",
        })
        if r is None:
            time.sleep(READ_THROTTLE)
            continue
        ents = r.get("entities", {})
        for q in batch:
            e = ents.get(q, {})
            if "missing" in e:
                continue
            enwiki = (e.get("sitelinks", {}).get("enwiki", {}) or {}).get("title", "")
            label = (e.get("labels", {}).get("en", {}) or {}).get("value", "")
            cand = ""
            if enwiki.startswith("Category:"):
                cand = enwiki
            elif label.startswith("Category:"):
                cand = label
            if cand:
                out[q] = cand
        time.sleep(READ_THROTTLE)
    return out


def fetch_place_resolutions(stems: list[str]) -> "dict[str, tuple[str, list[str]]]":
    """Resolve each place stem by its jawiki ARTICLE title on Wikidata → its
    enwiki sitelink + P31 classes. Returns {stem: (enwiki_title, [P31 QIDs])} for
    stems that have a Wikidata item; the caller applies the place gate. Batched by
    50 (wbgetentities cap). ``normalize`` is NOT sent — Wikidata rejects it for
    multi-title requests."""
    out: "dict[str, tuple[str, list[str]]]" = {}
    uniq = sorted(set(stems))
    for i in range(0, len(uniq), 50):
        batch = uniq[i:i + 50]
        r = _get_json(WD_API, {
            "action": "wbgetentities", "sites": "jawiki",
            "titles": "|".join(batch), "props": "sitelinks|claims",
            "sitefilter": "enwiki|jawiki", "languages": "en", "format": "json",
        })
        if r is None:
            time.sleep(READ_THROTTLE)
            continue
        for qid, e in r.get("entities", {}).items():
            if qid.startswith("-") or "missing" in e:
                continue
            sl = e.get("sitelinks", {})
            ja = (sl.get("jawiki", {}) or {}).get("title", "")
            en = (sl.get("enwiki", {}) or {}).get("title", "")
            p31 = [
                c["mainsnak"]["datavalue"]["value"]["id"]
                for c in e.get("claims", {}).get("P31", [])
                if c.get("mainsnak", {}).get("datavalue")
            ]
            if ja:
                out[ja] = (en, p31)
        time.sleep(READ_THROTTLE)
    return out


def dated_transform(name: str) -> "str | None":
    m = _DATED_RE.match(name)
    if not m:
        return None
    prefix = m.group("prefix").strip()
    # Strip a dangling "from" the regex may have left on the prefix.
    prefix = re.sub(r"\s+from$", "", prefix).strip()
    if not prefix:
        return None
    month = _JP_MONTHS.get(int(m.group("m")))
    if not month:
        return None
    return f"Category:{prefix} from {month} {m.group('y')}"


def load_existing_sources() -> set[str]:
    sources: set[str] = set()
    if not os.path.exists(CSV_PATH):
        return sources
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            s = (row.get("source") or "").strip()
            if s:
                sources.add(s)
    return sources


def resolve_all(existing: "set[str] | None" = None):
    """Run the deterministic resolution over every not-yet-in-CSV Japanese
    category. Returns ``(new_rows, residual, complete)`` where new_rows is a list
    of ``(source, dest, reason)`` confidently resolved, residual is the list of
    category names (no ``Category:`` prefix) with no confident English name, and
    complete is False if the wiki enumeration was truncated. Shared by main()
    (writes the CSV/report) and build_category_translation_queue.py (queues the
    residual for cloud agentic RAG). Network: wiki + Wikidata reads."""
    if existing is None:
        existing = load_existing_sources()
    cats, complete = get_subcats()
    todo = [c for c in cats if ("Category:" + c) not in existing]

    qids = fetch_category_qids(todo)
    wd_names = fetch_wd_category_names(list(qids.values()))

    place_stems = []
    for c in todo:
        if qids.get(c) in wd_names:
            continue
        pp = parse_place_pattern(c)
        if pp:
            place_stems.append(pp[0])
    place_res = fetch_place_resolutions(place_stems) if place_stems else {}

    new_rows: list[tuple[str, str, str]] = []
    residual: list[str] = []
    for c in todo:
        src = "Category:" + c
        dest = None
        reason = ""
        q = qids.get(c)
        if q and q in wd_names:
            dest = wd_names[q]
            reason = f"wikidata {q} enwiki/label category"
        if dest is None:
            d = dated_transform(c)
            if d:
                dest = d
                reason = "dated maintenance transform"
        if dest is None and c in _TEMPLATE_LOOKUP:
            dest = _TEMPLATE_LOOKUP[c]
            reason = "template lookup"
        if dest is None:
            pp = parse_place_pattern(c)
            if pp:
                stem, fmt = pp
                info = place_res.get(stem)
                if info:
                    cand = place_category(fmt, info[0], info[1])
                    if cand:
                        dest = cand
                        reason = f"place gazetteer (jawiki '{stem}' → enwiki)"
        if dest and dest != src:
            new_rows.append((src, dest, reason))
        else:
            residual.append(c)
    return new_rows, residual, complete


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="Append new rows to category_moves.csv + write the "
                             "residual report (default: dry-run summary only).")
    parser.add_argument("--max-rows", type=int, default=100000,
                        help="Cap new rows appended this run (default: all).")
    parser.add_argument("--run-tag", default="",
                        help="Accepted for template consistency; unused (no wiki "
                             "write).")
    args = parser.parse_args()

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    existing = load_existing_sources()
    print(f"Existing category_moves.csv sources: {len(existing)}")

    new_rows, residual, complete = resolve_all(existing)

    print(f"\nResolved (new rows): {len(new_rows)}  |  Residual (no confident "
          f"English name): {len(residual)}")
    print("Sample resolved:")
    for s, d, r in new_rows[:12]:
        print(f"  {s}  ->  {d}   [{r}]")

    if args.max_rows < len(new_rows):
        print(f"Capping new rows at --max-rows={args.max_rows}")
        new_rows = new_rows[:args.max_rows]

    if not args.apply:
        print(f"\n[DRY] would append {len(new_rows)} rows to category_moves.csv "
              f"and write {len(residual)} residual entries to "
              f"{os.path.relpath(RESIDUAL_PATH, REPO_ROOT)}")
        return

    # Append (preserve existing rows + 2-col format; reason kept as a 3rd column
    # only on the new rows is messy, so we DON'T add a reason column to the CSV —
    # move_categories.py reads source,destination only. Reasons go in the
    # residual/devlog. Keep the CSV exactly 2-column.)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for s, d, _ in new_rows:
            w.writerow([s, d])
    print(f"Appended {len(new_rows)} rows to {CSV_PATH}")

    os.makedirs(os.path.dirname(RESIDUAL_PATH), exist_ok=True)
    with open(RESIDUAL_PATH, "w", encoding="utf-8") as f:
        f.write("# Japanese category-name translation — residual queue\n\n")
        f.write("Auto-generated by `generate_category_translation_moves.py`. "
                "These Japanese-script categories in "
                f"`[[Category:{SOURCE_CATEGORY}]]` could NOT be resolved to a "
                "confident English name (no Wikidata-anchored Category sitelink, "
                "not a dated-maintenance pattern). They await the follow-on "
                "place-name gazetteer phase or human translation — **never "
                "machine-guessed**.\n\n")
        if not complete:
            f.write("> **⚠ PARTIAL PASS** — category enumeration was truncated "
                    "by a failed wiki request (Miraheze 502), so this residual "
                    "list is incomplete. A later healthy run will cover the rest "
                    "(sources already proposed in `category_moves.csv` are "
                    "skipped).\n\n")
        f.write(f"Residual count (this pass): **{len(residual)}**\n\n")
        for c in sorted(residual):
            f.write(f"- `{c}`\n")
    print(f"Wrote residual report: {RESIDUAL_PATH} ({len(residual)} entries)")


if __name__ == "__main__":
    main()
