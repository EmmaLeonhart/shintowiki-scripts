#!/usr/bin/env python3
"""
add_persian_month_interwikis.py
───────────────────────────────
Add (or verify) the Persian-wiki interwiki on each Islamic-calendar month template.

Run:
    python add_persian_month_interwikis.py
"""

import re, time, urllib.parse, mwclient
from mwclient.errors import APIError, InvalidPageTitle

# ──────────── CONFIG ──────────────────────────────────────────────
API_URL   = "https://shinto.miraheze.org/w/api.php"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_1]"
THROTTLE  = 0.4          # seconds between edits
# ──────────────────────────────────────────────────────────────────

MONTH_TEMPLATES = {
    "Islamic Muharram"        : "الگو:محرم",
    "Islamic Safar"           : "الگو:صفر",
    "Islamic Rabi' al-Awwal"  : "الگو:ربیع‌الاول",
    "Islamic Rabi' al-Thani"  : "الگو:ربیع‌الثانی",
    "Islamic Jumada al-Awwal" : "الگو:جمادی‌الاول",
    "Islamic Jumada al-Thani" : "الگو:جمادی‌الثانی",
    "Islamic Rajab"           : "الگو:رجب",
    "Islamic Sha'ban"         : "الگو:شعبان",
    "Islamic Ramadan"         : "الگو:رمضان",
    "Islamic Shawwal"         : "الگو:شوال",
    "Islamic Dhu al-Qadah"    : "الگو:ذیقعده",
    "Islamic Dhu al-Hijjah"   : "الگو:ذیحجه",
}

FA_RX = re.compile(r"\[\[\s*fa\s*:", re.I)
NOINC_RX = re.compile(r"<\s*noinclude[^>]*>", re.I)

# ──────────── MWCLIENT SESSION ───────────────────────────────────
parsed = urllib.parse.urlparse(API_URL)
site   = mwclient.Site(parsed.netloc, path=parsed.path.rsplit("/api.php",1)[0] + "/")
site.login(USERNAME, PASSWORD)

# ──────────── PROCESS EACH TEMPLATE ──────────────────────────────
for name, fa_title in MONTH_TEMPLATES.items():
    full = f"Template:{name}"
    print(" •", full)

    try:
        page = site.pages[full]
    except (InvalidPageTitle, KeyError):
        print("   ! invalid title – skipped");  continue

    if not page.exists:
        print("   ! page missing – skipped");  continue

    text = page.text()
    if FA_RX.search(text):
        print("   ✓ Persian link already present");  continue

    # compose the interwiki line
    iw_line = f"[[fa:{fa_title}]]"

    # insert before the first <noinclude>, or append at end
    m = NOINC_RX.search(text)
    if m:
        pos  = m.start()
        new  = text[:pos].rstrip() + "\n" + iw_line + "\n" + text[pos:]
    else:
        new  = text.rstrip() + "\n" + iw_line + "\n"

    try:
        page.save(new, summary="Bot: add Persian interwiki")
        print("   • added Persian interwiki")
    except APIError as e:
        print("   ! save failed:", e.code)
    time.sleep(THROTTLE)

print("Done – all month templates checked.")
