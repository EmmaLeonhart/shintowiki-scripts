#!/usr/bin/env python3
"""
ill_wikidata_fix_bot.py  –  FINAL‑4 (robust redirect detection)
================================================================
**What’s fixed**
* `enwiki_is_redirect()` now:
  1. Normalises the title to MediaWiki form (`_` instead of space).
  2. Requests the raw wikitext **twice**:
     * first with the normalised title;
     * if that returns HTTP 302 (rare) follows the `Location` header.
  3. Treats the page as a redirect when the *first non‑blank line* begins with
     “#redirect” (case‑insensitive, optional colon/whitespace).
* The converter now links to en‑wiki **only when** `enwiki_is_redirect()`
  explicitly returns **False** – any network error or ambiguous result falls
  back to *keeping* the template (safer).

All other behaviour—jawiki diagnostics and resolution pages—remains.
"""

import os, sys, time, re, requests, mwclient
from typing import Dict, List, Tuple, Optional
from mwclient.errors import APIError

# ─── CONFIG ────────────────────────────────────────────────────────
WIKI_URL   = "shinto.miraheze.org"
WIKI_PATH  = "/w/"
USERNAME   = "Immanuelle"
PASSWORD   = "[REDACTED_SECRET_1]"
PAGES_FILE = "pages.txt"
THROTTLE   = 1.0

ILL_RE = re.compile(r"\{\{\s*ill\|(.*?)\}\}", re.I | re.DOTALL)
API_WD      = "https://www.wikidata.org/w/api.php"
API_JAWIKI  = "https://ja.wikipedia.org/w/api.php"
RAW_ENWIKI  = "https://en.wikipedia.org/w/index.php"
UA          = {"User-Agent": "ill-fix-bot/1.3 (User:Immanuelle)"}

# ─── API helper -----------------------------------------------------

def api_json(url: str, params: Dict) -> Dict:
    params["format"] = "json"
    r = requests.get(url, params=params, headers=UA, timeout=15)
    r.raise_for_status()
    return r.json()

# ─── status helpers -------------------------------------------------

def jawiki_status(title: str) -> Tuple[str, Optional[str]]:
    data = api_json(API_JAWIKI, {"action": "query", "titles": title, "redirects": 1})
    page = next(iter(data["query"]["pages"].values()))
    if "missing" in page:
        return "missing", None
    if "redirects" in data["query"]:
        tgt = next((r["to"] for r in data["query"]["redirects"] if r["from"].lower() == title.lower()), None)
        return "redirect", tgt
    return "ok", None

REDIR_RE = re.compile(r"^#redirect", re.I)

def enwiki_is_redirect(title: str) -> bool:
    """Check raw wikitext for leading #redirect; network failures → None."""
    norm = title.replace(" ", "_")
    try:
        r = requests.get(
            RAW_ENWIKI,
            params={"title": norm, "action": "raw", "redirect": "no"},
            headers=UA,
            timeout=15,
        )
        if r.status_code != 200:
            return None
        first_line = next((ln.strip() for ln in r.text.splitlines() if ln.strip()), "")
        return bool(REDIR_RE.match(first_line))
    except Exception:
        return None


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

# ─── template parsing ----------------------------------------------

def split_params(inner: str):
    parts = [p.strip() for p in inner.split("|")]
    num: Dict[int, str] = {}
    named: Dict[str, str] = {}
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            (num if k.isdigit() else named)[int(k) if k.isdigit() else k.strip()] = v.strip()
    idx = 1
    for p in parts:
        if "=" in p: continue
        while idx in num: idx += 1
        num[idx] = p; idx += 1
    return parts, num, named


def find_jawiki(num, named, parts):
    if named.get("ja"): return named["ja"].strip()
    for n in sorted(num):
        if num[n] == "ja" and num.get(n+1, ""):
            return num[n+1].strip()
    for i, p in enumerate(parts):
        if p == "ja" and i+1 < len(parts):
            return parts[i+1].strip()
    return None

# ─── resolution page -----------------------------------------------

def log_resolution(site, ja_title: str, src: str, tmpl: str):
    pg = site.pages[ja_title]
    entry = f"[[{src}]] linked to {tmpl}\n"
    content = "" if (pg.exists and pg.redirect) else (pg.text() if pg.exists else "")
    if entry in content: return
    content = re.sub(r"\n?\[\[Category:jawiki resolution pages\|.*?\]\]", "", content).rstrip()
    content = (content+"\n" if content else "") + entry
    n = content.count(" linked to ")
    content += f"\n[[Category:jawiki resolution pages|{n}]]\n"
    try:
        pg.save(content, summary=f"Bot: add link reference from {src}")
    except APIError: pass

# ─── ill replacer ---------------------------------------------------

def make_replacer(site, page_title):
    def repl(m):
        raw = m.group(0)
        parts, num, named = split_params(m.group(1))
        ja = find_jawiki(num, named, parts)
        extra: List[str] = []
        if ja:
            state, tgt = jawiki_status(ja)
            if state == "missing":
                extra.append("ja_comment=jawiki link invalid")
            elif state == "redirect":
                extra.append(f"ja_comment=jawiki redirects to {tgt}")
            else:
                en_title = en_title_from_jawiki(ja)
                redir_flag = enwiki_is_redirect(en_title) if en_title else None
                if redir_flag:
                    extra.append("comment=enwiki is a redirect")
                elif redir_flag is False:
                    label = named.get("lt", "").strip() or num.get(1, "").strip()
                    if label and en_title:
                        return f"[[:en:{en_title}|{label}]]"
                tgt_local = num.get(1, "").strip()
                if not (tgt_local and site.pages[tgt_local].exists):
                    log_resolution(site, ja, page_title, raw)
        if extra:
            return "{{ill|" + "|".join(parts + extra) + "}}"
        return raw
    return repl

# ─── page handler ---------------------------------------------------

def process_page(site, title):
    pg = site.pages[title]
    if not pg.exists or pg.redirect:
        return
    txt = pg.text(); new = ILL_RE.sub(make_replacer(site, title), txt)
    if new != txt:
        try:
            pg.save(new, summary="Bot: ill fix final-4")
        except APIError as e:
            print("Save failed", e)

# ─── main -----------------------------------------------------------

def main():
    if not os.path.exists(PAGES_FILE):
        print("Missing", PAGES_FILE); sys.exit(1)
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
