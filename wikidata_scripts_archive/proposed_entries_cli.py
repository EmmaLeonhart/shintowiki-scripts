#!/usr/bin/env python3
"""
proposed_entries_cli.py – interactive CLI replacement for proposed_entries_streamlit.py

No Streamlit or pandas required.
Dependencies: pymongo, requests, mwclient, mwparserfromhell

Usage:
    python proposed_entries_cli.py
    python proposed_entries_cli.py --uri mongodb://user:pass@host:27017
    python proposed_entries_cli.py --collection missing_ills
"""

import os
import re
import time
import json
import argparse
from typing import Any, Dict, List, Set

import requests
import mwclient
import mwparserfromhell as mwp
from pymongo import MongoClient

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_URI = "mongodb://localhost:27017"
DB_NAME     = "shinto_label_review"
COLL_PROP   = "proposed_labels"   # items with QID but no en-label
COLL_MISS   = "missing_ills"      # no Wikidata item yet

WD_USER = os.getenv("WD_USERNAME", "EmmaBot@EmmaBotMisc")
WD_PASS = os.getenv("WD_PASSWORD", "")

SW_USER = os.getenv("WIKI_USERNAME", "EmmaBot")
SW_PASS = os.getenv("WIKI_PASSWORD", "")

WD_API = "https://www.wikidata.org/w/api.php"
UA     = "ShintoLabelDashboard/0.7 (User:EmmaBot)"
PAUSE  = 0.5  # seconds between ShintoWiki edits

# ──────────────────────────────────────────────────────────────────────────────
# MongoDB helpers
# ──────────────────────────────────────────────────────────────────────────────

_client: MongoClient | None = None


def mongo_client(uri: str = DEFAULT_URI) -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(uri)
    return _client


def fetch_docs(uri: str, coll: str, filters: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    return list(mongo_client(uri)[DB_NAME][coll].find(filters or {}, projection={"_id": False}))


def delete_many(uri: str, coll: str, db_field: str, values: List[str]) -> int:
    res = mongo_client(uri)[DB_NAME][coll].delete_many({db_field: {"$in": values}})
    return res.deleted_count


def mark_created(uri: str, ja_label: str, qid: str) -> None:
    mongo_client(uri)[DB_NAME][COLL_MISS].update_one({"ja": ja_label}, {"$set": {"qid": qid}})


# ──────────────────────────────────────────────────────────────────────────────
# Wikidata helpers
# ──────────────────────────────────────────────────────────────────────────────

def wd_login() -> tuple[requests.Session, str]:
    sess = requests.Session()
    sess.headers.update({"User-Agent": UA})
    lg_token = sess.get(
        WD_API,
        params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
        timeout=60,
    ).json()["query"]["tokens"]["logintoken"]
    login_out = sess.post(
        WD_API,
        data={"action": "login", "lgname": WD_USER, "lgpassword": WD_PASS,
              "lgtoken": lg_token, "format": "json"},
        timeout=60,
    ).json()
    if login_out.get("login", {}).get("result") != "Success":
        raise RuntimeError(f"Wikidata login failed: {login_out}")
    csrf = sess.get(
        WD_API,
        params={"action": "query", "meta": "tokens", "format": "json"},
        timeout=60,
    ).json()["query"]["tokens"]["csrftoken"]
    return sess, csrf


def wd_create_item(
    sess: requests.Session,
    csrf: str,
    labels_by_lang: Dict[str, List[str]],
    summary: str,
) -> str:
    """Create a new item with labels + aliases for every language present."""
    data: Dict[str, Any] = {"labels": {}, "aliases": {}}
    for lang, variants in labels_by_lang.items():
        if not variants:
            continue
        data["labels"][lang] = {"language": lang, "value": variants[0]}
        if len(variants) > 1:
            data["aliases"][lang] = [{"language": lang, "value": v} for v in variants[1:]]
    out = sess.post(
        WD_API,
        data={
            "action": "wbeditentity",
            "new": "item",
            "data": json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            "token": csrf,
            "bot": 1,
            "summary": summary,
            "format": "json",
        },
        timeout=60,
    ).json()
    if out.get("success") != 1:
        raise RuntimeError(out)
    return out["entity"]["id"]


# ──────────────────────────────────────────────────────────────────────────────
# ShintoWiki helpers
# ──────────────────────────────────────────────────────────────────────────────

_sw_site = None


def sw_site():
    global _sw_site
    if _sw_site is None:
        site = mwclient.Site("shinto.miraheze.org", path="/w/")
        site.login(SW_USER, SW_PASS)
        _sw_site = site
    return _sw_site


def patch_ill(tpl: mwp.nodes.template.Template, qid: str) -> bool:
    """Append or update |qid=Qxxx. Returns True if template changed."""
    for p in tpl.params:
        if p.showkey and str(p.name).strip().lower() == "qid":
            if str(p.value).strip() == qid:
                return False
            p.value = qid
            return True
    tpl.params.append(mwp.nodes.template.Parameter(name="qid", value=qid, showkey=True))
    return True


def _extract_ja_label(tpl: mwp.nodes.template.Template) -> str | None:
    """Return the ja label inside a {{ill}} template, regardless of param order."""
    if tpl.has("ja"):
        return str(tpl.get("ja").value).strip()
    parts: List[str] = []
    numbered: Dict[int, str] = {}
    for p in tpl.params:
        if p.showkey:
            key = str(p.name).strip()
            if key.isdigit():
                numbered[int(key)] = str(p.value).strip()
        else:
            parts.append(str(p.value).strip())
    for idx, val in numbered.items():
        while len(parts) < idx:
            parts.append("")
        parts[idx - 1] = val
    i = 0
    while i < len(parts) - 1:
        if parts[i].lower() == "ja":
            return parts[i + 1]
        i += 1
    return None


def update_pages_with_qid(ja_label: str, qid: str, pages: Set[str]) -> None:
    """Insert |qid=<qid> into every {{ill}} with the given ja label."""
    site = sw_site()
    for title in pages:
        pg = site.pages[title]
        if not pg.exists:
            continue
        original_text = pg.text()
        code = mwp.parse(original_text)
        changed_structured = False

        for tpl in code.filter_templates(recursive=True):
            if tpl.name.strip().lower() != "ill":
                continue
            if _extract_ja_label(tpl) == ja_label:
                if patch_ill(tpl, qid):
                    changed_structured = True

        if changed_structured:
            pg.save(str(code), summary=f"Bot: add |qid={qid} in {{ill}}", minor=True)
            time.sleep(PAUSE)
            continue

        # regex fallback for odd cases
        def add_qid_match(match: re.Match) -> str:
            chunk = match.group(1)
            if "|qid=" in chunk.lower():
                return match.group(0)
            return chunk + f"|qid={qid}" + match.group(2)

        pattern = re.compile(
            r"(\{\{\s*ill[^{}]*?" + re.escape(ja_label) + r"[^{}]*?)(\}\})",
            re.IGNORECASE | re.DOTALL,
        )
        new_text, n_sub = pattern.subn(add_qid_match, original_text)
        if n_sub:
            pg.save(new_text, summary=f"Bot: add |qid={qid} in {{ill}} (regex)", minor=True)
            time.sleep(PAUSE)


# ──────────────────────────────────────────────────────────────────────────────
# Display helpers
# ──────────────────────────────────────────────────────────────────────────────

def _col_widths(rows: List[List[str]], headers: List[str]) -> List[int]:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    return widths


def print_table(headers: List[str], rows: List[List[str]]) -> None:
    widths = _col_widths(rows, headers)
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt = "|" + "|".join(f" {{:<{w}}} " for w in widths) + "|"
    print(sep)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*row))
    print(sep)


