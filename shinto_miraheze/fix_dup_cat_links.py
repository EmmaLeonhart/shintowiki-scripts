import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import os
"""
fix_dup_cat_links.py
Fix existing dup pages that have [[Category:X]] instead of [[:Category:X]]
in their numbered list entries.
"""
import re, sys, io, mwclient
from wiki_login import login_with_retry

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL  = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = os.getenv("WIKI_USERNAME", "EmmaBot")
PASSWORD = os.getenv("WIKI_PASSWORD", "")
DUP_CAT   = "duplicated qid category redirects"

site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                     clients_useragent=USER_AGENT)
login_with_retry(site, USERNAME, PASSWORD)
print("Logged in as", USERNAME, flush=True)

# Regex: numbered list item with bare [[Category:...]] (no leading colon)
# We want to turn  # [[Category:Foo]]  into  # [[:Category:Foo]]
BAD_RE = re.compile(r'^(#\s*)\[\[Category:', re.MULTILINE)

cat = site.categories[DUP_CAT]
fixed = 0
for page in cat:
    if page.namespace != 14:
        continue
    text = page.text()
    if BAD_RE.search(text):
        new_text = BAD_RE.sub(r'\1[[:Category:', text)
        page.save(new_text, summary="Bot: fix category links in dup page (add colon prefix)")
        print(f"  FIXED {page.name}", flush=True)
        fixed += 1
    else:
        print(f"  OK    {page.name}", flush=True)

print(f"\nDone! Fixed {fixed} pages.", flush=True)
