"""Revert all pages in Category:Weird possibly ai botched translations
to their state as of February 12, 2026."""

import requests
import sys
import time

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# CONFIG
API_URL   = 'https://shinto.miraheze.org/w/api.php'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'
CATEGORY  = 'Weird possibly ai botched translations'
CUTOFF    = '2026-02-13T00:00:00Z'  # Revisions before this = on or before Feb 12
HEADERS   = {'User-Agent': 'WikiBot/1.0 (shinto.miraheze.org; Immanuelle)'}

session = requests.Session()
session.headers.update(HEADERS)


def api_get(**params):
    params['format'] = 'json'
    r = session.get(API_URL, params=params)
    r.raise_for_status()
    return r.json()


def api_post(**params):
    params['format'] = 'json'
    r = session.post(API_URL, data=params)
    r.raise_for_status()
    return r.json()


def login():
    # Step 1: get login token
    data = api_get(action='query', meta='tokens', type='login')
    login_token = data['query']['tokens']['logintoken']

    # Step 2: login
    data = api_post(action='login', lgname=USERNAME, lgpassword=PASSWORD,
                    lgtoken=login_token)
    result = data.get('login', {}).get('result')
    if result != 'Success':
        raise RuntimeError(f"Login failed: {data}")
    print(f"Logged in as {data['login']['lgusername']}")


def get_csrf_token():
    data = api_get(action='query', meta='tokens')
    return data['query']['tokens']['csrftoken']


def get_category_members(category):
    """Get all mainspace pages in a category."""
    pages = []
    cmcontinue = None
    while True:
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': f'Category:{category}',
            'cmlimit': 500,
            'cmnamespace': 0,
            'cmtype': 'page',
        }
        if cmcontinue:
            params['cmcontinue'] = cmcontinue
        data = api_get(**params)
        for m in data.get('query', {}).get('categorymembers', []):
            pages.append(m['title'])
        if 'continue' in data:
            cmcontinue = data['continue']['cmcontinue']
        else:
            break
    return pages


def get_feb12_revision(title):
    """Get the content of the last revision on or before Feb 12, 2026."""
    data = api_get(
        action='query',
        prop='revisions',
        titles=title,
        rvprop='ids|timestamp|content',
        rvlimit=1,
        rvstart=CUTOFF,
        rvdir='older',
        rvslots='main',
    )
    pages = data.get('query', {}).get('pages', {})
    for pid, pdata in pages.items():
        revisions = pdata.get('revisions', [])
        if revisions:
            rev = revisions[0]
            # MW 1.45 uses slots format
            content = rev.get('slots', {}).get('main', {}).get('*', '')
            if not content:
                # Fallback to old format
                content = rev.get('*', '')
            return {
                'revid': rev['revid'],
                'timestamp': rev['timestamp'],
                'content': content,
            }
    return None


def get_current_content(title):
    """Get the current page content."""
    data = api_get(
        action='query',
        prop='revisions',
        titles=title,
        rvprop='content',
        rvslots='main',
    )
    pages = data.get('query', {}).get('pages', {})
    for pid, pdata in pages.items():
        revisions = pdata.get('revisions', [])
        if revisions:
            rev = revisions[0]
            content = rev.get('slots', {}).get('main', {}).get('*', '')
            if not content:
                content = rev.get('*', '')
            return content
    return None


def edit_page(title, text, summary, csrf_token):
    """Edit a page."""
    data = api_post(
        action='edit',
        title=title,
        text=text,
        summary=summary,
        token=csrf_token,
    )
    if data.get('edit', {}).get('result') == 'Success':
        return True
    else:
        print(f"  Edit response: {data}")
        return False


def main():
    login()
    csrf_token = get_csrf_token()

    pages = get_category_members(CATEGORY)
    print(f"Found {len(pages)} pages in [[Category:{CATEGORY}]]")

    reverted = 0
    skipped = 0
    errors = 0

    for i, title in enumerate(pages, 1):
        print(f"\n[{i}/{len(pages)}] {title}")

        try:
            current = get_current_content(title)
        except Exception as e:
            print(f"  ERROR reading current: {e}")
            errors += 1
            continue

        rev = get_feb12_revision(title)
        if rev is None:
            print(f"  SKIP - no revision on or before Feb 12")
            skipped += 1
            continue

        print(f"  Target: rev {rev['revid']} ({rev['timestamp']})")

        if current is not None and current.rstrip() == rev['content'].rstrip():
            print(f"  SKIP - already matches Feb 12 state")
            skipped += 1
            continue

        try:
            success = edit_page(
                title,
                rev['content'],
                f"Reverting to revision {rev['revid']} (Feb 12 state) - undoing bad translations",
                csrf_token,
            )
            if success:
                print(f"  REVERTED")
                reverted += 1
            else:
                errors += 1
        except Exception as e:
            print(f"  ERROR saving: {e}")
            errors += 1

        time.sleep(1.5)

    print(f"\n{'='*50}")
    print(f"Done! Reverted: {reverted}, Skipped: {skipped}, Errors: {errors}")


if __name__ == '__main__':
    main()
