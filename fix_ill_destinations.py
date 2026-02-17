#!/usr/bin/env python3
"""
fix_ill_destinations.py
=======================
Goes through all mainspace pages and fixes {{ill|...}} templates.

For each ill template with |WD=QNNN|, resolve the correct destination (1=).
Priority:
  1. Wiki QID redirect (check if page "QNNN" redirects somewhere)
  2. enwiki article title (from Wikidata sitelinks)
  3. English label (from Wikidata)
  4. Last lt= parameter in the ill template
  5. The QID itself
"""

import re, time, io, sys, requests
import mwclient
from mwclient.errors import APIError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKI_URL = "shinto.miraheze.org"
WIKI_PATH = "/w/"
USERNAME = "Immanuelle"
PASSWORD = "[REDACTED_SECRET_2]"
WD_API = "https://www.wikidata.org/w/api.php"
THROTTLE = 1.5

site = mwclient.Site(WIKI_URL, path=WIKI_PATH,
                     clients_useragent='IllFixerBot/1.0 (User:Immanuelle; shinto.miraheze.org)')
site.login(USERNAME, PASSWORD)
print(f"Logged in as {USERNAME}", flush=True)

# ── QID resolution cache ──────────────────────────────────
_qid_cache = {}


def resolve_qid(qid):
    """Resolve QID to a page name.
    Priority: wiki redirect > enwiki > en label > None
    """
    if qid in _qid_cache:
        return _qid_cache[qid]

    # 1. Check wiki QID redirect
    try:
        qid_page = site.pages[qid]
        if qid_page.exists:
            text = qid_page.text()
            m = re.match(r'#REDIRECT\s*\[\[([^\]]+)\]\]', text, re.IGNORECASE)
            if m:
                target = m.group(1)
                _qid_cache[qid] = target
                return target
    except Exception:
        pass

    # 2. Query Wikidata for enwiki sitelink / en label
    try:
        time.sleep(0.5)
        resp = requests.get(WD_API, params={
            'action': 'wbgetentities', 'ids': qid,
            'props': 'labels|sitelinks', 'languages': 'en',
            'format': 'json'
        }, headers={'User-Agent': 'IllFixerBot/1.0'}, timeout=30)
        entity = resp.json().get('entities', {}).get(qid, {})

        # 2a. enwiki sitelink
        sitelinks = entity.get('sitelinks', {})
        if 'enwiki' in sitelinks:
            result = sitelinks['enwiki']['title']
            _qid_cache[qid] = result
            return result

        # 2b. English label
        labels = entity.get('labels', {})
        if 'en' in labels:
            result = labels['en']['value']
            _qid_cache[qid] = result
            return result
    except Exception:
        pass

    _qid_cache[qid] = None
    return None


# ── Template fixer ────────────────────────────────────────
ILL_RE = re.compile(r'\{\{ill\|([^{}]*)\}\}', re.IGNORECASE)


def fix_ill(match):
    """Fix a single {{ill|...}} match."""
    inner = match.group(1)
    params = inner.split('|')

    # Find WD= parameter
    wd_qid = None
    for p in params:
        if p.strip().startswith('WD='):
            wd_qid = p.strip()[3:].strip()
            break

    if not wd_qid or not re.match(r'^Q\d+$', wd_qid):
        return match.group(0)  # No valid WD, leave unchanged

    # Resolve via priority chain
    resolved = resolve_qid(wd_qid)

    if resolved is None:
        # Fall back to last lt= in the template
        last_lt = None
        for p in params:
            if p.strip().startswith('lt='):
                last_lt = p.strip()[3:]
        if last_lt:
            resolved = last_lt
        else:
            resolved = wd_qid  # Final fallback: the QID itself

    # Set first positional parameter
    if params and '=' not in params[0]:
        # First param is already positional — replace it
        if params[0].strip() == resolved:
            return match.group(0)  # Already correct, skip
        params[0] = resolved
    else:
        # First param is named (e.g. lt=...), insert destination at front
        params.insert(0, resolved)

    return '{{ill|' + '|'.join(params) + '}}'


# ── Main loop ─────────────────────────────────────────────
def main():
    print("=" * 70, flush=True)
    print("FIX ILL TEMPLATE DESTINATIONS", flush=True)
    print("=" * 70, flush=True)

    total = 0
    edited = 0
    skipped = 0

    for page in site.allpages(namespace=0):
        total += 1
        if total % 500 == 0:
            print(f"  ... scanned {total} pages, edited {edited}, "
                  f"cache size {len(_qid_cache)}", flush=True)

        try:
            text = page.text()
        except Exception as e:
            if "429" in str(e):
                print(f"  Rate limited at page {total}, waiting 60s...", flush=True)
                time.sleep(60)
                try:
                    text = page.text()
                except Exception:
                    continue
            else:
                continue

        if '{{ill|' not in text.lower():
            continue

        new_text = ILL_RE.sub(fix_ill, text)

        if new_text == text:
            skipped += 1
            continue

        try:
            page.save(new_text, summary="Bot: fix ill template destination links")
            edited += 1
            print(f"[{total}] Edited [[{page.name}]]", flush=True)
        except APIError as e:
            print(f"[{total}] ! APIError [[{page.name}]]: {e.code}", flush=True)
        except Exception as e:
            if "429" in str(e):
                print(f"  Rate limited, waiting 60s...", flush=True)
                time.sleep(60)
                try:
                    page.save(new_text, summary="Bot: fix ill template destination links")
                    edited += 1
                    print(f"[{total}] Edited [[{page.name}]] (retry)", flush=True)
                except Exception as e2:
                    print(f"[{total}] ! Still failing [[{page.name}]]: {e2}", flush=True)
            else:
                print(f"[{total}] ! Error [[{page.name}]]: {e}", flush=True)

        time.sleep(THROTTLE)

    print("\n" + "=" * 70, flush=True)
    print(f"DONE — {total} pages scanned, {edited} edited, {skipped} skipped (no change)", flush=True)
    print(f"QID cache size: {len(_qid_cache)}", flush=True)
    print("=" * 70, flush=True)


if __name__ == '__main__':
    main()
