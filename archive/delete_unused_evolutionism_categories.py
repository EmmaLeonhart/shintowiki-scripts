#!/usr/bin/env python3
"""
Delete all unused categories from evolutionism.miraheze.org
This script deletes approximately 300+ unused categories in a single batch operation.
"""

import sys
import io
import time
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wiki credentials
WIKI_URL = 'evolutionism.miraheze.org'
WIKI_PATH = '/w/'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

# Categories to delete
CATEGORIES = [
    "1805 births",
    "1840s assassinated politicians",
    "1844 deaths",
    "1995",
    "1997",
    "1998",
    "1999",
    "2000",
    "2001",
    "2002",
    "2003",
    "2004",
    "2005",
    "2006",
    "2007",
    "2008",
    "2009",
    "2010",
    "2011",
    "2012",
    "2013",
    "2014",
    "2015",
    "2016",
    "2017",
    "2018",
    "2019",
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
    "2026",
    "10th century",
    "11th century",
    "12th century",
    "13th century",
    "14th century",
    "15th century",
    "16th century",
    "17th century",
    "18th century",
    "19th century",
    "1st century",
    "2nd century",
    "3rd century",
    "4th century",
    "5th century",
    "6th century",
    "7th century",
    "8th century",
    "9th century",
    "20th century",
    "21st century",
    "American people of Armenian descent",
    "American people of Austrian descent",
    "American people of Belgian descent",
    "American people of Bulgarian descent",
    "American people of Cambodian descent",
    "American people of Canadian descent",
    "American people of Chilean descent",
    "American people of Chinese descent",
    "American people of Colombian descent",
    "American people of Cuban descent",
    "American people of Cypriot descent",
    "American people of Czech descent",
    "American people of Danish descent",
    "American people of Dutch descent",
    "American people of Egyptian descent",
    "American people of Emirati descent",
    "American people of English descent",
    "American people of Estonian descent",
    "American people of Finnish descent",
    "American people of French descent",
    "American people of German descent",
    "American people of Greek descent",
    "American people of Haitian descent",
    "American people of Hungarian descent",
    "American people of Icelandic descent",
    "American people of Indian descent",
    "American people of Indonesian descent",
    "American people of Irish descent",
    "American people of Israeli descent",
    "American people of Italian descent",
    "American people of Jamaican descent",
    "American people of Japanese descent",
    "American people of Korean descent",
    "American people of Laotian descent",
    "American people of Lebanese descent",
    "American people of Lithuanian descent",
    "American people of Macedonian descent",
    "American people of Malaysian descent",
    "American people of Mexican descent",
    "American people of Moroccan descent",
    "American people of Norwegian descent",
    "American people of Pakistani descent",
    "American people of Polish descent",
    "American people of Portuguese descent",
    "American people of Romanian descent",
    "American people of Russian descent",
    "American people of Scottish descent",
    "American people of Serbian descent",
    "American people of Slovak descent",
    "American people of Spanish descent",
    "American people of Swedish descent",
    "American people of Swiss descent",
    "American people of Syrian descent",
    "American people of Taiwanese descent",
    "American people of Thai descent",
    "American people of Turkish descent",
    "American people of Ukrainian descent",
    "American people of Welsh descent",
    "American people of Bangladeshi descent",
    "American people of Maltese descent",
    "American people of Burmese descent",
    "American people of Palestinian descent",
    "Articles needing additional references from February 2022",
    "Articles needing additional references from September 2023",
    "Articles needing additional references from January 2024",
    "Articles needing additional categories from February 2024",
    "Articles needing additional categories from April 2024",
    "Articles with multiple issues",
    "Articles with no identifiers",
    "Articles with an hcard",
    "Articles with unsourced statements from August 2022",
    "Articles with unsourced statements from February 2022",
    "Articles with unsourced statements from September 2022",
    "Articles with unsourced statements from November 2023",
    "Articles with unsourced statements from November 2024",
    "All pages needing cleanup",
    "Cleanup tagged articles without a reason field from June 2019",
    "All articles needing cleanup",
    "Wikipedia articles needing clarification from May 2022",
    "Cleanup tagged articles without a reason field from August 2018",
    "Cleanup tagged articles without a reason field from January 2024",
    "Articles with incomplete citations from August 2017",
    "Excess whitespace",
    "Wikipedia articles needing style cleanup from June 2024",
    "Wikipedia articles in need of updating from August 2022",
    "Wikipedia articles in need of updating from March 2023",
    "Wikipedia articles in need of updating from September 2022",
    "Wikipedia article stubs",
    "Stubs",
    "All stub articles",
    "All accuracy disputes",
    "All pages with unwanted transclusions",
    "Articles with disputed statements from August 2022",
    "Articles with disputed statements from May 2023",
    "Articles with disputed statements from March 2024",
    "Biographies of living people with no birth date",
    "Probable hoaxes",
    "Use dmy dates from January 2019",
    "Use dmy dates from May 2021",
    "Use dmy dates from August 2024",
    "Use dmy dates from September 2024",
    "Use dmy dates",
    "Articles lacking in-text citations from November 2021",
    "Articles lacking in-text citations from May 2024",
    "Articles lacking sources from January 2020",
    "Articles lacking sources from November 2022",
    "Articles lacking sources from January 2024",
    "All articles lacking sources",
    "Short description is different from Wikidata",
    "Short description matches Wikidata",
    "Accuracy disputes",
    "Cleanup from June 2019",
    "Wikipedia pages protected from sock puppetry",
    "Uncategorized articles from October 2022",
    "Uncategorized articles from November 2022",
    "Uncategorized articles from December 2022",
    "Uncategorized articles from January 2023",
    "Uncategorized articles from February 2023",
    "Uncategorized articles from March 2023",
    "Uncategorized articles from April 2023",
    "Uncategorized articles from May 2023",
    "Uncategorized articles from June 2023",
    "Uncategorized articles from July 2023",
    "Uncategorized articles from August 2023",
    "Uncategorized articles from September 2023",
    "Uncategorized articles from October 2023",
    "Uncategorized articles from November 2023",
    "Uncategorized articles from December 2023",
    "Uncategorized articles from January 2024",
    "Uncategorized articles from February 2024",
    "Uncategorized articles from March 2024",
    "Uncategorized articles from April 2024",
    "Uncategorized articles from May 2024",
    "Pages needing a plot summary",
    "Pages with no title",
    "Wikipedia articles with FAST identifiers",
    "Wikipedia articles with BNF identifiers",
    "Wikipedia articles with BNE identifiers",
    "Wikipedia articles with GND identifiers",
    "Wikipedia articles with ISNI identifiers",
    "Wikipedia articles with LCCN identifiers",
    "Wikipedia articles with NKC identifiers",
    "Wikipedia articles with ICCU identifiers",
    "Wikipedia articles with USGS identifiers",
    "Wikipedia articles with Trove identifiers",
    "Wikipedia articles with WorldCat identifiers",
    "Wikipedia articles with SUDOC identifiers",
    "Infobox templates",
    "Infobox person templates",
    "Infobox software templates",
    "Infobox templates using image parameter",
    "Infobox templates using vcard",
    "Pages using infobox templates",
    "Pages using the compound disamb template",
    "Pages with reference errors",
    "Pages with parse errors",
    "Pages with cite error references",
    "Pages with script errors",
    "Pages with content transcluded from Wikipedia",
    "Citation templates with empty parameters",
    "High-use templates",
    "Templates based on the citation/core module",
    "Wikipedia navigation templates",
    "Wikipedia-internal sidebar templates",
    "Sidebar templates",
    "Navigation templates with sorting",
    "Template Category TOC",
    "Navbox templates",
    "Templates using navbox columns without the first column",
    "Pages using navbox columns without the first column",
    "Navigation templates",
    "Wikipedia articles needing clarification from March 2023",
    "Wikimedia commons templates",
    "Category series navigation templates",
    "Category series navigation isolated",
    "Category series navigation year and decade",
    "Category series navigation chronological",
    "Wikipedia template categories",
    "Template redirect templates",
    "Dated categories for templates",
    "Template maintenance",
    "Administrative templates",
    "Wikipedia administrative templates",
    "All Wikipedia templates",
]

