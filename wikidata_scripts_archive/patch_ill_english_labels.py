#!/usr/bin/env python3
"""
patch_ill_english_labels.py  –  ShintoWiki ILL-template fixer
──────────────────────────────────────────────────────────────
Reads a list of page titles from **Pages.txt** (one per line).  
For every {{ill}} template it finds, the bot:

  1. Determines the *displayed* English title  
     – param “1=” if given, otherwise the first positional param.
  2. Ignores the template if that English title already links to a
     non-redirect page on **en.wikipedia.org**.
  3. Otherwise looks up the Japanese side:
        • If the template has numbered params:
              2 = language code, 3 = foreign title
          or positional:  |ja|日本語題|
     • Fetches its **Wikidata Q-ID** via ja.wikipedia.org
  4. With the Q-ID:
        • If the item *has* an English label, appends
              `|1=<English label>`   (only if not already present).
        • If it lacks an English label, adds the local English title
          as the item’s English label on Wikidata.
  5. Saves the page back to ShintoWiki (unless --dry).

The bot touches both Wikidata and ShintoWiki, re-using the same request/
token machinery you already trust.

Usage
─────
  python patch_ill_english_labels.py --dry        # no writes anywhere
  python patch_ill_english_labels.py              # live mode
"""

from __future__ import annotations
import argparse, logging, re, sys, time, pathlib
from typing import Any, Dict

import requests, mwclient, simplejson as json
import mwparserfromhell as mwp      # pip install mwparserfromhell

# ────────────────────  C R E D E N T I A L S  ────────────────────────────
WD_USER = "Immanuelle@ImmanuelleGeniTestBot"   # BotPassword user
WD_PASS = "4dgbha3p34arj1gj0sj2pmqp1jr89kbv"   # BotPassword pass
SW_USER = "Immanuelle"                         # ShintoWiki user
SW_PASS = "[REDACTED_SECRET_2]"                       # ShintoWiki pass
# ──────────────────────────────────────────────────────────────────────────

WD_API   = "https://www.wikidata.org/w/api.php"
JA_API   = "https://ja.wikipedia.org/w/api.php"
EN_API   = "https://en.wikipedia.org/w/api.php"
SESSION  = requests.Session()
WD_TOKEN = ""
TOKEN_TS = 0.0
TOKEN_TTL = 25*60            # refresh every 25 min
MAX_RETRY = 6
EDIT_DELAY = 1.2

# ─── Wikidata helpers ────────────────────────────────────────────────────
def wd_login() -> None:
    """Log in with BotPassword and grab CSRF token."""
    global WD_TOKEN, TOKEN_TS
    tok = SESSION.get(WD_API, params={
        "action":"query","meta":"tokens","type":"login","format":"json"
    }, timeout=30).json()["query"]["tokens"]["logintoken"]

    r = SESSION.post(WD_API, data={
        "action":"login","lgname":WD_USER,"lgpassword":WD_PASS,
        "lgtoken":tok,"format":"json"
    }, timeout=30).json()
    if r["login"]["result"] != "Success":
        sys.exit(f"Wikidata login failed: {r}")

    WD_TOKEN = SESSION.get(WD_API, params={
        "action":"query","meta":"tokens","format":"json"
    }, timeout=30).json()["query"]["tokens"]["csrftoken"]
    TOKEN_TS = time.time()
    logging.info("Logged in to Wikidata as %s", WD_USER)

def wd_post(params: Dict[str, Any]) -> Dict[str, Any]:
    """POST with token-refresh + retry on lag."""
    global WD_TOKEN, TOKEN_TS
    if not WD_TOKEN or time.time() - TOKEN_TS > TOKEN_TTL:
        wd_login()

    base = {"assert":"user","token":WD_TOKEN,"format":"json",
            "bot":1,"maxlag":5}
    for attempt in range(1, MAX_RETRY+1):
        r = SESSION.post(WD_API, data={**params, **base}, timeout=60)
        try:
            data = r.json()
        except ValueError:
            logging.warning("non-JSON (%s) – retry %d/%d",
                            r.status_code, attempt, MAX_RETRY)
            time.sleep(4); continue
        if data.get("error",{}).get("code")=="assertuserfailed":
            logging.warning("session expired – relog")
            wd_login(); base["token"]=WD_TOKEN; continue
        if data.get("error",{}).get("code") in ("maxlag","ratelimited"):
            logging.warning("lag – retry %d/%d", attempt, MAX_RETRY)
            time.sleep(6); continue
        if "error" in data:
            raise RuntimeError(f"Wikidata error: {data['error']}")
        time.sleep(EDIT_DELAY)
        return data
    raise RuntimeError("POST failed after retries")

def wd_get(params: Dict[str,Any]) -> Dict[str,Any]:
    return SESSION.get(WD_API, params=params, timeout=30).json()

def wd_entity(qid:str)->Dict[str,Any]:
    return wd_get({"action":"wbgetentities","ids":qid,"format":"json"})["entities"][qid]