def rows_for_coll(
    coll: str, docs: List[Dict[str, Any]]
) -> tuple[List[str], List[List[str]]]:
    if coll == COLL_PROP:
        headers = ["#", "QID", "Proposed English Label"]
        rows = [[str(i + 1), d.get("qid", ""), d.get("proposed_label", "")] for i, d in enumerate(docs)]
    else:
        headers = ["#", "JA label", "EN variants", "Languages", "Occurrences"]
        rows = []
        for i, d in enumerate(docs):
            labels = d.get("labels", {})
            rows.append([
                str(i + 1),
                d.get("ja", ""),
                ", ".join(labels.get("en", [])),
                ", ".join(sorted(labels.keys())),
                str(len(d.get("occurrences", []))),
            ])
    return headers, rows


def parse_selection(s: str, n: int) -> List[int]:
    """Parse '1,3-5,7' into a sorted list of 0-based indices."""
    indices: set[int] = set()
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            indices.update(range(int(a) - 1, int(b)))
        else:
            indices.add(int(part) - 1)
    return sorted(i for i in indices if 0 <= i < n)


# ──────────────────────────────────────────────────────────────────────────────
# Actions
# ──────────────────────────────────────────────────────────────────────────────

def build_filters(coll: str, text_filter: str) -> Dict[str, Any]:
    if not text_filter:
        return {}
    regex = {"$regex": text_filter, "$options": "i"}
    if coll == COLL_PROP:
        return {"$or": [{"qid": regex}, {"proposed_label": regex}]}
    return {"$or": [{"ja": regex}, {"labels.en": regex}]}