def main():
    """Main execution."""
    print("="*70)
    print("DELETE UNUSED EVOLUTIONISM CATEGORIES (BULK)")
    print("="*70)
    print()

    try:
        # Login to wiki
        print(f"Connecting to {WIKI_URL}...")
        site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
        site.login(USERNAME, PASSWORD)

        # Retrieve username
        try:
            ui = site.api('query', meta='userinfo')
            logged_user = ui['query']['userinfo'].get('name', USERNAME)
            print(f"Logged in as {logged_user}\n")
        except Exception:
            print("Logged in (could not fetch username via API, but login succeeded).\n")

        deleted = []
        failed = []
        skipped = []
        total_count = len(CATEGORIES)

        print(f"Processing {total_count} categories...\n")

        for i, cat_name in enumerate(CATEGORIES, 1):
            page_title = f"Category:{cat_name}"
            print(f"{i}/{total_count}: Deleting '{cat_name}'...", end=" ", flush=True)

            try:
                page_obj = site.pages[page_title]

                # Check if page exists
                try:
                    existing = page_obj.text()
                    if not existing.strip():
                        print("[EMPTY - SKIP]")
                        skipped.append(cat_name)
                        continue
                except:
                    # Page doesn't exist
                    print("[NOT EXISTS - SKIP]")
                    skipped.append(cat_name)
                    continue

                # Delete the page
                page_obj.delete(reason="Deleting unused category")
                print("[DELETED]")
                deleted.append(cat_name)

                # Rate limit
                time.sleep(1.5)

            except Exception as e:
                print(f"[FAILED] {str(e)[:50]}")
                failed.append((cat_name, str(e)))
                time.sleep(1.5)
                continue

        # Summary
        print("\n" + "="*70)
        print("DELETION SUMMARY")
        print("="*70)
        print(f"Deleted: {len(deleted)}")
        print(f"Skipped: {len(skipped)}")
        print(f"Failed: {len(failed)}")
        print(f"Total: {total_count}")
        print()

        if deleted:
            print("DELETED CATEGORIES:")
            for cat in deleted[:30]:
                print(f"  {cat}")
            if len(deleted) > 30:
                print(f"  ... and {len(deleted) - 30} more")
            print()

        if skipped:
            print("SKIPPED CATEGORIES:")
            for cat in skipped[:10]:
                print(f"  {cat}")
            if len(skipped) > 10:
                print(f"  ... and {len(skipped) - 10} more")
            print()

        if failed:
            print("FAILED DELETIONS:")
            for cat, reason in failed[:10]:
                print(f"  {cat}: {reason}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
