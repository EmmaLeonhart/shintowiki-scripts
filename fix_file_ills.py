#!/usr/bin/env python3
"""
fix_file_ills.py
================
Fix {{ill|File:...}} templates by converting them to proper [[File:...]] syntax
For pages in [[Category:Pages with files linked by ill]]
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
# <<< credentials <<<

import os, sys, time, urllib.parse, mwclient, re
from mwclient.errors import APIError

CATEGORY = "Pages with files linked by ill"
THROTTLE = 0.5

# ─── site login ───────────────────────────────────────────────────

def site():
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
    s.login(USERNAME,PASSWORD)
    return s

# ─── main loop ────────────────────────────────────────────────────

def main():
    s = site()
    print("Logged in")

    # Get all pages in the category
    cat = s.pages[f"Category:{CATEGORY}"]

    if not cat.exists:
        print(f"[ERROR] Category '{CATEGORY}' does not exist")
        return

    print(f"[INFO] Processing pages in Category:{CATEGORY}")

    count = 0
    for pg in cat:
        # Only process main namespace articles
        if pg.namespace != 0:
            continue

        try:
            page_name = pg.name.encode('utf-8', errors='replace').decode('utf-8')
            print(f"Processing: {page_name}")
            text = pg.text()

            # Find all {{ill|File:...}} templates
            # Pattern: {{ill|File:... with File: at the start
            ill_pattern = r'\{\{ill\|File:[^}]*?\}\}'
            matches = list(re.finditer(ill_pattern, text))

            if not matches:
                print(f"  [SKIP] no file ill templates found")
                continue

            updated = False
            new_text = text

            for match in matches:
                template_text = match.group(0)
                print(f"  [INFO] Found file ill template")

                # Extract the filename from {{ill|File:...}}
                # Format: {{ill|File:Name|lang|File:Name|...}}
                # We want to extract just the File:Name part

                # Remove {{ ill| and }}
                content = template_text[6:-2]
                parts = content.split('|')

                # First part should be File:Something (possibly with space after colon)
                first_part = parts[0].strip()
                if first_part.startswith('File:'):
                    # Keep the filename as-is (with the space if it has one)
                    filename = parts[0]
                    print(f"    Extracted filename: {repr(filename)}")

                    # Replace with [[File:...|thumb]]
                    new_template = f"[[{filename}|thumb]]"
                    new_text = new_text.replace(template_text, new_template, 1)
                    updated = True
                    print(f"    Replaced with: {new_template}")
                else:
                    print(f"    [SKIP] doesn't start with File:")
                    continue

            if updated:
                try:
                    pg.save(new_text, summary="Bot: Fix ill templates with files - convert to [[File:...|thumb]]")
                    count += 1
                    print(f"  [DONE] updated page")
                except APIError as e:
                    print(f"  [FAILED] save failed: {e.code}")

            time.sleep(THROTTLE)

        except Exception as e:
            print(f"  [ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\nTotal pages updated: {count}")

if __name__=='__main__':
    main()
