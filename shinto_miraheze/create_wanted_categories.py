"""
create_wanted_categories.py
============================
Creates category pages for all "wanted categories" (categories that have
members but no category page). Each page gets a single line:
    [[Category:categories made during git consolidation]]

Also creates the parent category page itself if it doesn't exist.

Run dry-run first:
    python create_wanted_categories.py --dry-run
"""

import time
import mwclient
import argparse
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
THROTTLE  = 1.5

PARENT_CAT = "categories made during git consolidation"
CONTENT    = f"[[Category:{PARENT_CAT}]]"

DUP_QID_CAT = "Duplicated qid category redirects"
DUP_QID_CONTENT = """\
Pages in this category are Q{QID} mainspace pages where two or more \
category pages share the same Wikidata QID. Each page is a disambiguation \
list in the format:

<pre>
# [[:Category:Foo]]
# [[:Category:Bar]]
[[Category:Duplicated qid category redirects]]
</pre>

The [[:Category:]] colon prefix is intentional — it links to the category \
rather than adding the Q page to that category.

To resolve a page in this category: determine which category correctly holds \
the QID, then replace the disambiguation list with a standard \
<code>#REDIRECT [[Category:Name]]</code> and remove the category tag.

[[Category:categories made during git consolidation]]"""

WANTED_CATEGORIES = [
    "Categories in qq but actually having wikidata",
    "Qq but with jawiki",
    "Qq old",
    "Categories in Categories in qq but actually having wikidata but actually having wikidata",
    "Templates with Documentation template",
    "Duplicated qid category redirects",
    "Categories in qq but actually having wikidata but with jawiki",
    "Qqqqqqq",
    "Articles with incorrect citation syntax",
    "Cqq",
    "Cqq but with jawiki",
    "Nnnnnnnnn",
    "Pages with jalink",
    "Cqq old",
    "Kkkkkkkkkkkkkk",
    "Qqqqqqqqqqqqqqqqqqqqqqq",
    "Generated x-no-miya lists",
    "I think I cleared all the incomplete or blank pages earlier",
    "Pages which might possibly be incomplete but are most likely complete",
    "Pages with ISSN errors",
    "Articles using Template:Designation with invalid designation",
    "Articles missing coordinates with coordinates on Wikidata",
    "Articles requiring unit attention",
    "TEMPLATES",
    "Wikipedia soft redirects to nonexistent targets",
    "Articles needing additional references from December 2025",
    "Articles containing Bulgarian-language text",
    "Articles containing Icelandic-language text",
    "Wikipedia page with obscure country",
    "Articles containing Belarusian-language text",
    "Articles containing Catalan-language text",
    "Articles containing Classical Nahuatl-language text",
    "Articles containing Corsican-language text",
    "Articles containing Czech-language text",
    "Articles containing Estonian-language text",
    "Articles containing Faroese-language text",
    "Articles containing Finnish-language text",
    "Articles containing Irish-language text",
    "Articles containing Middle Dutch (ca. 1050-1350)-language text",
    "Articles containing Middle English (1100-1500)-language text",
    "Articles containing Old Frisian-language text",
    "Articles containing Old High German (ca. 750-1050)-language text",
    "Articles containing Portuguese-language text",
    "Articles containing Romanian-language text",
    "Articles containing Sardinian-language text",
    "Articles containing Scottish Gaelic-language text",
    "Articles containing Serbian-language text",
    "Articles containing Slovak-language text",
    "Articles containing Slovene-language text",
    "Articles containing Spanish-language text",
    "Articles containing Swedish-language text",
    "Articles containing Turkish-language text",
    "Articles containing Ukrainian-language text",
    "Articles containing Welsh-language text",
    "Articles with unsourced statements from August 2024",
    "Articles with unsourced statements from March 2020",
    "Pages using infobox military installation with unknown parameters",
    "テンプレート呼び出しエラーのあるページ/Template:和暦",
    "Accuracy disputes from August 2023",
    "Ares",
    "Articles containing Armenian-language text",
    "Articles containing Chamorro-language text",
    "Articles containing Church Slavonic-language text",
    "Articles containing Croatian-language text",
    "Articles containing Filipino-language text",
    "Articles containing Georgian-language text",
    "Articles containing Hungarian-language text",
    "Articles containing Latvian-language text",
    "Articles containing Lithuanian-language text",
    "Articles containing Macedonian-language text",
    "Articles containing Manx-language text",
    "Articles containing Middle Low German-language text",
    "Articles containing Māori-language text",
    "Articles containing Norwegian-language text",
    "Articles containing Nynorsk-language text",
    "Articles containing Old Norse-language text",
    "Articles containing Saterland Frisian-language text",
    "Articles containing Serbo-Croatian-language text",
    "Articles containing Tajik-language text",
    "Articles containing Venetian-language text",
    "Articles containing West Frisian-language text",
    "Articles containing Yiddish-language text",
    "Articles containing uncoded-language text",
    "Articles lacking sources from 10 July 2019 (Wed) 03:29 (UTC)",
    "Articles lacking sources from 14 June 2016 (Tue) 12:41 (UTC)",
    "Articles lacking sources from 14 June 2016 (Tue) 12:46 (UTC)",
    "Articles lacking sources from 14 June 2016 (Tue) 12:49 (UTC)",
    "Articles lacking sources from 19 March 2015 (Thu) 14:52 (UTC)",
    "Articles lacking sources from 1 January 2023 (Sun) 13:23 (UTC)",
    "Articles lacking sources from 26 October 2014 (Sun) 04:27 (UTC)",
    "Articles lacking sources from 27 October 2014 (Mon) 12:49 (UTC)",
    "Articles lacking sources from December 2017",
    "Articles lacking sources from February 2020",
    "Articles lacking sources from July 2020",
    "Articles lacking sources from June 20, 2015 (Sat) 04:19 (UTC)",
    "Articles lacking sources from October 2025",
    "Articles lacking sources from October 26, 2014 (Sun) 11:38 (UTC)",
    "Articles lacking sources from October 27, 2014 (Mon) 12:50 (UTC)",
    "Articles needing a sentence or phrase to be explained from July 2018",
    "Articles needing additional references from January 2008",
    "Articles needing additional references from November 2014",
    "Articles that may contain original research from April 2020",
    "Articles that may contain original research from March 2021",
    "Articles to be expanded from August 2020",
    "Articles with empty sections from August 2020",
    "Articles with incomplete citations from November 2011",
    "Articles with text in Nahuatl languages",
    "Articles with trivia sections from January 2026",
    "Articles with unsourced statements from 2014-10-26 (Sun) 04:19 (UTC)",
    "Articles with unsourced statements from 2014-10-27 (Mon) 11:43 (UTC)",
    "Articles with unsourced statements from 2015-01-11 (Sun) 13:17 (UTC)",
    "Articles with unsourced statements from 2018-05-16 (Wed) 10:15 (UTC)",
    "Articles with unsourced statements from 2022-01-06 (Thu) 13:02 (UTC)",
    "Articles with unsourced statements from 2025-09",
    "Articles with unsourced statements from August 2025",
    "Articles with unsourced statements from August 7, 2017 (Mon) 07:49 (UTC)",
    "Articles with unsourced statements from June 2024",
    "Articles with unsourced statements from June 2025",
    "Articles with unsourced statements from October 2021",
    "Buildings and structures in Awaji City",
    "Buildings and structures in Suzuka City",
    "Country data templates of Belarus",
    "Country data templates of Bhutan",
    "Country data templates of subdivisions of the Soviet Union",
    "Cronus",
    "Eastern Christian liturgy",
    "Fasting",
    "Former prefectural shrines in Mie Prefecture",
    "Friday",
    "Fujisan Hongū Sengen Taisha",
    "Furutsu-Hachimanyama Kofun",
    "Hermes",
    "History of Awaji City",
    "History of Suzuka City",
    "Ichinomiya 2",
    "Monday",
    "Odin",
    "Old Pages",
    "Pages containing broken anchor template with unsupported parameters",
    "Pages using infobox film with flag icon",
    "Pages with bad rounding precision",
    "Prefectural People's 100 Selected Buildings",
    "Saturday",
    "Selene",
    "Shimazu Island",
    "States and territories established in the 1950s",
    "Thor",
    "Thursday",
    "Tuesday",
    "Use dmy dates from December 2014",
    "Wednesday",
    "Zeus",
]


