#!/usr/bin/env python3
"""
patch_ill_english_labels_v2.py  –  ShintoWiki ILL-template fixer
──────────────────────────────────────────────────────────────
Reads a list of page titles from **Pages.txt** (UTF-8, one per line).

For every {{ill}} it finds, the bot:

  • extracts the English display title (param 1 or first positional).  
  • If that EN title is already a non-redirect on enwiki → skip.  
  • Otherwise locates the Japanese pair anywhere in the template
       (positional, numeric 2/3, or named |ja=).  
  • Looks up its Q-ID via ja.wikipedia.org.

     – If the item HAS an English label → appends `|1=<label>`  
       to the template (unless already present).  
     – If it lacks an English label → sets the local English title
       as the EN label on Wikidata.

All edits respect `--dry`.

Usage
─────
  pip install mwparserfromhell mwclient simplejson requests
  python patch_ill_english_labels.py --dry        # log only
  python patch_ill_english_labels.py              # live writes
"""

from __future__ import annotations
import argparse, logging, pathlib, re, sys, time
from typing import Any, Dict

import requests, mwclient, simplejson as json
import mwparserfromhell as mwp        # pip install mwparserfromhell

# ────────────────────  C R E D E N T I A L S  ────────────────────────────
WD_USER = "Immanuelle@ImmanuelleGeniTestBot"
WD_PASS = "4dgbha3p34arj1gj0sj2pmqp1jr89kbv"
SW_USER = "Immanuelle"
SW_PASS = "[REDACTED_SECRET_1]"
# ──────────────────────────────────────────────────────────────────────────

WD_API   = "https://www.wikidata.org/w/api.php"
JA_API   = "https://ja.wikipedia.org/w/api.php"
EN_API   = "https://en.wikipedia.org/w/api.php"
SESSION  = requests.Session()
WD_TOKEN = ""
TOKEN_TS = 0.0
TOKEN_TTL = 25*60
MAX_RETRY = 6
EDIT_DELAY = 1.2

# ─── Wikidata helpers ────────────────────────────────────────────────────
def wd_login() -> None:
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

# ─── Wikipedia look-ups ───────────────────────────────────────────────────
def ja_title_to_qid(title:str)->str|None:
    data = SESSION.get(JA_API, params={
        "action":"query","titles":title,"prop":"pageprops",
        "ppprop":"wikibase_item","redirects":1,"format":"json"
    }, timeout=30).json()
    page = next(iter(data["query"]["pages"].values()))
    return page.get("pageprops",{}).get("wikibase_item")

def en_title_status(title:str)->str:
    """Return 'missing', 'redirect', or 'exists' for enwiki."""
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
    try: pg = SW_SITE.pages[title]; return pg.text() if pg.exists else None
    except Exception as e:
        logging.warning("! cannot fetch %s – %s", title, e); return None

def save_text(title:str, text:str, summary:str, dry:bool):
    if dry: return
    SW_SITE.pages[title].save(text, summary=summary, minor=True)

# ─── helpers: extract pieces from {{ill}} ─────────────────────────────────
def english_title(tpl:mwp.nodes.template.Template)->str:
    if tpl.has("1"): return str(tpl.get("1").value).strip()
    for i, p in enumerate(tpl.params):
        if p.showkey: continue
        if i == 0: return str(p.value).strip()
    return ""

def append_param_1(tpl:mwp.nodes.template.Template, value:str):
    if tpl.has("1"): return
    tpl.add("1", value, showkey=True)

def ja_title_from_ill(tpl:mwp.nodes.template.Template)->str|None:
    """Return Japanese title from any style of param."""
    # named |ja=
    if tpl.has("ja"):
        return str(tpl.get("ja").value).strip()

    # build ordered positional list incl. numeric keys
    slots: list[str] = []
    numeric: dict[int,str] = {}
    for p in tpl.params:
        if p.showkey:
            key = str(p.name).strip()
            if key.isdigit():
                numeric[int(key)] = str(p.value).strip()
            continue
        slots.append(str(p.value).strip())
    for idx,val in numeric.items():
        while len(slots) < idx: slots.append("")
        slots[idx-1] = val

    # scan pairs after English display (index 1 onward)
    i = 1
    while i < len(slots)-1:
        if slots[i].lower() == "ja":
            return slots[i+1]
        i += 2
    return None

# ─── per-page driver ─────────────────────────────────────────────────────
def process_page(title:str, dry:bool):
    text = fetch_text(title)
    if text is None:
        logging.warning("! missing %s", title); return

    modified = False
    code = mwp.parse(text)

    for tpl in code.filter_templates(recursive=True):
        if tpl.name.strip().lower() != "ill": continue

        en_disp = english_title(tpl)
        logging.info("→ ILL  en:'%s'  raw:'%s'", en_disp, tpl)

        if not en_disp: continue
        if en_title_status(en_disp) == "exists":
            logging.info("· link blue – skip"); continue   # already fine

        ja_title = ja_title_from_ill(tpl)
        if not ja_title:
            logging.info("· no ja-pair – skip"); continue

        qid = ja_title_to_qid(ja_title)
        if not qid:
            logging.info("· %s – no Q-ID", ja_title); continue

        entity = wd_entity(qid)
        labels = entity.get("labels", {})

        if "en" in labels:
            wd_en = labels["en"]["value"]
            append_param_1(tpl, wd_en)
            modified = True
            logging.info("· patched with |1=%s", wd_en)
        else:
            labels["en"] = {"language":"en","value":en_disp}
            if dry:
                logging.info("· (dry) set en-label %s → %s", en_disp, qid)
            else:
                wd_post({
                    "action":"wbeditentity",
                    "id":qid,
                    "data":json.dumps({"labels":labels}),
                    "summary":"Bot: add English label from ILL"
                })
            logging.info("· en-label set on %s", qid)

    if modified:
        save_text(title, str(code),
                  summary="Bot: add |1=English title to {{ill}}",
                  dry=dry)

# ─── CLI driver ──────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="no writes anywhere")
    ap.add_argument("--pages", default="Pages.txt",
                    help="file with one title per line (default Pages.txt)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)-8s %(message)s")

    wd_login()

    pages = [ln.strip() for ln in pathlib.Path(args.pages).read_text(
             encoding="utf-8").splitlines() if ln.strip()]
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
        sys.exit("Aborted")
