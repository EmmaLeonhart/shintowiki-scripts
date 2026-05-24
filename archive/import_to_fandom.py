"""
Import a shintowiki page's full history into shinto.fandom.com.

Pipeline:
  1. Fetch full-history XML via shinto.miraheze.org Special:Export.
  2. Log in to shinto.fandom.com with .env bot password.
  3. POST that XML to the fandom wiki's action=import.

Usage:
    python import_to_fandom.py                     # imports "Main Page"
    python import_to_fandom.py "Some Page Title"   # arbitrary page
    python import_to_fandom.py "Main Page" --dry-run   # fetch only, no import
"""

import argparse
import io
import json
import os
import sys
import traceback

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


SRC_HOST = "shinto.miraheze.org"
SRC_EXPORT_URL = f"https://{SRC_HOST}/w/index.php"
DST_HOST = "shinto.fandom.com"
DST_API_URL = f"https://{DST_HOST}/api.php"
USER_AGENT = "ShintowikiMigrationTest/0.1 (local test; User:Their_Eminence)"


def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def fetch_xml(title: str) -> str:
    """Full-history XML for one page from shintowiki's Special:Export."""
    print(f"Fetching {title!r} from {SRC_HOST} (full history)...")
    # NOTE: `curonly` must be OMITTED for full history. Setting it to "0"
    # doesn't work — SpecialExport.php uses $request->getCheck('curonly'),
    # which treats any present value (even "0") as truthy.
    # history=1 forces the include-history path explicitly.
    resp = requests.post(
        SRC_EXPORT_URL,
        data={
            "title": "Special:Export",
            "pages": title,
            "history": "1",
            "wpDownload": "1",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=300,
    )
    resp.raise_for_status()
    xml = resp.text
    if "<mediawiki" not in xml:
        raise RuntimeError(f"Export didn't return MediaWiki XML. First 200 chars: {xml[:200]!r}")
    print(f"  OK. {len(xml)} chars, {xml.count('<revision>')} revisions.")
    return xml


def import_xml(xml_text: str) -> dict:
    """POST xml to the fandom wiki's action=import. Returns the JSON response."""
    import mwclient

    username = os.getenv("FANDOM_USERNAME")
    password = os.getenv("FANDOM_PASSWORD")
    if not username or not password:
        raise RuntimeError("FANDOM_USERNAME / FANDOM_PASSWORD not set in .env")

    print(f"Logging in to {DST_HOST} as {username}...")
    site = mwclient.Site(DST_HOST, path="/", clients_useragent=USER_AGENT)
    site.login(username, password)
    print("  OK.")

    print("Requesting CSRF token...")
    token = site.get_token("csrf")

    print(f"POSTing XML to {DST_API_URL} action=import ({len(xml_text)} chars)...")
    # Use the mwclient connection's session so auth cookies ride along.
    resp = site.connection.post(
        DST_API_URL,
        data={
            "action": "import",
            "format": "json",
            "token": token,
            "summary": "Import of revision history from shinto.miraheze.org",
            # Required by MediaWiki for XML upload: prefix applied to remote
            # usernames in the log so edits by shintowiki's "Immanuelle" show
            # as "shintowiki>Immanuelle" on fandom rather than getting
            # collapsed into a local account of the same name.
            "interwikiprefix": "shintowiki",
        },
        files={
            "xml": ("export.xml", xml_text.encode("utf-8"), "application/xml"),
        },
        headers={"User-Agent": USER_AGENT},
        timeout=300,
    )
    print(f"  HTTP {resp.status_code}")
    try:
        body = resp.json()
    except Exception:
        print(f"  Response was not JSON. First 500 chars: {resp.text[:500]!r}")
        raise
    return body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("page", nargs="?", default="Main Page",
                        help="Title of the page to import.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and dump XML, skip the import POST.")
    parser.add_argument("--save-xml", help="Write fetched XML to this path")
    args = parser.parse_args()

    load_env()

    try:
        xml = fetch_xml(args.page)
    except Exception as e:
        print(f"FETCH FAILED: {e}")
        traceback.print_exc()
        return 1

    if args.save_xml:
        with open(args.save_xml, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"Wrote XML to {args.save_xml}")

    if args.dry_run:
        print("\n--dry-run: skipping import. XML first 400 chars:")
        print(xml[:400])
        return 0

    try:
        body = import_xml(xml)
    except Exception as e:
        print(f"IMPORT FAILED: {e}")
        traceback.print_exc()
        return 1

    print()
    print("=== Import response ===")
    print(json.dumps(body, indent=2, ensure_ascii=False))

    if "error" in body:
        print(f"\nERROR from API: {body['error']}")
        return 1
    imported = body.get("import", [])
    if imported:
        print(f"\nImported {len(imported)} page(s):")
        for entry in imported:
            print(f"  - {entry.get('title')!r}: "
                  f"revisions={entry.get('revisions')} ns={entry.get('ns')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