def create_category(site, title, dry_run):
    page = site.pages[f"Category:{title}"]
    if page.exists:
        print(f"  SKIP (exists): Category:{title}")
        return
    if dry_run:
        print(f"  DRY RUN: would create Category:{title}")
        return
    page.save(CONTENT, summary="Create wanted category page (git consolidation cleanup)")
    print(f"  CREATED: Category:{title}")
    time.sleep(THROTTLE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done without editing")
    args = parser.parse_args()

    site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                         clients_useragent="WantedCategoryBot/1.0 (User:Immanuelle; shinto.miraheze.org)")
    site.login(USERNAME, PASSWORD)
    print(f"Logged in as {USERNAME}\n")

    # Create parent category first
    print(f"--- Parent category ---")
    create_category(site, PARENT_CAT, args.dry_run)
    print()

    # Create all wanted categories (special content for dup QID category)
    print(f"--- Wanted categories ({len(WANTED_CATEGORIES)}) ---")
    for cat in WANTED_CATEGORIES:
        if cat == DUP_QID_CAT:
            page = site.pages[f"Category:{cat}"]
            if page.exists:
                print(f"  SKIP (exists): Category:{cat}")
            elif args.dry_run:
                print(f"  DRY RUN: would create Category:{cat} (with special docs)")
            else:
                page.save(DUP_QID_CONTENT, summary="Create wanted category page with documentation (git consolidation cleanup)")
                print(f"  CREATED (with docs): Category:{cat}")
                time.sleep(THROTTLE)
        else:
            create_category(site, cat, args.dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
