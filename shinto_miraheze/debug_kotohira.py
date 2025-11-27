#!/usr/bin/env python3
import urllib.parse, mwclient, re

API_URL = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"

p = urllib.parse.urlparse(API_URL)
s = mwclient.Site(p.netloc, path=p.path.rsplit("/api.php",1)[0]+"/")
s.login(USERNAME,PASSWORD)

pg = s.pages["Kotohira-gū"]
text = pg.text()

# Test different patterns
pattern1 = r'\{\{ill\|File:[^}]*?\}\}'
pattern2 = r'\{\{ill\|File:[^}]*\}\}'

matches1 = list(re.finditer(pattern1, text))
matches2 = list(re.finditer(pattern2, text))

print(f"Pattern 1 (non-greedy): {len(matches1)} matches")
print(f"Pattern 2 (greedy): {len(matches2)} matches\n")

# Show first 3
print("First 3 matches with pattern 1:")
for i, m in enumerate(matches1[:3]):
    template = m.group(0)
    # Truncate for display
    if len(template) > 100:
        template = template[:97] + "..."
    print(f"  {i+1}. {template}")
