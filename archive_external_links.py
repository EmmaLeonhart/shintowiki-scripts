#!/usr/bin/env python3
"""
archive_all_external_links.py
─────────────────────────────
Walk every page on the wiki and send each external URL found in the
wikitext to the Internet Archive's Wayback Machine (web.archive.org).

* Skips URLs that already have a Wayback snapshot from the last 24 h.
* Sleeps between requests so you don’t hammer either API.
* Logs every action to the console.

DEPENDENCIES:
  pip install mwclient beautifulsoup4 requests

USAGE:
  python archive_all_external_links.py
"""

import re, time, urllib.parse, datetime as dt, requests, mwclient
from html import unescape
from bs4 import BeautifulSoup as Soup
from mwclient.errors import APIError

# ─── CONFIG ─────────────────────────────────────────────────────────
API_URL   = "https://shinto.miraheze.org/w/api.php"
USERNAME  = "Immanuelle"
PASSWORD  = "[REDACTED_SECRET_1]"
WP_THROTTLE  = 0.2   # seconds between page fetches
WB_THROTTLE  = 1.0   # seconds between Wayback “save” calls

SAVE_ENDPOINT   = "https://web.archive.org/save/"
CDX_API         = "https://web.archive.org/cdx/search/cdx"

HEADERS = {
    "User-Agent": "all-links-archiver/0.1 (User:Immanuelle)",
    "Accept":     "application/json"
}

URL_RX = re.compile(r"https?://[^\s\]<>\"']+", re.I)

# ─── HELPERS ────────────────────────────────────────────────────────
def have_recent_capture(url: str, hours: int = 24) -> bool:
    """Return True if Wayback already has a capture in the past *hours*."""
    try:
        r = requests.get(
            CDX_API,
            params={
                "url": url,
                "limit": 1,
                "filter": "statuscode:200",
                "output": "json",
                "collapse": "digest"
            },
            headers=HEADERS,
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        if len(data) < 2:        # first row is header
            return False
        ts = data[1][1]          # timestamp YYYYMMDDhhmmss
        snap_time = dt.datetime.strptime(ts, "%Y%m%d%H%M%S")
        return (dt.datetime.utcnow() - snap_time).total_seconds() < hours*3600
    except Exception:
        return False   # on any error, treat as not-archived


def send_to_wayback(url: str) -> None:
    """Fire-and-forget save request."""
    try:
        r = requests.get(SAVE_ENDPOINT + url, headers=HEADERS, timeout=60)
        print(f"      ↳ archive request → {r.status_code}")
    except Exception as e:
        print(f"      ! archive failed: {e}")


def external_links_from_wikitext(text: str) -> set[str]:
    """Quick & dirty: find bare URLs in wikitext *and* in raw HTML comments."""
    urls = set(URL_RX.findall(text))

    # also scan any <ref> tags (they may hide links HTML-encoded)
    for m in re.finditer(r"<ref[^>]*>(.*?)</ref>", text, re.I|re.S):
        frag = unescape(m.group(1))
        urls.update(URL_RX.findall(frag))
        # in case somebody shoved raw HTML
        soup = Soup(frag, "html.parser")
        for a in soup.find_all("a", href=True):
            urls.add(a["href"])

    return urls


# ─── MAIN ───────────────────────────────────────────────────────────
def main() -> None:
    parsed = urllib.parse.urlparse(API_URL)
    site   = mwclient.Site(parsed.netloc, path=parsed.path.rsplit("/api.php",1)[0]+"/")
    site.login(USERNAME, PASSWORD)
    print("Logged in – scanning every page for external links…")

    apcontinue = None
    while True:
        params = {
            "action":"query", "list":"allpages",
            "aplimit":"max",  "format":"json"
        }
        if apcontinue:
            params["apcontinue"] = apcontinue
        batch = site.api(**params)

        for ap in batch["query"]["allpages"]:
            title = ap["title"]
            page  = site.pages[title]
            try:
                text = page.text()
            except APIError:
                continue

            urls = external_links_from_wikitext(text)
            if not urls:
                continue

            print(f"\n→ {title}  ({len(urls)} URLs)")
            for url in sorted(urls):
                if have_recent_capture(url):
                    print(f"   – already archived: {url}")
                    continue
                print(f"   + archiving {url} …")
                send_to_wayback(url)
                time.sleep(WB_THROTTLE)

            time.sleep(WP_THROTTLE)

        if "continue" in batch:
            apcontinue = batch["continue"]["apcontinue"]
        else:
            break

    print("\nFinished archiving pass.")

if __name__ == "__main__":
    main()
