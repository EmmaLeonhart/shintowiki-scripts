#!/usr/bin/env python3
"""
generate_doujou_address_fixes.py
=================================
Emit corrective QS lines for the 同上 address bug into
``doujou_address_fixes.txt`` (consumed by direct_daily_edits.py).

Input: ``doujou_resolution.json`` from resolve_doujou_addresses.py —
per QID the real address resolved from the jawiki per-district
式内社一覧 table (同上 = "same as the row above") and the source
article.

Because direct_daily_edits.py samples lines RANDOMLY, a remove+re-add
pair could split across days. So each emitted line is self-contained
and the fix converges in two phases, re-derived from LIVE Wikidata
state on every run:

  phase 1 — item still lacks the correct address:
      Qxxx|P6375|ja:"島根県..."|S143|Q177837|S4656|"https://ja.wikipedia.org/wiki/..."
  phase 2 — correct address present, 同上 still there:
      -Qxxx|P6375|ja:"同上"

Once neither condition holds the item emits nothing and has converged.
S143 = imported from Wikimedia project (Q177837 = Japanese Wikipedia),
S4656 = Wikimedia import URL — the citation Emma specified (the list
article the addresses were originally imported from).

Deliberately slow via the daily drip; multi-year convergence is fine
(Emma, 2026-07-04). Unmatched items in the JSON are printed for
manual/LLM handling, never guessed.
"""

import io
import json
import sys
import time
import urllib.parse

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

UA = {"User-Agent": "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"}
WD_API = "https://www.wikidata.org/w/api.php"
INPUT_FILE = "doujou_resolution.json"
OUTPUT_FILE = "doujou_address_fixes.txt"
JAWIKI_ITEM = "Q177837"  # Japanese Wikipedia


def fetch_p6375(qids):
    """{qid: [monolingual values]} for current P6375 claims."""
    out = {}
    qid_list = sorted(qids)
    for i in range(0, len(qid_list), 50):
        batch = qid_list[i:i + 50]
        r = requests.get(WD_API, params={
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "claims", "format": "json",
        }, headers=UA, timeout=60)
        if r.status_code == 429:
            print("WARNING: Wikidata 429 — aborting; writing no lines this run")
            return None
        r.raise_for_status()
        for qid, ent in r.json().get("entities", {}).items():
            vals = []
            for c in ent.get("claims", {}).get("P6375", []):
                dv = c.get("mainsnak", {}).get("datavalue", {}).get("value")
                if isinstance(dv, dict):
                    vals.append((dv.get("text"), dv.get("language")))
            out[qid] = vals
        time.sleep(0.3)
    return out


def main():
    try:
        with open(INPUT_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except OSError:
        print(f"{INPUT_FILE} not found — run resolve_doujou_addresses.py first; writing empty file")
        open(OUTPUT_FILE, "w", encoding="utf-8").close()
        return

    resolved = data.get("resolved", {})
    print(f"Resolved entries: {len(resolved)}; unmatched (manual): {len(data.get('unmatched', []))}")
    for u in data.get("unmatched", []):
        print(f"  manual: {u['qid']} {u['label']}")

    state = fetch_p6375(resolved.keys())
    if state is None:
        open(OUTPUT_FILE, "w", encoding="utf-8").close()
        return

    lines = []
    adds = removals = done = 0
    for qid, info in sorted(resolved.items()):
        addr = info["resolved_address"]
        url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(info["source_article"])
        vals = state.get(qid, [])
        has_doujou = ("同上", "ja") in vals
        has_addr = (addr, "ja") in vals
        if not has_addr:
            lines.append(f'{qid}|P6375|ja:"{addr}"|S143|{JAWIKI_ITEM}|S4656|"{url}"')
            adds += 1
        elif has_doujou:
            lines.append(f'-{qid}|P6375|ja:"同上"')
            removals += 1
        else:
            done += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"Wrote {len(lines)} lines ({adds} adds, {removals} removals; {done} converged) -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
