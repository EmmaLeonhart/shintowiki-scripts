#!/usr/bin/env python3
"""
patch_ill_english_labels_v5.py  –  ShintoWiki ILL-template fixer
────────────────────────────────────────────────────────────────
* Reads page titles from Pages.txt (UTF-8, one per line).
* For every {{ill}} template:
    1. If the EN display title is already a non-redirect on **ShintoWiki**,
       skip (prevents breaking local links).
    2. Else find the Japanese pair (positional, numeric, or |ja=).
    3. Fetch its Q-ID, then:
         • If Wikidata has an English label – add/replace |1=<that label>.
         • Otherwise add the local English title as Wikidata’s EN label.
* Verbose logging shows every step.  All edits respect --dry.
"""

from __future__ import annotations
import argparse, logging, pathlib, sys, time
from typing import Any, Dict

import requests, mwclient, simplejson as json
import mwparserfromhell as mwp

# ─────────────────── credentials ─────────────────────────────────────────
WD_USER = "Immanuelle@ImmanuelleGeniTestBot"
WD_PASS = "4dgbha3p34arj1gj0sj2pmqp1jr89kbv"
SW_USER = "Immanuelle"
SW_PASS = "[REDACTED_SECRET_2]"
# ─────────────────────────────────────────────────────────────────────────

WD_API = "https://www.wikidata.org/w/api.php"
JA_API = "https://ja.wikipedia.org/w/api.php"
SESSION = requests.Session()
WD_TOKEN = ""
TOKEN_TS = 0.0
TOKEN_TTL = 25 * 60
MAX_RETRY = 6
EDIT_DELAY = 1.2

# ─── Wikidata helpers ────────────────────────────────────────────────────
def wd_login() -> None:
    global WD_TOKEN, TOKEN_TS
    tok = SESSION.get(WD_API, params={
        "action": "query", "meta": "tokens", "type": "login", "format": "json"
    }, timeout=30).json()["query"]["tokens"]["logintoken"]

    r = SESSION.post(WD_API, data={
        "action": "login", "lgname": WD_USER, "lgpassword": WD_PASS,
        "lgtoken": tok, "format": "json"
    }, timeout=30).json()
    if r["login"]["result"] != "Success":
        sys.exit(f"Wikidata login failed: {r}")

    WD_TOKEN = SESSION.get(WD_API, params={
        "action": "query", "meta": "tokens", "format": "json"
    }, timeout=30).json()["query"]["tokens"]["csrftoken"]
    TOKEN_TS = time.time()
    logging.info("Logged in to Wikidata as %s", WD_USER)

def wd_post(params: Dict[str, Any]) -> Dict[str, Any]:
    global WD_TOKEN, TOKEN_TS

    # 1. Refresh token every TTL seconds *without* re-logging
    if time.time() - TOKEN_TS > TOKEN_TTL:
        WD_TOKEN = SESSION.get(WD_API, params={
            "action": "query", "meta": "tokens", "format": "json"
        }, timeout=30).json()["query"]["tokens"]["csrftoken"]
        TOKEN_TS = time.time()
        logging.info("CSRF token refreshed")

    base = {"assert": "user", "token": WD_TOKEN,
            "format": "json", "bot": 1, "maxlag": 5}

    for attempt in range(1, MAX_RETRY + 1):
        r = SESSION.post(WD_API, data={**params, **base}, timeout=60)
        data = r.json()

        # If the CSRF token was invalidated (rare), just fetch a new
        # token — **do not** call action=login again.
        if data.get("error", {}).get("code") == "badtoken":
            WD_TOKEN = SESSION.get(WD_API, params={
                "action": "query", "meta": "tokens", "format": "json"
            }, timeout=30).json()["query"]["tokens"]["csrftoken"]
            base["token"] = WD_TOKEN
            TOKEN_TS = time.time()
            logging.warning("badtoken → refreshed CSRF, retry")
            continue

        if data.get("error", {}).get("code") in ("maxlag", "ratelimited"):
            time.sleep(6); continue
        if "error" in data:
            raise RuntimeError(f"Wikidata error: {data['error']}")

        time.sleep(EDIT_DELAY)
        return data
    raise RuntimeError("POST failed after retries")


def wd_entity(qid: str) -> Dict[str, Any]:
    return SESSION.get(WD_API, params={
        "action": "wbgetentities", "ids": qid, "format": "json"
    }, timeout=30).json()["entities"][qid]

# ─── Wikipedia / ShintoWiki helpers ──────────────────────────────────────
SW_SITE = mwclient.Site("shinto.miraheze.org", path="/w/")
SW_SITE.login(SW_USER, SW_PASS)

def ja_title_to_qid(title: str) -> str | None:
    data = SESSION.get(JA_API, params={
        "action": "query", "titles": title, "prop": "pageprops",
        "ppprop": "wikibase_item", "redirects": 1, "format": "json"
    }, timeout=30).json()
    page = next(iter(data["query"]["pages"].values()))
    return page.get("pageprops", {}).get("wikibase_item")

