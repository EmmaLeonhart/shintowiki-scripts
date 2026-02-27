#!/usr/bin/env python3
# tier_enwiki_sync.py
#
# Import EN-wiki text & full inter-wikis for every category that sits in
# Category:Tier_N_Categories_with_enwiki   (N = 1‥9)
#
# EmmaBot – 2025-05-28

from __future__ import annotations
import re, time, argparse, requests, mwclient
from mwclient.errors import APIError
from typing import List

# ── BASIC CONFIG ──────────────────────────────────────────────────────
LOCAL_URL  = "shinto.miraheze.org"; LOCAL_PATH = "/w/"
USERNAME   = "EmmaBot";          PASSWORD   = "[REDACTED_SECRET_1]"
THROTTLE   = 0.4          # seconds between edits
UA         = {"User-Agent": "tier-enwiki-sync/1.0 (User:EmmaBot)"}

WD_API     = "https://www.wikidata.org/w/api.php"
EN_API     = "https://en.wikipedia.org/w/api.php"

TIERS = [f"Category:Tier_{i}_Categories_with_enwiki" for i in range(2,10)]

CAT_RX = re.compile(r"\[\[\s*Category:[^\]]+]]", re.I)
IW_RX  = re.compile(r"\[\[\s*[a-z\-]+:[^\]]+]]", re.I)
EN_IW_RX = re.compile(r"\[\[\s*en:Category:([^\]|]+)", re.I)

# ── SESSIONS ──────────────────────────────────────────────────────────
site = mwclient.Site(LOCAL_URL, path=LOCAL_PATH)
site.login(USERNAME, PASSWORD)
jaw        = mwclient.Site("ja.wikipedia.org")   # only for testing existence
print("Logged in – processing Tier-N categories")

# ── HELPERS ───────────────────────────────────────────────────────────
def get_wd_sitelinks(qid:str) -> dict[str,str]:
    try:
        j = requests.get(WD_API,
                         params={"action":"wbgetentities","ids":qid,
                                 "props":"sitelinks","format":"json"},
                         headers=UA, timeout=8).json()
        sl = j["entities"][qid]["sitelinks"]
        return {k[:-4]: v["title"] for k,v in sl.items()}
    except Exception:
        return {}

def qid_for_en_category(title:str) -> str|None:
    try:
        r = requests.get(EN_API,
                         params={"action":"query","prop":"pageprops",
                                 "titles":title,"ppprop":"wikibase_item",
                                 "format":"json"},
                         headers=UA, timeout=8).json()
        pp = next(iter(r["query"]["pages"].values())).get("pageprops",{})
        return pp.get("wikibase_item")
    except Exception:
        return None

def pull_en_body(en_title:str) -> str|None:
    try:
        r = requests.get(EN_API,
                         params={"action":"query","prop":"revisions",
                                 "rvprop":"content","rvslots":"main",
                                 "titles":en_title,"formatversion":2,
                                 "format":"json"},
                         headers=UA, timeout=10).json()
        txt = r["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]
        body = CAT_RX.sub("", txt)   # strip en categories
        return body.strip() or None
    except Exception:
        return None

def collect_members(cat_title:str) -> List[str]:
    """ Return MEMBERS (titles) of the meta category (non-hidden, all ns). """
    q = {"action":"query","list":"categorymembers","cmtitle":cat_title,
         "cmtype":"page|subcat","cmlimit":"max","format":"json"}
    data = site.api(**q)
    return [m["title"] for m in data["query"]["categorymembers"]]

# ── CORE FUNCTION ────────────────────────────────────────────────────
def sync_page(title:str, dry:bool=False):
    pg = site.pages[title]
    text = pg.text()

    m = EN_IW_RX.search(text)
    if not m:
        print("  • no en-wiki link – skipped"); return
    en_name = m.group(1).strip()

    en_body = pull_en_body(f"Category:{en_name}")
    if not en_body:
        print("  • EN page missing/empty – skipped"); return

    # Build replacement
    new_lines: List[str] = []

    # --- English block at top --------------------------------------
    new_lines.append("==English Content==")
    new_lines.append(en_body.rstrip())
    new_lines.append("")                 # blank line

    # --- keep every existing inter-wiki & cat ----------------------
    existing_iws  = IW_RX.findall(text)
    existing_cats = CAT_RX.findall(text)

    # --- extra inter-wikis from Wikidata ---------------------------
    if (qid := qid_for_en_category(f"Category:{en_name}")):
        sl = get_wd_sitelinks(qid)
        for lang, ttl in sl.items():
            iw = f"[[{lang}:Category:{ttl}]]"
            if iw not in existing_iws:
                existing_iws.append(iw)

    # sort for consistency
    existing_iws  = sorted(set(existing_iws))
    existing_cats = sorted(set(existing_cats))

    new_lines.extend(existing_iws)
    new_lines.append("")                 # spacer
    new_lines.append("==Local Content==")
    new_lines.extend(existing_cats)
    new_text = "\n".join(new_lines).rstrip() + "\n"

    if new_text == text:
        print("  • up-to-date")
        return

    if dry:
        print("  • (dry-run) would update")
    else:
        try:
            pg.save(new_text,
                    summary="Bot: import en-wiki content & complete inter-wikis (Tier-sync)")
            print("  • updated")
        except APIError as e:
            print("  ! save failed", e.code)
        time.sleep(THROTTLE)

# ── CLI ─────────────────────────────────────────────────────────────
ap = argparse.ArgumentParser(description="Sync EN content + inter-wikis for Tier_N_Categories_with_enwiki")
ap.add_argument("--test","-t",action="store_true",help="dry-run (no saves)")
args = ap.parse_args()

# ── RUN ─────────────────────────────────────────────────────────────
for meta in TIERS:
    print(f"\n=== {meta} ===")
    for member in collect_members(meta):
        print("→", member, end="")
        sync_page(member, dry=args.test)

print("\nFinished Tier sync.")
