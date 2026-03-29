"""
Fetch P11250 QuickStatements lines from the shintowiki wiki page.

Reads [[QuickStatements/P11250]] (public, no auth needed) and writes the
QS lines to a local file for submission by submit_daily_batch.py.
"""

import io
import re
import sys
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WIKI_API = "https://shinto.miraheze.org/w/api.php"
PAGE_TITLE = "QuickStatements/P11250"
OUTPUT_FILE = "p11250_miraheze_links.txt"
USER_AGENT = "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts"
QS_LINE_RE = re.compile(r'^Q\d+\|P11250\|"shinto:.+"$')


def main():
    print(f"Fetching [[{PAGE_TITLE}]] from shintowiki...")
    resp = requests.get(
        WIKI_API,
        params={
            "action": "parse",
            "page": PAGE_TITLE,
            "prop": "wikitext",
            "format": "json",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if resp.status_code == 429:
        print("WARNING: 429 Too Many Requests — writing empty file")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            pass
        return
    resp.raise_for_status()

    data = resp.json()
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")

    lines = []
    for line in wikitext.split("\n"):
        line = line.strip()
        if QS_LINE_RE.match(line):
            lines.append(line)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Wrote {len(lines)} QS lines to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
