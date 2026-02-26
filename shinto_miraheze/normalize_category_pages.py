"""
normalize_category_pages.py
===========================
Normalizes Category: pages to a strict structure that keeps only:
1) templates
2) interwiki links
3) category links

Output layout:
<!--templates-->
...templates...
<!--interwikis-->
...interwiki links...
<!--categories-->
...category links...

Default mode is dry-run. Use --apply to save.
"""

import argparse
import io
import re
import sys
import time

import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
THROTTLE = 1.5

CATEGORY_LINE_RE = re.compile(r"^\s*\[\[\s*Category\s*:[^\]]+\]\]\s*$", re.IGNORECASE)
INTERWIKI_LINE_RE = re.compile(r"^\s*\[\[\s*[a-z][a-z0-9-]{1,15}\s*:[^\]]+\]\]\s*$", re.IGNORECASE)
REDIRECT_RE = re.compile(r"^\s*#redirect\b", re.IGNORECASE)


def dedupe_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        key = item.strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def extract_top_level_templates(text):
    templates = []
    depth = 0
    start = None
    i = 0

    while i < len(text):
        two = text[i:i + 2]
        if two == "{{":
            if depth == 0:
                start = i
            depth += 1
            i += 2
            continue
        if two == "}}" and depth > 0:
            depth -= 1
            i += 2
            if depth == 0 and start is not None:
                block = text[start:i].strip()
                if block:
                    templates.append(block)
                start = None
            continue
        i += 1

    return dedupe_preserve_order(templates)


def extract_interwikis_and_categories(text):
    interwikis = []
    categories = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if CATEGORY_LINE_RE.match(line):
            categories.append(line)
            continue
        if INTERWIKI_LINE_RE.match(line):
            # Keep only language interwikis; skip local namespace links like [[Category:...]]
            if not line.lower().startswith("[[category:"):
                interwikis.append(line)
    return dedupe_preserve_order(interwikis), dedupe_preserve_order(categories)


def build_normalized_text(text):
    templates = extract_top_level_templates(text)
    interwikis, categories = extract_interwikis_and_categories(text)

    lines = []
    lines.append("<!--templates-->")
    lines.extend(templates)
    lines.append("<!--interwikis-->")
    lines.extend(interwikis)
    lines.append("<!--categories-->")
    lines.extend(categories)
    return "\n".join(lines).rstrip() + "\n"


def iter_category_titles(site, start_title=None, include_redirects=False):
    params = {
        "list": "allpages",
        "apnamespace": 14,
        "aplimit": "max",
    }
    if not include_redirects:
        params["apfilterredir"] = "nonredirects"
    if start_title:
        params["apfrom"] = start_title

    while True:
        result = site.api("query", **params)
        for entry in result.get("query", {}).get("allpages", []):
            yield entry["title"]
        if "continue" in result:
            params.update(result["continue"])
        else:
            break


def parse_titles_arg(titles_arg):
    if not titles_arg:
        return []
    return [t.strip() for t in titles_arg.split(",") if t.strip()]


def parse_titles_file(path):
    titles = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                titles.append(s)
    return titles


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Save edits (default is dry-run).")
    parser.add_argument("--limit", type=int, default=0, help="Max pages to process (0 = no limit).")
    parser.add_argument("--start-title", default="", help="Start title for full category scan.")
    parser.add_argument("--titles", default="", help="Comma-separated category titles to process.")
    parser.add_argument("--titles-file", default="", help="Path to newline-delimited category titles.")
    parser.add_argument("--include-redirects", action="store_true", help="Include redirect category pages.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL,
        path=WIKI_PATH,
        clients_useragent="CategoryNormalizerBot/1.0 (User:Immanuelle; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    explicit_titles = []
    explicit_titles.extend(parse_titles_arg(args.titles))
    if args.titles_file:
        explicit_titles.extend(parse_titles_file(args.titles_file))
    explicit_titles = list(dict.fromkeys(explicit_titles))

    if explicit_titles:
        titles_iter = iter(explicit_titles)
        print(f"Processing explicit list: {len(explicit_titles)} categories")
    else:
        titles_iter = iter_category_titles(
            site,
            start_title=args.start_title or None,
            include_redirects=args.include_redirects,
        )
        print("Processing all category pages")

    processed = edited = skipped = errors = 0
    api_nochange = 0

    for title in titles_iter:
        if args.limit and processed >= args.limit:
            break
        if not title.startswith("Category:"):
            title = f"Category:{title}"

        processed += 1
        page = site.pages[title]
        prefix = f"[{processed}] {title}"

        try:
            text = page.text() if page.exists else ""
        except Exception as e:
            print(f"{prefix} ERROR reading page: {e}")
            errors += 1
            continue

        if not text:
            print(f"{prefix} SKIP (missing or empty)")
            skipped += 1
            continue

        if REDIRECT_RE.match(text) and not args.include_redirects:
            print(f"{prefix} SKIP (redirect)")
            skipped += 1
            continue

        new_text = build_normalized_text(text)
        if not args.apply:
            changed = (text.rstrip() != new_text.rstrip())
            print(f"{prefix} DRY RUN {'would edit' if changed else 'no change'}")
            continue

        try:
            page.save(
                new_text,
                summary="Bot: normalize category page structure (templates/interwikis/categories only)",
            )
            edited += 1
            print(f"{prefix} EDITED")
            time.sleep(THROTTLE)
        except Exception as e:
            msg = str(e).lower()
            if "nochange" in msg:
                api_nochange += 1
                print(f"{prefix} NOCHANGE returned by API")
            else:
                errors += 1
                print(f"{prefix} ERROR saving page: {e}")

    print("\n" + "=" * 60)
    print(
        f"Done. Processed: {processed} | Edited: {edited} | "
        f"Skipped: {skipped} | Errors: {errors} | Mode: {'APPLY' if args.apply else 'DRY-RUN'}"
    )
    print(f"API nochange responses: {api_nochange}")


if __name__ == "__main__":
    main()
