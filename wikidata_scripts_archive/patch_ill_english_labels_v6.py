#!/usr/bin/env python3
"""
patch_ill_english_labels_v6.py
──────────────────────────────
• Reads page titles from Pages.txt (UTF-8, one per line)
• For every {{ill}}:
    – skips if the EN title is already a blue link on ShintoWiki
    – locates the Japanese pair, fetches its Q-ID
    – reads the item's labels from Wikidata (no login, read-only)
    – if the item LACKS an English label:
        • appends  <label>,<QID>  to label_qid_pairs.csv (append mode)
    – in every case inserts tail params
        |1=<label>   |comment=changed title based on wikidata   |WD=Q…
      at the end of the template and saves the page (unless --dry)
"""

from __future__ import annotations
import argparse, csv, logging, pathlib, sys, time
from typing import Dict, Tuple, Set

import mwclient, mwparserfromhell as mwp, requests

# ─── credentials ─────────────────────────────────────────────────────────
SW_USER = "Immanuelle"
SW_PASS = "[REDACTED_SECRET_2]"
# ─────────────────────────────────────────────────────────────────────────

JA_API = "https://ja.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
SESSION = requests.Session()

# ─── ShintoWiki login ────────────────────────────────────────────────────
SW_SITE = mwclient.Site("shinto.miraheze.org", path="/w/")
SW_SITE.login(SW_USER, SW_PASS)

def shinto_title_status(title: str) -> str:
    pg = SW_SITE.pages[title]
    if not pg.exists:  return "missing"
    if pg.redirect:    return "redirect"
    return "exists"

# ─── look-ups ────────────────────────────────────────────────────────────
def ja_title_to_qid(title: str) -> str | None:
    data = SESSION.get(JA_API, params={
        "action": "query", "titles": title, "prop": "pageprops",
        "ppprop": "wikibase_item", "redirects": 1, "format": "json"
    }, timeout=30).json()
    page = next(iter(data["query"]["pages"].values()))
    return page.get("pageprops", {}).get("wikibase_item")

def item_has_en_label(qid: str) -> Tuple[bool, str | None]:
    """
    Return (has_en_label, current_label_or_None)
    """
    data = SESSION.get(WD_API, params={
        "action": "wbgetentities", "ids": qid, "props": "labels",
        "languages": "en", "format": "json"
    }, timeout=30).json()
    ent = data["entities"].get(qid, {})
    lbl = ent.get("labels", {}).get("en")
    return (lbl is not None, lbl["value"] if lbl else None)

# ─── template helpers ────────────────────────────────────────────────────
def english_title(tpl: mwp.nodes.template.Template) -> str:
    if tpl.has("1"):
        return str(tpl.get("1").value).strip()
    for i, p in enumerate(tpl.params):
        if not p.showkey and i == 0:
            return str(p.value).strip()
    return ""

def ensure_tail_params(tpl: mwp.nodes.template.Template,
                       en_target: str, qid: str) -> bool:
    wanted = {
        "1": en_target,
        "comment": "changed title based on wikidata",
        "WD": qid
    }
    changed = False
    for key, val in wanted.items():
        for p in tpl.params:
            if p.showkey and str(p.name).strip() == key:
                if str(p.value).strip() != val:
                    p.value = val
                    changed = True
                break
        else:
            tpl.params.append(
                mwp.nodes.template.Parameter(name=key,
                                             value=val,
                                             showkey=True))
            changed = True
    return changed

def ja_title_from_ill(tpl: mwp.nodes.template.Template) -> str | None:
    if tpl.has("ja"):
        return str(tpl.get("ja").value).strip()

    slots, numeric = [], {}
    for p in tpl.params:
        if p.showkey:
            k = str(p.name).strip()
            if k.isdigit():
                numeric[int(k)] = str(p.value).strip()
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
def process_page(title: str,
                 dry: bool,
                 writer,
                 seen: Set[Tuple[str, str]]):
    page = SW_SITE.pages[title]
    if not page.exists:
        logging.warning("! %s missing", title)
        return
    code = mwp.parse(page.text())
    changed = False

    for tpl in code.filter_templates(recursive=True):
        if tpl.name.strip().lower() != "ill":
            continue

        en_disp = english_title(tpl)
        if not en_disp:
            continue
        if shinto_title_status(en_disp) == "exists":
            continue

        ja_title = ja_title_from_ill(tpl)
        if not ja_title:
            continue

        qid = ja_title_to_qid(ja_title)
        if not qid:
            continue

        has_lbl, current_lbl = item_has_en_label(qid)
        label_for_csv = en_disp if not has_lbl else None

        if ensure_tail_params(tpl,
                              current_lbl or en_disp,
                              qid):
            changed = True

        if label_for_csv and (label_for_csv, qid) not in seen:
            writer.writerow([label_for_csv, qid])
            seen.add((label_for_csv, qid))
            logging.info("· queued CSV: %s , %s", label_for_csv, qid)

    if changed:
        if dry:
            logging.info("· (dry) would save %s", title)
        else:
            page.save(str(code),
                      summary="Bot: append |1=, |comment=, |WD= in {{ill}}",
                      minor=True)
            logging.info("✓ saved %s", title)

# ─── CLI driver ──────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true",
                    help="no ShintoWiki edits (CSV still written)")
    ap.add_argument("--pages", default="Pages.txt",
                    help="list of titles (default Pages.txt)")
    ap.add_argument("--csv", default="label_qid_pairs.csv",
                    help="CSV file to *append* to")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)-8s %(message)s")

    titles = [ln.strip() for ln in pathlib.Path(args.pages)
              .read_text(encoding="utf-8").splitlines() if ln.strip()]

    # open CSV in append mode
    with open(args.csv, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        seen: Set[Tuple[str, str]] = set()  # avoid duplicates within this run

        for idx, t in enumerate(titles, 1):
            logging.info("(%d/%d) %s", idx, len(titles), t)
            try:
                process_page(t, args.dry, writer, seen)
            except Exception as e:
                logging.error("! error on %s – %s", t, e)

    logging.info("✓ appended %d new rows to %s", len(seen), args.csv)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Aborted")
