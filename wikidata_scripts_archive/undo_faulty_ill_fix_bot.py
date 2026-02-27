#!/usr/bin/env python3
"""
ill_wikidata_fix_bot.py  –  FINAL-8
===================================
This release ensures **all** edge cases are tagged in the template itself:

1. **Jawiki**:
   - Missing → `ja_comment=jawiki link invalid`
   - Redirect → `ja_comment=jawiki redirects to <target>`
2. **Enwiki**:
   - Redirect → `comment=enwiki is a redirect`
   - Otherwise → safely convert to `[:en:…]` link
3. **Resolution pages** still created for jawiki OK + missing local target.

Key change: `make_replacer` now checks enwiki redirect *before* conversion
and always rewrites the template (with comment) for redirects.
"""

import os, sys, time, re, requests, mwclient
from typing import Dict, List, Tuple, Optional
from mwclient.errors import APIError

# ─── CONFIG ────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "EmmaBot"
PASSWORD   = "[REDACTED_SECRET_1]"
PAGES_FILE = "pages.txt"
THROTTLE   = 1.0

ILL_RE     = re.compile(r"\{\{\s*ill\|(.*?)\}\}", re.I | re.DOTALL)
API_WD     = "https://www.wikidata.org/w/api.php"
API_JAWIKI = "https://ja.wikipedia.org/w/api.php"
RAW_ENWIKI = "https://en.wikipedia.org/w/index.php"
UA         = {"User-Agent": "ill-fix-bot/1.7 (User:EmmaBot)"}
REDIR_RE   = re.compile(r"^#\s*redirect", re.I)

# ─── API JSON GET ─────────────────────────────────────────────────

def api_json(url: str, params: Dict) -> Dict:
    params["format"] = "json"
    r = requests.get(url, params=params, headers=UA, timeout=15)
    r.raise_for_status()
    return r.json()

# ─── Jawiki status ─────────────────────────────────────────────────

def jawiki_status(title: str) -> Tuple[str, Optional[str]]:
    data = api_json(API_JAWIKI, {"action": "query", "titles": title, "redirects": 1})
    page = next(iter(data["query"]["pages"].values()))
    if "missing" in page:
        return "missing", None
    for r in data["query"].get("redirects", []):
        if r.get("from","").lower() == title.lower():
            return "redirect", r.get("to")
    return "ok", None

# ─── Enwiki redirect detection ─────────────────────────────────────

def enwiki_is_redirect(title: str) -> bool:
    norm = title.replace(" ", "_")
    try:
        r = requests.get(
            RAW_ENWIKI,
            params={"action": "raw", "title": norm, "redirect": "no"},
            headers=UA,
            timeout=15
        )
        r.raise_for_status()
        for ln in r.text.splitlines():
            line = ln.strip()
            if not line:
                continue
            return bool(REDIR_RE.match(line))
        return False
    except Exception:
        return True

# ─── Fetch en title via Wikidata ───────────────────────────────────

def en_title_from_jawiki(title: str) -> Optional[str]:
    data = api_json(API_WD, {
        "action": "wbgetentities", "sites": "jawiki", "titles": title,
        "props": "sitelinks", "sitefilter": "enwiki",
    })
    for ent in data.get("entities", {}).values():
        sl = ent.get("sitelinks", {}).get("enwiki")
        if sl:
            return sl["title"]
    return None

# ─── Template parsing ──────────────────────────────────────────────

def split_params(inner: str):
    parts = [p.strip() for p in inner.split("|")]
    num, named = {}, {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            if k.isdigit(): num[int(k)] = v.strip()
            else: named[k.strip()] = v.strip()
    idx = 1
    for p in parts:
        if "=" in p: continue
        while idx in num: idx += 1
        num[idx] = p; idx += 1
    return parts, num, named


def find_jawiki(num, named, parts):
    if named.get("ja"):
        return named["ja"].strip()
    for n in sorted(num):
        if num[n] == "ja" and num.get(n+1,""):
            return num[n+1].strip()
    for i,p in enumerate(parts):
        if p == "ja" and i+1 < len(parts):
            return parts[i+1].strip()
    return None

# ─── Jawiki resolution pages ──────────────────────────────────────

def log_resolution(site, ja_title: str, src: str, tmpl: str):
    pg = site.pages[ja_title]
    entry = f"[[{src}]] linked to {tmpl}\n"
    content = "" if (pg.exists and pg.redirect) else (pg.text() if pg.exists else "")
    if entry in content: return
    content = re.sub(r"\n?\[\[Category:jawiki resolution pages\|.*?\]\]", "", content).rstrip()
    content = (content+"\n" if content else "") + entry
    cnt = content.count(" linked to ")
    content += f"\n[[Category:jawiki resolution pages|{cnt}]]\n"
    try: pg.save(content, summary=f"Bot: add link reference from {src}")
    except APIError: pass

# ─── Template replacer ─────────────────────────────────────────────

def make_replacer(site, page_title):
    def repl(m):
        raw = m.group(0)
        parts, num, named = split_params(m.group(1))
        ja = find_jawiki(num, named, parts)
        extra: List[str] = []

        if ja:
            st, tgt = jawiki_status(ja)
            if st == "missing":
                extra.append("ja_comment=jawiki link invalid")
            elif st == "redirect":
                extra.append(f"ja_comment=jawiki redirects to {tgt}")
            else:
                en_t = en_title_from_jawiki(ja)
                if en_t:
                    if enwiki_is_redirect(en_t):
                        extra.append("comment=enwiki is a redirect")
                    else:
                        lbl = named.get("lt","") or num.get(1,"")
                        lbl = lbl.strip()
                        if lbl:
                            return f"[[:en:{en_t}|{lbl}]]"
                # jawiki resolution page
                tgt_loc = num.get(1,"").strip()
                if not (tgt_loc and site.pages[tgt_loc].exists):
                    log_resolution(site, ja, page_title, raw)

        if extra:
            return "{{ill|" + "|".join(parts + extra) + "}}"
        return raw
    return repl

# ─── Page handler ─────────────────────────────────────────────────

def process_page(site, title):
    pg = site.pages[title]
    if not pg.exists or pg.redirect: return
    old = pg.text()
    new = ILL_RE.sub(make_replacer(site, title), old)
    if new != old:
        try: pg.save(new, summary="Bot: ill fix final-8")
        except APIError as e: print("Save failed", e)

# ─── Main loop ────────────────────────────────────────────────────

def main():
    if not os.path.exists(PAGES_FILE): sys.exit("Missing pages.txt")
    titles = [l.strip() for l in open(PAGES_FILE, encoding="utf-8") if l.strip() and not l.startswith("#")]
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    for i, t in enumerate(titles,1):
        print(f"{i}. [[{t}]]")
        process_page(site, t)
        time.sleep(THROTTLE)
    print("Done")

if __name__ == "__main__":
    main()