# ─── Wikipedia helpers ────────────────────────────────────────────────────
def ja_title_to_qid(title:str)->str|None:
    data = SESSION.get(JA_API, params={
        "action":"query","titles":title,"prop":"pageprops",
        "ppprop":"wikibase_item","redirects":1,"format":"json"
    }, timeout=30).json()
    page = next(iter(data["query"]["pages"].values()))
    return page.get("pageprops",{}).get("wikibase_item")

def en_title_status(title:str)->str:
    """
    Returns 'missing', 'redirect', or 'exists' for a title on en.wikipedia.
    """
    data = SESSION.get(EN_API, params={
        "action":"query","titles":title,"redirects":0,"format":"json"
    }, timeout=30).json()
    page = next(iter(data["query"]["pages"].values()))
    if "missing" in page: return "missing"
    if "redirect" in page: return "redirect"
    return "exists"

# ─── ShintoWiki session ──────────────────────────────────────────────────
SW_SITE = mwclient.Site("shinto.miraheze.org", path="/w/")
SW_SITE.login(SW_USER, SW_PASS)

def fetch_text(title:str)->str|None:
    try:
        pg = SW_SITE.pages[title]
        return pg.text() if pg.exists else None
    except Exception as e:
        logging.warning("! cannot fetch %s – %s", title, e); return None

def save_text(title:str, text:str, summary:str, dry:bool):
    if dry: return
    pg = SW_SITE.pages[title]
    pg.save(text, summary=summary, minor=True)

# ─── {{ill}} processing ──────────────────────────────────────────────────
def normalize_param_key(key:str)->str:
    return key.strip().lower()

def ill_english_title(tpl:mwp.nodes.template.Template)->str:
    # explicit 1=
    if tpl.has("1"):
        return tpl.get("1").value.strip()
    # first unnamed param
    for i, param in enumerate(tpl.params):
        if param.showkey:                 # skip named ones
            continue
        if i == 0:                        # first positional
            return param.value.strip()
    return ""

def ill_language_code_and_foreign(tpl:mwp.nodes.template.Template)->tuple[str|None,str|None]:
    """
    Returns (language_code, foreign_title)
    e.g. ('ja', '日本語名')
    """
    # numbered style 2=lang 3=title
    if tpl.has("2") and tpl.has("3"):
        return tpl.get("2").value.strip(), tpl.get("3").value.strip()

    # positional style |lang|title|
    positionals = [p.value.strip() for p in tpl.params if not p.showkey]
    if len(positionals) >= 3:
        return positionals[1], positionals[2]
    return None, None

def append_param_1(tpl:mwp.nodes.template.Template, value:str):
    if tpl.has("1"):      # don't clobber existing
        return
    tpl.add("1", value, showkey=True)

# ─── per-page driver ─────────────────────────────────────────────────────
def process_page(title:str, dry:bool):
    text = fetch_text(title)
    if text is None:
        logging.warning("! missing %s", title); return

    modified = False
    code = mwp.parse(text)

    for tpl in code.filter_templates(recursive=True):
        if tpl.name.strip().lower() != "ill":
            continue

        en_title = ill_english_title(tpl)
        if not en_title:
            continue                       # ill with no English side?

        status = en_title_status(en_title)
        if status == "exists":
            continue                       # link already blue & non-redirect

        # get foreign (Japanese) side
        lang_code, ja_title = ill_language_code_and_foreign(tpl)
        if lang_code != "ja" or not ja_title:
            continue                       # not a ja-link or badly formed

        qid = ja_title_to_qid(ja_title)
        if not qid:
            logging.info("· %s – %s → no Q-ID", title, ja_title); continue

        entity = wd_entity(qid)
        labels = entity.get("labels", {})
        if "en" in labels:
            wd_en = labels["en"]["value"]
            append_param_1(tpl, wd_en)
            modified = True
            logging.info("· %s – ILL patched with %s", title, wd_en)
        else:
            # add English label to Wikidata
            if dry:
                logging.info("· (dry) add en-label %s → %s", en_title, qid)
            else:
                labels["en"] = {"language":"en","value":en_title}
                wd_post({
                    "action":"wbeditentity",
                    "id":qid,
                    "data":json.dumps({"labels":labels}),
                    "summary":"Bot: add English label from ILL"
                })
            logging.info("· %s – en-label set on %s", title, qid)

    if modified:
        save_text(title, str(code),
                  summary="Bot: add |1=English title to {{ill}}",
                  dry=dry)

# ─── CLI driver ───────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="no writes to WD or SW")
    ap.add_argument("--pages", default="Pages.txt",
                    help="file with one page title per line (default Pages.txt)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)-8s %(message)s")

    wd_login()

    pages = [ln.rstrip("\n") for ln in pathlib.Path(args.pages).read_text(encoding="utf-8").splitlines() if ln.strip()]
    for idx, title in enumerate(pages, 1):
        logging.info("(%d/%d) %s", idx, len(pages), title)
        try:
            process_page(title, args.dry)
        except Exception as e:
            logging.error("! error on %s – %s", title, e)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Aborted by Ctrl-C")
