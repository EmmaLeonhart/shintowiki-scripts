#!/usr/bin/env python3
import urllib.parse, mwclient

API_URL = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"

p = urllib.parse.urlparse(API_URL)
s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
s.login(USERNAME,PASSWORD)

# Try different variations
attempts = [
    "Pages with files linked by ill",
    "Pages with files linked by ills",
    "Files linked by ill",
    "Files linked by ills",
]

for cat_name in attempts:
    cat = s.pages[f"Category:{cat_name}"]
    if cat.exists:
        print(f"Found: Category:{cat_name}")
        # Count pages
        count = 0
        for pg in cat:
            count += 1
            if count <= 5:
                print(f"  - {pg.name}")
        print(f"Total: {count} pages\n")
        break
else:
    print("Category not found")
