#!/usr/bin/env python3
"""
islamic_day_overwrite.py  –  rebuild every Islamic-day page
-----------------------------------------------------------

• Reads every {{ill|…}} on  List_of_days_of_the_Islamic_Calendar
• Creates / over-writes page 0-param (e.g. “Muharram 1”) with:

    {{Expand Arabic}}
    {{Expand Bengali}}
    {{Expand Persian}}
    '''Muharram 1''' is a day of the [[Islamic calendar]]. It is the 1st day
    of the month [[Muharram]].

    ==See also==
    * [[List of days of the Islamic Calendar]]
    [[Category:Islamic Calendar Days]]
    [[Category:Days 1 of the Islamic Calendar]]
    [[Category:Muharram]]
    [[ar:...]]
    [[bn:...]]
    …

The inter-wiki block uses the lang/title pairs that are already embedded
inside the fixed {{ill|}} templates, so **no Wikidata API calls** are needed.

Run repeatedly with no harm – each run simply re-writes the same deterministic
stub.

"""

# ── ACCOUNT / WIKI ────────────────────────────────────────────────
API_URL  = "https://shinto.miraheze.org/w/api.php"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_1]"
THROTTLE = 0.4         # seconds between edits
# -----------------------------------------------------------------

import re, time, urllib.parse, mwclient
from mwclient.errors import APIError

# set up mwclient
up = urllib.parse.urlparse(API_URL)
site = mwclient.Site(up.netloc, path=up.path.rsplit("/api.php", 1)[0] + "/")
site.login(USERNAME, PASSWORD)

# target page containing all ILLs
LIST_PAGE = site.pages["List_of_days_of_the_Islamic_Calendar"]
text      = LIST_PAGE.text()

ILL_RX = re.compile(r"""
    \{\{ill\|
    \s*([^|{}]+?)           # 1 – EN page title
    \s*\|ms\|[^|{}]+?       # skip the Malay pair (already present)
    (?P<pairs>(?:\|[^{}]*)*)   # all the remaining |lang|title pairs
    \}\}""", re.I | re.X | re.S)

ORDINAL = {1:"st", 2:"nd", 3:"rd"}
def ordinal(n:int) -> str:        # 1 → 1st, 2 → 2nd …
    return f"{n}{ORDINAL.get(n if 10<n%100<14 else n%10, 'th')}"

def page_stub(title:str, month:str, day:int, iw_lines:list[str]) -> str:
    return (
        "{{Expand Arabic}}\n{{Expand Bengali}}\n{{Expand Persian}}\n"
        f"'''{title}''' is a day of the [[Islamic calendar]]. "
        f"It is the {ordinal(day)} day of the month [[{month}]].\n\n"
        "==See also==\n"
        "* [[List of days of the Islamic Calendar]]\n"
        "[[Category:Islamic Calendar Days]]\n"
        f"[[Category:Days {day} of the Islamic Calendar]]\n"
        f"[[Category:{month}]]\n" +
        "".join(iw_lines)
    )

def iter_pairs(pair_block:str):
    """Yield (lang,title) from  |lang|title|lang|title …"""
    parts = [p for p in pair_block.split("|") if p.strip()]
    for i in range(0, len(parts), 2):
        if i+1 < len(parts):
            yield parts[i].strip(), parts[i+1].strip()

count = 0
for m in ILL_RX.finditer(text):
    en_title = m.group(1).strip()
    try:
        month, day_s = en_title.rsplit(" ", 1)
        day = int(day_s)
    except ValueError:
        print("  ! skipped malformed title:", en_title); continue

    # collect |lang|title pairs into [[lang:title]] lines
    iw_lines = []
    for lang,title in iter_pairs(m.group("pairs")):
        if lang == "en":          # already the page itself
            continue
        iw_lines.append(f"[[{lang}:{title}]]\n")

    stub_text = page_stub(en_title, month, day, iw_lines)

    page = site.pages[en_title]
    try:
        page.save(stub_text, summary="Bot: overwrite Islamic-day stub")
        print(" •", en_title)
        count += 1
    except APIError as e:
        print("  ! cannot save", en_title, e.code)
    time.sleep(THROTTLE)

print(f"\nFinished – {count} pages written.")
