#!/usr/bin/env python3
"""
tidy_categories.py – Category-namespace housekeeping
─────────────────────────────────────────────────────
*This edition fixes the “stops at 5 000 pages” issue by walking
 through **every** batch returned by the Allpages API.*

(Everything else – re-ordering cats/interwikis, importing ja-text,
 adding en-links, tracking categories – is unchanged.)
"""
from __future__ import annotations
import re, time, urllib.parse, requests, mwclient
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
API_URL   = "https://shinto.miraheze.org/w/api.php"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_2]"
THROTTLE  = 0.5
UA        = {"User-Agent": "cat-tidier/1.0 (User:Immanuelle)"}

TRACK_JA   = "Categories with Japanese explanatory text to translate to english"
TRACK_NOEN = "Categories without enwiki"

# ─── REGEXES ────────────────────────────────────────────────────────
CAT_RX   = re.compile(r"\[\[\s*Category:[^]]+]]", re.I)
IW_RX    = re.compile(r"\[\[\s*([a-z_-]{2,12}):[^]]+]]", re.I)
JA_IW_RX = re.compile(r"\[\[\s*ja:[^]]+]]", re.I)
EN_IW_RX = re.compile(r"\[\[\s*en:[^]]+]]", re.I)

# ─── MW SESSION ─────────────────────────────────────────────────────
api_host = urllib.parse.urlparse(API_URL)
PATH = api_host.path.rsplit("/api.php", 1)[0] + "/"

site = mwclient.Site(api_host.netloc, path=PATH,
                     clients_useragent=UA["User-Agent"])
site.login(USERNAME, PASSWORD)
print("Logged in – traversing full Category namespace…")

# ─── WIKIDATA HELPERS (unchanged) ───────────────────────────────────
WD_API = "https://www.wikidata.org/w/api.php"
def en_from_wikidata(qid:str)->str|None:
    try:
        data = requests.get(WD_API, params={
            "action":"wbgetentities", "ids":qid, "props":"sitelinks",
            "format":"json"}, timeout=10).json()
        return data["entities"][qid]["sitelinks"].get("enwiki", {}).get("title")
    except Exception:
        return None
def wikidata_qid_from_ja(title:str)->str|None:
    ja = mwclient.Site("ja.wikipedia.org")
    data = ja.api(action="query", prop="pageprops", ppprop="wikibase_item",
                  titles=f"Category:{title}", format="json")
    return next(iter(data["query"]["pages"].values())) \
           .get("pageprops", {}).get("wikibase_item")
# --- replace the three blocks in the previous script -----------------

# 1) better JA-interwiki regex: capture *title* (incl. namespace) in group(1)
JA_IW_RX = re.compile(r"\[\[\s*ja:([^\]]+?)]]", re.I)

# 2) helper now returns clean prose (strips both cats *and* interwikis)
def fetch_jawiki_body(title: str) -> str | None:
    """Return ja-wiki wikitext of Category:title with cats/IWs removed."""
    ja = mwclient.Site("ja.wikipedia.org")
    pg = ja.pages[title if title.startswith("Category:") else f"Category:{title}"]
    if not pg.exists:
        return None
    txt = pg.text()
    txt = CAT_RX.sub("", txt)             # drop cats
    txt = IW_RX.sub("", txt)              # drop interwikis
    return txt.strip() or None            # None if now blank

# 3) in tidy_page()   (just the JA block; rest unchanged)
    # pull JA text block …
    ja_match = JA_IW_RX.search(orig)
    if ja_match:
        ja_target = ja_match.group(1)          # full title after ja:
        ja_body   = fetch_jawiki_body(ja_target)
        if ja_body and "==Japanese Content==" not in body:
            body = ("\n".join([
                "==Japanese Content==",
                ja_body,
                "",
                f"[[Category:{TRACK_JA}]]",
                "",
                "==Old Content==",
                body.lstrip()
            ]))
            changed = True


# ─── PAGE ITERATOR  (NEW) ───────────────────────────────────────────
def all_category_pages():
    """Yield every Category: page title on the wiki, >5 000 included."""
    cont = None
    while True:
        params = {
            "action": "query",
            "list":   "allpages",
            "apnamespace": 14,          # Category namespace
            "aplimit": "max",           # 5 000 for bots
            "format": "json"
        }
        if cont:
            params["apcontinue"] = cont
        data = site.api(**params)
        for ap in data["query"]["allpages"]:
            yield ap["title"]
        cont = data.get("continue", {}).get("apcontinue")
        if not cont:
            break

# ─── CORE PROCESSOR  (identical to previous) ───────────────────────
def tidy_page(page):
    try:
        orig = page.text()
    except APIError as e:
        print("   ! cannot fetch:", e.code); return

    cats  = CAT_RX.findall(orig)
    iws   = IW_RX.findall(orig)
    iw_lines = [m.group(0) for m in IW_RX.finditer(orig)]
    body = CAT_RX.sub("", orig)
    body = IW_RX.sub("", body).rstrip()
    changed = False

    # ensure EN sitelink if possible …
    has_en = any(lang.lower() == "en" for lang in iws)
    if not has_en:
        ja_match = JA_IW_RX.search(orig)
        if ja_match:
            ja_title = ja_match.group(0).split(":",1)[1].strip("[]")
            qid = wikidata_qid_from_ja(ja_title)
            en_title = en_from_wikidata(qid) if qid else None
            if en_title:
                iw_lines.append(f"[[en:{en_title}]]")
                has_en = True
                changed = True

    # pull JA text block …
    ja_match = JA_IW_RX.search(orig)
    if ja_match:
        ja_target = ja_match.group(1)          # full title after ja:
        ja_body   = fetch_jawiki_body(ja_target)
        if ja_body and "==Japanese Content==" not in body:
            body = ("\n".join([
                "==Japanese Content==",
                ja_body,
                "",
                f"[[Category:{TRACK_JA}]]",
                "",
                "==Old Content==",
                body.lstrip()
            ]))
            changed = True

    if not has_en and f"[[Category:{TRACK_NOEN}]]" not in cats:
        cats.append(f"[[Category:{TRACK_NOEN}]]")
        changed = True

    cats = sorted(set(cats), key=str.casefold)
    iw_lines = sorted(set(iw_lines), key=str.casefold)

    new_txt = body.rstrip() + "\n"
    if iw_lines:
        new_txt += "\n".join(iw_lines) + "\n"
    if cats:
        new_txt += "\n".join(cats) + "\n"

    if new_txt != orig:
        try:
            page.save(new_txt,
                      summary="Bot: tidy cats/interwikis, add JA text & EN link",
                      minor=False)
            print("   ✓ saved")
            time.sleep(THROTTLE)
        except APIError as e:
            print("   ! save failed", e.code)

# ─── MAIN LOOP ─────────────────────────────────────────────────────
def main():
    count = 0
    for title in all_category_pages():
        count += 1
        print(f"[{count}] {title}")
        tidy_page(site.pages[title])
    print(f"Done – processed {count} category pages.")

if __name__ == "__main__":
    main()