def shinto_title_status(title: str) -> str:
    pg = SW_SITE.pages[title]
    if not pg.exists:      return "missing"
    if pg.redirect:        return "redirect"
    return "exists"

# ─── mwparser helpers ────────────────────────────────────────────────────
def english_title(tpl: mwp.nodes.template.Template) -> str:
    if tpl.has("1"):
        return str(tpl.get("1").value).strip()
    for i, p in enumerate(tpl.params):
        if not p.showkey and i == 0:
            return str(p.value).strip()
    return ""

# ─── helpers: keep  |1=  and  |comment=  at the *end* ────────────────────
# ─── helpers: append or update tail parameters ───────────────────────────
def ensure_tail_params(tpl: mwp.nodes.template.Template,
                       en_target: str,
                       qid: str | None) -> bool:
    """
    Ensure three params live at the *end* of the template:

        |1=<en_target>
        |comment=changed title based on wikidata
        |WD=<qid>          (only if qid is given)

    Returns True iff the template text actually changes.
    """
    wanted = {
        "1": en_target,
        "comment": "changed title based on wikidata"
    }
    if qid:
        wanted["WD"] = qid

    changed = False
    for key, val in wanted.items():
        # Does key already exist?
        for p in tpl.params:
            if p.showkey and str(p.name).strip() == key:
                if str(p.value).strip() != val:
                    p.value = val
                    changed = True
                break
        else:
            # not found → append new param
            tpl.params.append(
                mwp.nodes.template.Parameter(name=key,
                                             value=val,
                                             showkey=True))
            changed = True
    return changed



def ja_title_from_ill(tpl: mwp.nodes.template.Template) -> str | None:
    if tpl.has("ja"):
        return str(tpl.get("ja").value).strip()

    slots: list[str] = []
    numeric: dict[int, str] = {}
    for p in tpl.params:
        if p.showkey:
            key = str(p.name).strip()
            if key.isdigit():
                numeric[int(key)] = str(p.value).strip()
        else:
            slots.append(str(p.value).strip())
    for idx, val in numeric.items():
        while len(slots) < idx:
            slots.append("")
        slots[idx - 1] = val
    i = 1
    while i < len(slots) - 1:
        if slots[i].lower() == "ja":
            return slots[i + 1]
        i += 2
    return None

# ─── per-page driver ─────────────────────────────────────────────────────
def process_page(title: str, dry: bool):
    page = SW_SITE.pages[title]
    text = page.text() if page.exists else None
    if text is None:
        logging.warning("! %s missing", title); return

    code = mwp.parse(text)
    changed = False

    for tpl in code.filter_templates(recursive=True):
        if tpl.name.strip().lower() != "ill":
            continue

        en_disp = english_title(tpl)
        logging.info("→ ILL en:'%s'", en_disp)

        if not en_disp:
            continue
        if shinto_title_status(en_disp) == "exists":
            logging.info("· local page blue – skip")
            continue

        ja_title = ja_title_from_ill(tpl)
        if not ja_title:
            logging.info("· no ja-pair – skip")
            continue

        qid = ja_title_to_qid(ja_title)
        if not qid:
            logging.info("· %s – no Q-ID", ja_title); continue

        entity = wd_entity(qid)
        labels = entity.get("labels", {})

        if "en" in labels:
            wd_en = labels["en"]["value"]
            if ensure_tail_params(tpl, wd_en, qid):
                logging.info("· appended |1=%s |WD=%s", wd_en, qid)
                changed = True

        else:
            labels["en"] = {"language": "en", "value": en_disp}
            if not dry:
                wd_post({
                    "action": "wbeditentity", "id": qid,
                    "data": json.dumps({"labels": labels}),
                    "summary": "Bot: add English label"
                })
                if ensure_tail_params(tpl, en_disp, qid):
                    logging.info("· set label & appended tail params")
                    changed = True

            logging.info("· set EN label on %s", qid)

    if changed:
        newtext = str(code)
        if newtext != text:
            if dry:
                logging.info("· (dry) would save page")
            else:
                page.save(newtext,
                          summary="Bot: add/fix |1= param in {{ill}}",
                          minor=True)
                logging.info("✓ saved page")

# ─── CLI driver ──────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="no writes anywhere")
    ap.add_argument("--pages", default="Pages.txt",
                    help="title list (default Pages.txt)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)-8s %(message)s")

    wd_login()
    titles = [ln.strip() for ln in pathlib.Path(args.pages)
              .read_text(encoding="utf-8").splitlines() if ln.strip()]

    for idx, t in enumerate(titles, 1):
        logging.info("(%d/%d) %s", idx, len(titles), t)
        try:
            process_page(t, args.dry)
        except Exception as e:
            logging.error("! error on %s – %s", t, e)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Aborted")
