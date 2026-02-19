"""
create_category_qid_redirects.py
==================================
For every category page with {{wikidata link|Q...}}:
1. Create Category:Q{QID} as #REDIRECT [[Category:Name]] if the page doesn't exist
2. If Category:Q{QID} already redirects to the same category: skip
3. If Category:Q{QID} already redirects to a DIFFERENT category (duplicate QID):
   - Replace it with a numbered list linking to both categories
   - Add [[Category:duplicated qid category redirects]] to that page
4. If Category:Q{QID} is already a dup-disambiguation page, append the new entry
"""

import re, time, io, sys
import mwclient

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
THROTTLE  = 1.5
DUP_CAT   = "duplicated qid category redirects"

WD_LINK_RE  = re.compile(r'\{\{wikidata link\|(Q\d+)\}\}', re.IGNORECASE)
REDIRECT_RE = re.compile(r'^#REDIRECT\s*\[\[(.+?)\]\]', re.IGNORECASE | re.MULTILINE)

site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                     clients_useragent='CategoryQidRedirectBot/1.0 (User:Immanuelle; shinto.miraheze.org)')
site.login(USERNAME, PASSWORD)
print("Logged in as", USERNAME, flush=True)


def get_categories_with_wikidata():
    """Return all Category-namespace pages that transclude {{wikidata link}}."""
    pages = []
    cont = {}
    while True:
        data = site.api('query', list='embeddedin',
                        eititle='Template:wikidata link',
                        einamespace=14,
                        eilimit=500,
                        **cont)
        for item in data['query']['embeddedin']:
            pages.append(item['title'])
        if 'continue' in data:
            cont = data['continue']
        else:
            break
    return pages


def main():
    print("Finding categories with {{wikidata link}}...", flush=True)
    cat_titles = get_categories_with_wikidata()
    # Skip QID redirect pages themselves (Category:Q12345)
    cat_titles = [t for t in cat_titles if not re.match(r'Category:Q\d+$', t)]
    print(f"Found {len(cat_titles)} categories with wikidata links\n", flush=True)

    created = duplicates = skipped = errors = 0

    for i, title in enumerate(cat_titles, 1):
        page = site.pages[title]
        try:
            text = page.text()
        except Exception as e:
            print(f"[{i}] ERROR reading {title}: {e}", flush=True)
            errors += 1
            continue

        m = WD_LINK_RE.search(text)
        if not m:
            skipped += 1
            continue

        qid = m.group(1)
        qid_title = f"Category:{qid}"
        qid_page  = site.pages[qid_title]
        print(f"[{i}/{len(cat_titles)}] {title}  →  {qid_title}", flush=True)

        try:
            if not qid_page.exists:
                # Simple case: create the redirect
                qid_page.save(
                    f"#REDIRECT [[{title}]]",
                    summary=f"Bot: redirect {qid} → [[{title}]]"
                )
                print(f"  CREATED", flush=True)
                created += 1

            else:
                existing = qid_page.text() or ""
                rm = REDIRECT_RE.search(existing)

                if rm:
                    target = rm.group(1)
                    if target == title:
                        # Already correct
                        print(f"  SKIP (already correct redirect)", flush=True)
                        skipped += 1
                        continue
                    else:
                        # Duplicate: two categories share this QID
                        print(f"  DUPLICATE — was → [[{target}]]", flush=True)
                        new_text = (
                            f"# [[{target}]]\n"
                            f"# [[{title}]]\n"
                            f"[[Category:{DUP_CAT}]]"
                        )
                        qid_page.save(new_text,
                            summary=f"Bot: {qid} claimed by multiple categories — disambiguation")
                        duplicates += 1

                elif f"[[Category:{DUP_CAT}]]" in existing:
                    # Already a dup page — add this entry if missing
                    if title not in existing:
                        cleaned = existing.replace(f"[[Category:{DUP_CAT}]]", "").rstrip()
                        new_text = f"{cleaned}\n# [[{title}]]\n[[Category:{DUP_CAT}]]"
                        qid_page.save(new_text,
                            summary=f"Bot: adding [[{title}]] to {qid} disambiguation")
                        print(f"  ADDED to existing dup page", flush=True)
                        duplicates += 1
                    else:
                        print(f"  SKIP (already in dup page)", flush=True)
                        skipped += 1
                        continue

                else:
                    # Exists but is neither a redirect nor a dup page — leave alone
                    print(f"  SKIP (page exists with other content)", flush=True)
                    skipped += 1
                    continue

        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            errors += 1
            continue

        time.sleep(THROTTLE)

    print(f"\n{'='*60}", flush=True)
    print(f"Done! Created: {created} | Duplicates: {duplicates} | Skipped: {skipped} | Errors: {errors}", flush=True)


if __name__ == "__main__":
    main()
