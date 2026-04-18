#!/usr/bin/env python3
"""
create_shrine_ranking_pages.py
================================================
Create article pages for shrine rankings that have categories but no articles.
Uses the Gō-sha page as a template.

TEMPORARY SCRIPT — intended to run once to create all missing shrine ranking
articles, then be removed from the workflow.

For each subcategory of [[Category:Shrine rankings needing pages]]:
1. Checks if an article page with the same name exists
2. If the category has a {{wikidata link|Q...}}, queries Wikidata P301
   for the article QID
3. Creates the article with appropriate content
"""

import argparse
import io
import os
import re
import sys
import time

import mwclient
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
THROTTLE = 2.5

# ─── JAPANESE NAMES AND METADATA ────────────────────────────
# Maps normalized article title (lowercase) to metadata
ARTICLE_META = {
    "bekkaku kanpeisha": {"japanese": "別格官幣社", "system": "modern", "ja_link": "別格官幣社"},
    "kanpei taisha":     {"japanese": "官幣大社",   "system": "modern", "ja_link": "官幣大社"},
    "kanpei chūsha":     {"japanese": "官幣中社",   "system": "modern", "ja_link": "官幣中社"},
    "kanpei shōsha":     {"japanese": "官幣小社",   "system": "modern", "ja_link": "官幣小社"},
    "kokuhei taisha":    {"japanese": "国幣大社",   "system": "modern", "ja_link": "国幣大社"},
    "kokuhei chūsha":    {"japanese": "国幣中社",   "system": "modern", "ja_link": "国幣中社"},
    "kokuhei shōsha":    {"japanese": "国幣小社",   "system": "modern", "ja_link": "国幣小社"},
    "fu-sha":            {"japanese": "府社",       "system": "modern", "ja_link": "府社"},
    "ken-sha":           {"japanese": "県社",       "system": "modern", "ja_link": "県社"},
    "fuken-sha":         {"japanese": "府県社",     "system": "modern", "ja_link": "府県社"},
    "gō-sha":            {"japanese": "郷社",       "system": "modern", "ja_link": "郷社"},
    "son-sha":           {"japanese": "村社",       "system": "modern", "ja_link": "村社"},
    "unranked shrines":  {"japanese": "無格社",     "system": "modern", "ja_link": "無格社",
                          "nihongo_title": "Mukaku-sha"},
    "myōjin taisha":     {"japanese": "名神大社",   "system": "engishiki", "ja_link": "名神大社"},
    "shikinai taisha":   {"japanese": "式内大社",   "system": "engishiki", "ja_link": "式内大社"},
    "shikinai shōsha":   {"japanese": "式内小社",   "system": "engishiki", "ja_link": "式内小社"},
    # Engishiki offering classifications
    "shrines receiving hoe and quiver":
        {"system": "engishiki_offering"},
    "shrines receiving hoe offering":
        {"system": "engishiki_offering"},
    "shrines receiving quiver offering":
        {"system": "engishiki_offering"},
    "shrines receiving tsukinami-sai and niiname-sai and ainame-sai offerings":
        {"system": "engishiki_offering"},
    "shrines receiving tsukinami-sai and niiname-sai offerings":
        {"system": "engishiki_offering"},
}

WIKIDATA_LINK_RE = re.compile(r'\{\{wikidata link\|([Qq]\d+)\}\}')


