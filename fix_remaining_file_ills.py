#!/usr/bin/env python3
"""
fix_remaining_file_ills.py
==========================
Fix the 3 remaining pages with file ills:
- Gekū Sando (2 file ills)
- Kotohira-gū (50 file ills)
- Okihata Suitengū (2 file ills)
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"
# <<< credentials <<<

import os, sys, time, urllib.parse, mwclient, re
from mwclient.errors import APIError

THROTTLE = 0.5

# ─── site login ───────────────────────────────────────────────────

def site():
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
    s.login(USERNAME,PASSWORD)
    return s

# ─── fix page ─────────────────────────────────────────────────────

def fix_page(s, page_name):
    try:
        pg = s.pages[page_name]
        text = pg.text()

        # Find all {{ill|File:...}} templates
        ill_pattern = r'\{\{ill\|File:[^}]*?\}\}'
        matches = list(re.finditer(ill_pattern, text))

        if not matches:
            print(f"  [SKIP] no file ill templates found")
            return 0

        new_text = text
        updated_count = 0

        for match in matches:
            template_text = match.group(0)

            # Extract the filename from {{ill|File:...}}
            content = template_text[6:-2]
            parts = content.split('|')

            # First part should be File:Something
            first_part = parts[0].strip()
            if first_part.startswith('File:'):
                filename = parts[0]

                # Replace with [[File:...|thumb]]
                new_template = f"[[{filename}|thumb]]"
                new_text = new_text.replace(template_text, new_template, 1)
                updated_count += 1

        if updated_count > 0:
            try:
                pg.save(new_text, summary="Bot: Fix ill templates with files - convert to [[File:...|thumb]]")
                print(f"  [DONE] updated {updated_count} file ill templates")
                return 1
            except APIError as e:
                print(f"  [FAILED] save failed: {e.code}")
                return 0

        return 0

    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        return 0

# ─── main ────────────────────────────────────────────────────────

def main():
    s = site()
    print("Logged in\n")

    pages_to_fix = [
        "Gekū Sando",
        "Kotohira-gū",
        "Okihata Suitengū"
    ]

    total_updated = 0

    for page_name in pages_to_fix:
        try:
            # Write page name to log file instead
            with open('fix_remaining_progress.log', 'a', encoding='utf-8') as log:
                log.write(f"Processing: {page_name}\n")
            print(f"Page {len(pages_to_fix)}: Processing...")

            total = fix_page(s, page_name)
            total_updated += total
            time.sleep(THROTTLE)
        except Exception as e:
            with open('fix_remaining_progress.log', 'a', encoding='utf-8') as log:
                log.write(f"  [ERROR] {str(e)}\n")

    print(f"\nTotal pages updated: {total_updated}")

if __name__=='__main__':
    main()
