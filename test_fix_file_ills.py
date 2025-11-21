#!/usr/bin/env python3
"""
test_fix_file_ills.py
====================
Test the file ill fix on a single page
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
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

# ─── main loop ────────────────────────────────────────────────────

def main():
    s = site()
    print("Logged in\n")

    # Get a test page from the category
    cat = s.pages["Category:Pages with files linked by ill"]

    if not cat.exists:
        print(f"[ERROR] Category does not exist")
        return

    print(f"[INFO] Getting first page from category\n")

    # Get first page
    for pg in cat:
        if pg.namespace != 0:
            continue

        print(f"Testing on: {pg.name}\n")

        text = pg.text()
        print(f"[INFO] Original text length: {len(text)} characters\n")

        # Find all {{ill|File:...}} templates
        ill_pattern = r'\{\{ill\|File:[^}]*?\}\}'
        matches = list(re.finditer(ill_pattern, text))

        print(f"[INFO] Found {len(matches)} file ill templates\n")

        if not matches:
            print(f"[SKIP] no file ill templates found")
            break

        new_text = text
        updated_count = 0

        for i, match in enumerate(matches):
            template_text = match.group(0)
            print(f"TEMPLATE {i+1}:")
            print(f"  Original: {template_text[:80]}")

            # Extract the filename
            content = template_text[6:-2]
            parts = content.split('|')

            if parts[0].startswith('File:'):
                filename = parts[0]
                print(f"  Filename: {filename}")

                # Replace with [[File:...|thumb]]
                new_template = f"[[{filename}|thumb]]"
                new_text = new_text.replace(template_text, new_template, 1)
                updated_count += 1
                print(f"  Would replace with: {new_template}\n")
            else:
                print(f"  [SKIP] doesn't start with File:\n")

        print(f"[INFO] Total templates to update: {updated_count}")
        print(f"[INFO] New text length: {len(new_text)} characters\n")

        if updated_count > 0:
            print(f"[PREVIEW] First replacement visible in text: {new_text.find('[[File:') >= 0}")

        # DON'T actually save, just show what would happen
        break

if __name__=='__main__':
    main()