def query_wikidata_p301(cat_qid):
    """Query Wikidata for P301 (category's main topic) of a category QID."""
    url = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT ?mainTopic ?mainTopicLabel WHERE {{
      wd:{cat_qid} wdt:P301 ?mainTopic .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,ja". }}
    }}
    """
    headers = {"Accept": "application/json", "User-Agent": "ShrineRankingPageBot/1.0"}
    try:
        resp = requests.get(url, params={"query": query, "format": "json"},
                            headers=headers, timeout=30)
        resp.raise_for_status()
        results = resp.json().get("results", {}).get("bindings", [])
        if results:
            main_topic_uri = results[0]["mainTopic"]["value"]
            qid = main_topic_uri.split("/")[-1]
            label = results[0].get("mainTopicLabel", {}).get("value", "")
            return qid, label
    except Exception as e:
        print(f"  Warning: Wikidata query failed for {cat_qid}: {e}")
    return None, None


def _system_link(system):
    if system == "modern":
        return "[[modern system of ranked Shinto shrines]]"
    elif system in ("engishiki", "engishiki_offering"):
        return "[[Engishiki Jinmyōchō]]"
    return "Shinto shrine ranking system"


def generate_article_text(title, category_name, meta, wikidata_qid=None):
    """Generate wikitext for a shrine ranking article page."""
    lines = []

    system = meta.get("system", "")
    japanese = meta.get("japanese")
    nihongo_title = meta.get("nihongo_title", title)
    ja_link = meta.get("ja_link")

    # Japanese interwiki
    if ja_link:
        lines.append(f"<!--interwikis from wikidata-->[[ja:{ja_link}]]")

    # Opening paragraph
    if japanese:
        lines.append(f"{{{{nihongo|'''{nihongo_title}'''|{japanese}}}}} is a rank "
                      f"in the {_system_link(system)}.")
    elif system == "engishiki_offering":
        lines.append(f"'''{title}''' is a classification of shrines "
                      f"in the {_system_link(system)}.")
    else:
        lines.append(f"'''{title}''' is a rank in the {_system_link(system)}.")

    # See Also
    lines.append("")
    lines.append("== See Also ==")
    lines.append(f"* [[:Category:{category_name}|Category for the rank]]")

    # Wikidata link
    if wikidata_qid:
        lines.append(f"{{{{wikidata link|{wikidata_qid}}}}}")

    # Categories
    lines.append(f"[[Category:{category_name}|*]]")
    lines.append("[[Category:Shrine rankings]]")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Actually create pages (default is dry-run).")
    parser.add_argument("--max-edits", type=int, default=0,
                        help="Max pages to create (0 = no limit).")
    parser.add_argument("--run-tag", required=True,
                        help="Wiki-formatted run tag link for edit summaries.")
    args = parser.parse_args()

    site = mwclient.Site(
        WIKI_URL, path=WIKI_PATH,
        clients_useragent="ShrineRankingPageBot/1.0 (User:EmmaBot; shinto.miraheze.org)",
    )
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    # Get subcategories of "Shrine rankings needing pages"
    parent_cat = site.categories["Shrine rankings needing pages"]
    subcats = []
    for page in parent_cat.members(namespace=14):  # namespace 14 = Category
        cat_name = page.name.replace("Category:", "")
        subcats.append(cat_name)

    print(f"Found {len(subcats)} subcategories")

    created = 0
    skipped_exists = 0
    skipped_no_meta = 0

    for cat_name in subcats:
        article_title = cat_name
        print(f"\n--- {article_title} ---")

        if args.max_edits and created >= args.max_edits:
            print("  Max edits reached, stopping.")
            break

        # Check if article already exists
        page = site.pages[article_title]
        if page.exists:
            print(f"  SKIP: already exists")
            skipped_exists += 1
            continue

        # Look up metadata
        key = article_title.lower()
        meta = ARTICLE_META.get(key)
        if not meta:
            print(f"  WARNING: no metadata for '{article_title}', skipping")
            skipped_no_meta += 1
            continue

        # Check category page for wikidata link
        cat_page = site.pages[f"Category:{cat_name}"]
        cat_text = cat_page.text() if cat_page.exists else ""
        wikidata_qid = None

        wd_match = WIKIDATA_LINK_RE.search(cat_text)
        if wd_match:
            cat_qid = wd_match.group(1)
            print(f"  Category wikidata: {cat_qid}")
            article_qid, wd_label = query_wikidata_p301(cat_qid)
            if article_qid:
                wikidata_qid = article_qid
                print(f"  P301 → {article_qid} ({wd_label})")
            else:
                print(f"  Warning: no P301 for {cat_qid}")
            time.sleep(0.5)
        else:
            print(f"  No wikidata on category")

        # Generate article text
        article_text = generate_article_text(article_title, cat_name, meta, wikidata_qid)

        if args.apply:
            try:
                page.save(article_text,
                          summary=f"Bot: create shrine ranking article {args.run_tag}")
                print(f"  CREATED")
                created += 1
                time.sleep(THROTTLE)
            except Exception as e:
                print(f"  ERROR: {e}")
        else:
            print(f"  DRY RUN: would create with text:")
            for line in article_text.strip().split("\n"):
                print(f"    {line}")

    print(f"\nDone. Created: {created}, Skipped (exists): {skipped_exists}, "
          f"Skipped (no meta): {skipped_no_meta}")


if __name__ == "__main__":
    main()