def action_delete(uri: str, coll: str, docs: List[Dict], indices: List[int]) -> None:
    selected = [docs[i] for i in indices]
    db_field = "qid" if coll == COLL_PROP else "ja"
    values = [d[db_field] for d in selected]
    print(f"\nAbout to delete {len(values)} document(s):")
    for v in values:
        print(f"  • {v}")
    if input("Confirm? [y/N] ").strip().lower() != "y":
        print("Cancelled.")
        return
    n = delete_many(uri, coll, db_field, values)
    print(f"Deleted {n} document(s).")


def action_create(uri: str, docs: List[Dict], indices: List[int]) -> None:
    selected = [docs[i] for i in indices]
    print(f"\nAbout to create Wikidata items for {len(selected)} entry(s):")
    for d in selected:
        print(f"  • {d.get('ja', '?')}")
    if input("Confirm? [y/N] ").strip().lower() != "y":
        print("Cancelled.")
        return

    try:
        sess, csrf = wd_login()
    except RuntimeError as e:
        print(f"ERROR: Wikidata login failed: {e}")
        return

    created: Dict[str, str] = {}
    for doc in selected:
        ja_label = doc.get("ja", "")
        labels_by_lang: Dict[str, List[str]] = doc.get("labels", {})
        en_variants = labels_by_lang.get("en", [])
        en_main = en_variants[0] if en_variants else None
        occ = doc.get("occurrences", [{}])[0] if doc.get("occurrences") else {}
        jp_src  = occ.get("translated_from", "?")
        en_page = occ.get("page", "?")
        summary = (
            f"Created item for red-link present on {jp_src}, {en_page}"
            f" – '{ja_label}' / '{en_main or ''}'"
        )
        try:
            qid = wd_create_item(sess, csrf, labels_by_lang, summary)
        except Exception as e:
            print(f"  FAILED to create item for {ja_label}: {e}")
            continue

        pages_set = {o.get("page") for o in doc.get("occurrences", []) if o.get("page")}
        try:
            update_pages_with_qid(ja_label, qid, pages_set)
            mark_created(uri, ja_label, qid)
            created[ja_label] = qid
            print(f"  Created {qid} for '{ja_label}'")
        except Exception as e:
            print(f"  Created {qid} but failed to update pages: {e}")

        time.sleep(PAUSE)

    if created:
        print(f"\nCreated: {', '.join(created.values())}")
    else:
        print("No items created.")


# ──────────────────────────────────────────────────────────────────────────────
# Interactive loop
# ──────────────────────────────────────────────────────────────────────────────

def run_interactive(uri: str, collection: str) -> None:
    text_filter = ""
    while True:
        filters = build_filters(collection, text_filter)
        docs    = fetch_docs(uri, collection, filters)
        headers, rows = rows_for_coll(collection, docs)

        coll_label = (
            "Proposed English labels" if collection == COLL_PROP
            else "ILLs with no Wikidata item"
        )
        print(f"\n{'─' * 60}")
        print(f"Collection : {coll_label}")
        print(f"Filter     : '{text_filter or 'none'}'  |  {len(docs)} row(s)")
        print()
        if rows:
            print_table(headers, rows)
        else:
            print("  (no results)")

        print("\nCommands:")
        print("  d <nums>   – delete rows (e.g. d 1,3-5)")
        if collection == COLL_MISS:
            print("  c <nums>   – create Wikidata items for rows")
        print("  f <text>   – set text filter  (just 'f' to clear)")
        print(f"  s          – switch to {'missing_ills' if collection == COLL_PROP else 'proposed_labels'}")
        print("  r          – refresh")
        print("  q          – quit")

        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not cmd:
            continue

        if cmd.lower() == "q":
            print("Bye.")
            break

        if cmd.lower() == "r":
            continue

        if cmd.lower().startswith("f "):
            text_filter = cmd[2:].strip()
        elif cmd.lower() == "f":
            text_filter = ""

        elif cmd.lower() == "s":
            collection  = COLL_MISS if collection == COLL_PROP else COLL_PROP
            text_filter = ""

        elif cmd.lower().startswith("d "):
            indices = parse_selection(cmd[2:], len(docs))
            if not indices:
                print("No valid rows selected.")
            else:
                action_delete(uri, collection, docs, indices)

        elif cmd.lower().startswith("c ") and collection == COLL_MISS:
            indices = parse_selection(cmd[2:], len(docs))
            if not indices:
                print("No valid rows selected.")
            else:
                action_create(uri, docs, indices)

        else:
            print("Unknown command.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ShintoWiki label review CLI")
    parser.add_argument(
        "--uri",
        default=os.getenv("MONGO_URI", DEFAULT_URI),
        help="MongoDB connection URI (default: $MONGO_URI or mongodb://localhost:27017)",
    )
    parser.add_argument(
        "--collection",
        choices=[COLL_PROP, COLL_MISS],
        default=COLL_PROP,
        help="Collection to open on launch",
    )
    args = parser.parse_args()
    run_interactive(args.uri, args.collection)


if __name__ == "__main__":
    main()
