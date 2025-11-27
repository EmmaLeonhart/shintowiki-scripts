#!/usr/bin/env python3
"""
Delete specified category pages from the wiki
"""
# >>> credentials / endpoint >>>
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
# <<< credentials <<<

import os, sys, time, urllib.parse, mwclient, io
from mwclient.errors import APIError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

THROTTLE = 0.5

# Categories to delete
CATEGORIES = [
    "1,004 → 1,048 members",
    "1005 deaths",
    "1027 deaths",
    "1210 births",
    "1253 deaths",
    "12th-century people by nationality and occupation",
    "1570s establishments in Japan",
    "1650 in Japan",
    "1657 births",
    "16th-century births",
    "1700s books",
    "1725 deaths",
    "1788年生",
    "1800s novels",
    "1815 in Japan",
    "1853年没",
    "1885 festivals",
    "18th-century Japanese historians",
    "1908 works",
    "1940 establishments",
    "1944 establishments in the Japanese colonial empire",
    "1946 establishments in Japan",
    "1953 festivals",
    "1956 disestablishments in Japan",
    "1958 establishments in Japan",
    "1960s plays",
    "1965 short story collections",
    "1968 establishments in Japan",
    "1996年登録の世界遺産",
    "19th century in politics",
    "1st-century establishments",
    "1st millennium beginnings",
    "2013 establishments in Japan",
    "20th-century women",
    "21st-century American people by occupation",
    "21st-century people by occupation",
    "21st-century philosophers by nationality",
    "21st-century women",
    "3rd century in religion",
    "48 Temples of Bizen",
    "500s establishments",
    "5th-century BC people by occupation",
    "5th-century BC scholars",
    "5th-century BC writers",
    "662 births",
    "6th-century nobility",
    "708 in Japan",
    "778",
    "921 births",
    "921 establishments",
    "954 births",
    "9th-century deaths",
]

def site():
    p = urllib.parse.urlparse(API_URL)
    s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
    s.login(USERNAME, PASSWORD)
    return s

def main():
    s = site()
    print("Logged in")
    print(f"Will delete {len(CATEGORIES)} categories")

    deleted = 0
    failed = 0
    skipped = 0

    for i, cat_name in enumerate(CATEGORIES, 1):
        page_title = f"Category:{cat_name}"

        try:
            pg = s.pages[page_title]

            if not pg.exists:
                print(f"[{i:4d}] [SKIP] does not exist")
                skipped += 1
                continue

            # Delete the page
            pg.delete(reason="Bot: Removing unwanted category page")
            print(f"[{i:4d}] [DELETED] {cat_name}")
            deleted += 1

            time.sleep(THROTTLE)

        except APIError as e:
            print(f"[{i:4d}] [FAILED] {cat_name}: {e.code}")
            failed += 1
        except Exception as e:
            print(f"[{i:4d}] [ERROR] {cat_name}: {str(e)}")
            failed += 1

    print(f"\n=== SUMMARY ===")
    print(f"Deleted: {deleted}")
    print(f"Failed: {failed}")
    print(f"Skipped (not found): {skipped}")
    print(f"Total: {deleted + failed + skipped}")

if __name__ == '__main__':
    main()
