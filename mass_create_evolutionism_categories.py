#!/usr/bin/env python3
"""
Mass create required categories on evolutionismwiki.
Each category gets a page with the category name and creation date.
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

# Categories to create - from user's list
CATEGORIES = [
    "Year disambiguations",
    "Generated Gaiad character entries for the 1st 62 chapters",
    "110th century",
    "113th century",
    "114th century",
    "118th century",
    "111th century",
    "112th century",
    "115th century",
    "116th century",
    "117th century",
    "119th century",
    "120th century",
    "121st century",
    "Special:LonelyPages November 4 2025",
    "Year type categories that appear not to exist",
    "LINKED FROM WIKIDATA DO NOT OVERWRITE",
    "10890s",
    "10900s",
    "10930s",
    "10960s",
    "10990s",
    "11000s",
    "11030s",
    "11070s",
    "11110s",
    "11150s",
    "11180s",
    "11210s",
    "11220s",
    "11250s",
    "11290s",
    "11300s",
    "11330s",
    "11360s",
    "11390s",
    "11400s",
    "11430s",
    "11470s",
    "11510s",
    "11550s",
    "11580s",
    "11610s",
    "11650s",
    "11690s",
    "11700s",
    "11730s",
    "11760s",
    "11790s",
    "11800s",
    "11830s",
    "11870s",
    "11910s",
    "11950s",
    "11980s",
    "12010s",
    "12050s",
    "12090s",
    "0th century",
    "10870s",
    "10880s",
    "10910s",
    "10920s",
    "10940s",
    "10950s",
    "10970s",
    "10980s",
    "11010s",
    "11020s",
    "11040s",
    "11050s",
    "11060s",
    "11080s",
    "11090s",
    "11100s",
    "11120s",
    "11130s",
    "11140s",
    "11160s",
    "11170s",
    "11190s",
    "11200s",
    "11230s",
    "11240s",
    "11260s",
    "11270s",
    "11280s",
    "11310s",
    "11320s",
    "11340s",
    "11350s",
    "11370s",
    "11380s",
    "11410s",
    "11420s",
    "11440s",
    "11450s",
    "11460s",
    "11480s",
    "11490s",
    "11500s",
    "11520s",
    "11530s",
    "11540s",
    "11560s",
    "11570s",
    "11590s",
    "11600s",
    "11620s",
    "11630s",
    "11640s",
    "11660s",
    "11670s",
    "11680s",
    "11710s",
    "11720s",
    "11740s",
    "11750s",
    "11770s",
    "11780s",
    "11810s",
    "11820s",
    "11840s",
    "11850s",
    "11860s",
    "11880s",
    "11890s",
    "11900s",
    "11920s",
    "11930s",
    "11940s",
    "11960s",
    "11970s",
    "11990s",
    "12000s",
    "12020s",
    "12030s",
    "12040s",
    "12060s",
    "12070s",
    "12080s",
    "Navigational box metatemplates",
    "Not real year types",
    "Redirects connected to a Evolutionism Wiki item",
    "Under Review",
    "-1s",
    "-2s",
    "-3s",
    "-4s",
    "-5s",
    "-6s",
    "-7s",
    "-8s",
    "-9s",
    "11",
    "12100s",
    "17th-century BC pharaohs",
    "1s",
    "240s births",
    "2s",
    "320s deaths",
    "3rd-century Greek philosophers",
    "3rd-century Romans",
    "3rd-century mathematicians",
    "4s",
    "4th-century Greek philosophers",
    "4th-century Romans",
    "4th-century mathematicians",
    "4th-century philosophers",
    "5s",
    "Actual Terms",
    "Ancient slaves",
    "Apamea, Syria",
    "Articles lacking in-text citations from November 2021",
    "Articles with disputed statements from November 2023",
    "Articles with unsourced statements from November 2024",
    "Category series navigation isolated",
    "Category series navigation year and decade",
    "Children of Jacob",
    "Common Terms",
    "Contains Content Warning",
    "Dfa gateways",
    "Disorder-Related Terms",
    "Dissociation-Related Terms",
    "Five Dragon Boat Festivals'",
    "Founders of biblical tribes",
    "Greek-language commentators on Plato",
    "Hebrew Bible prophets of the Quran",
    "Historical period subtemplates",
    "History of magic",
    "Intercalary months",
    "Joseph (Genesis)",
    "Neo-Pythagoreans",
    "Neoplatonists",
    "Not Plural Exclusive",
    "Occult writers",
    "Pagan anti-Gnosticism",
    "Pages using navbox columns without the first column",
    "Pages where template include size is exceeded",
    "Pages with no translate target",
    "Pages with numeric Bible version references",
    "People from Avaris",
    "People from Roman Syria",
    "Pharaohs of the Fifteenth Dynasty of Egypt",
    "Polycyclic aromatic hydrocarbons",
    "Psychiatric Terms",
    "Q",
    "Short description is different from Wikidata",
    "Short description matches Wikidata",
    "Syrian philosophers",
    "System Function Terms",
    "TED speaker template missing ID and not in Wikidata",
    "Template Category TOC without CatAutoTOC on category with 601–900 pages",
    "Terms",
    "Terms that may be used as nouns",
    "Terms with a known coiner",
    "Terms with synonyms or alternate forms",
    "Theurgy",
    "Use dmy dates from January 2019",
    "Wikipedia-internal sidebar templates",
    "Wikipedia articles needing clarification from March 2023",
    "Wisdom literature",
    "Year of death uncertain",
]

def main():
    """Main execution."""
    print("="*70)
    print("MASS CREATE EVOLUTIONISM CATEGORIES")
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

        created = []
        failed = []

        print(f"Creating {len(CATEGORIES)} categories...\n")

        for i, cat_name in enumerate(CATEGORIES, 1):
            page_title = f"Category:{cat_name}"
            print(f"{i}/{len(CATEGORIES)}: Creating '{cat_name}'...", end=" ", flush=True)

            try:
                page = site.pages[page_title]

                # Check if category page exists
                try:
                    existing = page.text()
                    if existing.strip():
                        print("[SKIP - already exists]")
                        continue
                except:
                    pass

                # Create page with category name and current date
                content = f"{cat_name}\n"

                page.edit(content, summary="Create required category")
                print("[OK]")
                created.append(cat_name)

                # Rate limit
                time.sleep(1.5)

            except Exception as e:
                print(f"[FAILED] {str(e)[:50]}")
                failed.append((cat_name, str(e)))
                time.sleep(1.5)

        # Summary
        print("\n" + "="*70)
        print(f"CREATION SUMMARY")
        print("="*70)
        print(f"Created: {len(created)}")
        print(f"Failed: {len(failed)}")
        print(f"Total: {len(CATEGORIES)}")
        print()

        if failed:
            print("FAILED CATEGORIES:")
            for cat, reason in failed[:20]:
                print(f"  {cat}: {reason}")
            if len(failed) > 20:
                print(f"  ... and {len(failed) - 20} more")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
