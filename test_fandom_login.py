"""
Smoke test: can we log in to shinto.fandom.com via mwclient and read a page?

Does NOT edit anything. Just:
  1. Load creds from .env
  2. mwclient.Site(...).login(...)
  3. Fetch Main_Page text (proves auth + read works)
  4. Print userinfo so we can confirm we're logged in as a human vs anonymous

Run: python test_fandom_login.py
"""

import io
import os
import sys
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


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


def main():
    load_env()

    host = os.getenv("FANDOM_WIKI_URL", "shinto.fandom.com")
    username = os.getenv("FANDOM_USERNAME")
    password = os.getenv("FANDOM_PASSWORD")

    if not username or not password:
        print("ERROR: FANDOM_USERNAME and FANDOM_PASSWORD must be set in .env")
        return 1

    print(f"Host: {host}")
    print(f"User: {username}")
    print()

    try:
        import mwclient
    except ImportError:
        print("ERROR: mwclient not installed. Run: pip install mwclient")
        return 1

    # Fandom wiki paths: most are at /api.php under the root.
    print("Step 1: Creating Site object...")
    try:
        site = mwclient.Site(
            host,
            path="/",
            clients_useragent="ShintowikiTest/0.1 (local test)",
        )
        print(f"  OK. MediaWiki version: {site.version}")
    except Exception as e:
        print(f"  FAIL creating Site: {e}")
        traceback.print_exc()
        return 1

    print()
    print("Step 2: Attempting login...")
    try:
        site.login(username, password)
        print("  OK. login() did not raise.")
    except Exception as e:
        print(f"  FAIL login: {e}")
        print()
        print("  Fandom often requires either:")
        print("   - a bot password from Special:BotPasswords on the wiki")
        print("   - Fandom SSO via services.fandom.com (needs browser / OAuth)")
        print("  Raw account passwords usually don't work for API login.")
        traceback.print_exc()
        return 1

    print()
    print("Step 3: Checking userinfo...")
    try:
        info = site.api("query", meta="userinfo", uiprop="groups|rights")
        ui = info.get("query", {}).get("userinfo", {})
        print(f"  logged-in name: {ui.get('name')!r}")
        print(f"  anon?: {ui.get('anon', False)}")
        print(f"  groups: {ui.get('groups', [])}")
        rights = ui.get("rights", [])
        interesting = [r for r in rights if r in ("edit", "createpage", "bot", "writeapi")]
        print(f"  relevant rights: {interesting}")
    except Exception as e:
        print(f"  FAIL userinfo: {e}")
        traceback.print_exc()
        return 1

    print()
    print("Step 4: Fetching Main_Page text...")
    try:
        page = site.pages["Main_Page"]
        if not page.exists:
            print("  Main_Page does not exist. Trying 'Shinto' instead.")
            page = site.pages["Shinto"]
        text = page.text()
        print(f"  OK. Read {len(text)} chars from {page.name!r}")
        print(f"  First 200 chars: {text[:200]!r}")
    except Exception as e:
        print(f"  FAIL reading page: {e}")
        traceback.print_exc()
        return 1

    print()
    print("=== All checks passed. Edits should be possible via mwclient. ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
