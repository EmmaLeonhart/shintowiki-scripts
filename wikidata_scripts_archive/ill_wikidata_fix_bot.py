#!/usr/bin/env python3
"""
ill_wikidata_fix_bot.py  –  FINAL-12
====================================
Adds a debug print at the start of each `{{ill|…}}` template processing,
so the raw template text is output before any parsing or network calls.

Other behaviors (jawiki/enwiki diagnostics, resolution pages) remain unchanged.
"""

import os, sys, time, re, requests, mwclient
from typing import Dict, List, Tuple, Optional
from mwclient.errors import APIError

# ─── CONFIG ────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_2]"
PAGES_FILE = "pages.txt"
THROTTLE   = 1.0  # seconds between edits

ILL_RE     = re.compile(r"\{\{\s*ill\|(.*?)\}\}", re.I | re.DOTALL)
API_WD     = "https://www.wikidata.org/w/api.php"
API_JAWIKI = "https://ja.wikipedia.org/w/api.php"
RAW_ENWIKI = "https://en.wikipedia.org/w/index.php"
UA         = {"User-Agent": "ill-fix-bot/1.10 (User:Immanuelle)"}
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
    for r in data.get("query", {}).get("redirects", []):
        if r.get("from"," ").lower() == title.lower():
            return "redirect", r.get("to")
    return "ok", None

# ─── Enwiki redirect detection ─────────────────────────────────────

def enwiki_is_redirect(title: str) -> bool:
    norm = title.replace(" ", "_")
    try:
        r = requests.get(
            RAW_ENWIKI,
            params={"action": "raw", "title": norm, "redirect": "no"},
            headers=UA, timeout=15
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
        "props": "sitelinks", "sitefilter": "enwiki"
    })
    for ent in data.get("entities", {}).values():
        sl = ent.get("sitelinks", {}).get("enwiki")
        if sl:
            return sl.get("title")
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
        if num[n] == "ja" and num.get(n+1, "").strip():
            return num[n+1].strip()
    for i, p in enumerate(parts):
        if p == "ja" and i+1 < len(parts):
            return parts[i+1].strip()
    return None

# ─── Jawiki resolution pages ──────────────────────────────────────

def log_resolution(site, ja_title: str, src: str, tmpl: str):
    import urllib.parse
    ja_decoded = urllib.parse.unquote(ja_title)
    ja_page_title = ja_decoded.replace('_', ' ')
    pg = site.pages[ja_page_title]
    if pg.exists:
        return
    entry = f"[[{src}]] linked to {tmpl}\n"
    content = pg.text() if pg.exists and not pg.redirect else ""
    if entry in content:
        return
    content = re.sub(r"\n?\[\[Category:jawiki resolution pages\|.*?\]\]", "", content).rstrip()
    content = (content + "\n" if content else "") + entry
    cnt = content.count(" linked to ")
    content += f"\n[[Category:jawiki resolution pages|{cnt}]]\n"
    try: pg.save(content, summary=f"Bot: add link reference from {src}")
    except APIError: pass

# ─── Template replacer ─────────────────────────────────────────────

def make_replacer(site, page_title):
    def repl(m):
        raw = m.group(0)
        print(f"Processing ILL template: {raw}")  # debug print
        parts, num, named = split_params(m.group(1))
        ja = find_jawiki(num, named, parts)
        diagnostics: List[str] = []

        if ja:
            st, tgt = jawiki_status(ja)
            if st == "missing":
                diagnostics.append("ja_comment=jawiki link invalid")
            elif st == "redirect":
                diagnostics.append(f"ja_comment=jawiki redirects to {tgt}")
            en_t = en_title_from_jawiki(ja)
            if en_t:
                if enwiki_is_redirect(en_t):
                    diagnostics.append("comment=enwiki is a redirect")
                else:
                    lbl = named.get("lt", "") or num.get(1, "")
                    lbl = lbl.strip()
                    if lbl:
                        return f"[[:en:{en_t}|{lbl}]]"
            if st == "ok":
                log_resolution(site, ja, page_title, raw)

        if diagnostics:
            return "{{ill|" + "|".join(parts + diagnostics) + "}}"
        return raw
    return repl

# ─── Page handler ─────────────────────────────────────────────────

def process_page(site, title):
    pg = site.pages[title]
    if not pg.exists or pg.redirect:
        return
    text = pg.text()
    new_text = ILL_RE.sub(make_replacer(site, title), text)
    if new_text != text:
        try: pg.save(new_text, summary="Bot: ill fix final-12")
        except APIError as e: print("Save failed", e)

# ─── Main loop ────────────────────────────────────────────────────

def main():
    if not os.path.exists(PAGES_FILE): sys.exit("Missing pages.txt")
    titles = [l.strip() for l in open(PAGES_FILE, encoding="utf-8") if l.strip() and not l.startswith("#")]
    site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
    site.login(USERNAME, PASSWORD)
    for i, t in enumerate(titles, 1):
        print(f"{i}. [[{t}]]")
        process_page(site, t)
        time.sleep(THROTTLE)
    print("Done")

if __name__ == "__main__":
    main()
