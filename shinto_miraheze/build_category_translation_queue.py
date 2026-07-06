#!/usr/bin/env python3
"""
build_category_translation_queue.py
===================================
Queue item 5 — agentic RAG the ENTIRE category-translation residual (Emma
2026-07-06: "do agentic RAG on the entire residual going 100% all in"). The
deterministic resolver (``generate_category_translation_moves.resolve_all``)
only handles Wikidata-anchored + verified-convention cases and drops everything
else into a *residual* — but that residual is NOT out of scope. This script
writes one work-file per residual category into ``category_translation/`` so the
cloud remote routine (``remote_queue.py`` → ``remote_queue.json``) can research
each and fill in a canonical English ``Category:`` name. ``collect_category_
translations.py`` then folds the finished answers into ``category_moves.csv``,
which the monthly ``move_categories`` step already consumes.

Why a file per category (not a mechanical guess): RAG's job is exactly the
research a script can't do — read the members, the jawiki equivalent, the
Wikidata context, and pick the real English category name. So each file carries
that context: a sample of the category's members + the category page's own
wikitext (which may hold ``{{wikidata link}}`` / interwiki hints).

Read-only on the wiki. Writes local files only; ``remote_queue.py`` picks them
up on its next rebuild. Skips a category whose work-file already exists.
"""
import io
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
import generate_category_translation_moves as g  # noqa: E402

OUT_DIR = os.path.join(REPO_ROOT, "category_translation")
WIKI_API = "https://shinto.miraheze.org/w/api.php"
USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
READ_THROTTLE = 0.25


def _safe_filename(cat_name: str) -> str:
    """Match sync_git_synced_pages.title_to_filename: ':' → '%3A', '/' → '%2F'.
    The category name has no 'Category:' prefix here; we store the full title."""
    title = "Category:" + cat_name
    return title.replace(":", "%3A").replace("/", "%2F") + ".wiki"


def _member_sample(cat_name: str, limit: int = 25) -> list[str]:
    d = g._get_json(WIKI_API, {
        "action": "query", "list": "categorymembers",
        "cmtitle": "Category:" + cat_name, "cmlimit": str(limit), "format": "json",
    })
    if not d:
        return []
    return [m["title"] for m in d.get("query", {}).get("categorymembers", [])]


def _page_wikitext(cat_name: str) -> str:
    d = g._get_json(WIKI_API, {
        "action": "query", "titles": "Category:" + cat_name, "prop": "revisions",
        "rvprop": "content", "rvslots": "main", "formatversion": "2", "format": "json",
    })
    if not d:
        return ""
    for pg in d.get("query", {}).get("pages", []):
        if pg.get("missing"):
            return ""
        revs = pg.get("revisions") or []
        if revs:
            return revs[0]["slots"]["main"]["content"]
    return ""


def _work_file(cat_name: str, members: list[str], wikitext: str) -> str:
    src = "Category:" + cat_name
    lines = [
        f"<!-- SOURCE: {src} -->",
        "<!-- TRANSLATED: -->",
        "<!-- TASK: replace the empty TRANSLATED marker above with the canonical "
        "English 'Category:...' name for this Japanese-named category. Research it "
        "— use the member sample + the category wikitext + the jawiki/Wikidata "
        "equivalent. Follow real enwiki category-naming conventions; do NOT invent "
        "or transliterate blindly. When the TRANSLATED marker is filled, this file "
        "is done (collect_category_translations.py folds it into category_moves.csv "
        "and deletes it). If genuinely untranslatable, leave TRANSLATED empty and "
        "add a line '<!-- SKIP: <reason> -->'. -->",
        "",
        "== Members (sample) ==",
    ]
    lines += [f"* {m}" for m in members] or ["(empty category)"]
    lines += ["", "== Category page wikitext ==", "<pre>", wikitext.rstrip(), "</pre>", ""]
    return "\n".join(lines)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Resolving deterministically to find the residual…")
    _new_rows, residual, complete = g.resolve_all()
    print(f"Residual to queue for RAG: {len(residual)}"
          f"{'' if complete else '  (PARTIAL enumeration)'}")

    written = skipped = 0
    for cat_name in residual:
        path = os.path.join(OUT_DIR, _safe_filename(cat_name))
        if os.path.exists(path):
            skipped += 1
            continue
        members = _member_sample(cat_name)
        time.sleep(READ_THROTTLE)
        wikitext = _page_wikitext(cat_name)
        time.sleep(READ_THROTTLE)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(_work_file(cat_name, members, wikitext))
        written += 1
        if written % 25 == 0:
            print(f"  … {written} work-files written")
    print(f"Wrote {written} category_translation/*.wiki work-files; "
          f"skipped {skipped} (already present).")


if __name__ == "__main__":
    main()
