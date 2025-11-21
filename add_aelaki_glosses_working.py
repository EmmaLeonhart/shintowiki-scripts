#!/usr/bin/env python3
"""
add_aelaki_glosses_working.py
=============================
Add English glosses to L1-L60 by copying L61's PROVEN structure.

Key insight from testing:
- L61 modifications work perfectly
- New lexeme creation drops senses
- Adding senses to empty lexemes fails with "nochange"
- SOLUTION: Use L61 as template, modify only essential fields

Strategy:
1. Get the full L61 structure (which works)
2. For each L1-L60: fetch it, copy L61 structure, modify lemma/sense
3. This avoids the "new sense creation" bug by using existing sense structure
"""

import requests
import json
import time
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = 'https://aelaki.miraheze.org/w/api.php'
USERNAME = 'Immanuelle'
PASSWORD = '[REDACTED_SECRET_2]'

english_glosses = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
    11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
    16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
    21: "twenty-one", 22: "twenty-two", 23: "twenty-three", 24: "twenty-four", 25: "twenty-five",
    26: "twenty-six", 27: "twenty-seven", 28: "twenty-eight", 29: "twenty-nine", 30: "thirty",
    31: "thirty-one", 32: "thirty-two", 33: "thirty-three", 34: "thirty-four", 35: "thirty-five",
    36: "thirty-six", 37: "thirty-seven", 38: "thirty-eight", 39: "thirty-nine", 40: "forty",
    41: "forty-one", 42: "forty-two", 43: "forty-three", 44: "forty-four", 45: "forty-five",
    46: "forty-six", 47: "forty-seven", 48: "forty-eight", 49: "forty-nine", 50: "fifty",
    51: "fifty-one", 52: "fifty-two", 53: "fifty-three", 54: "fifty-four", 55: "fifty-five",
    56: "fifty-six", 57: "fifty-seven", 58: "fifty-eight", 59: "fifty-nine", 60: "sixty"
}

# The cardinal names for L1-L60 (assuming same as L3-L60 creation)
cardinal_names = {
    1: "Pan", 2: "Bal", 3: "Bhan", 4: "Ven", 5: "Syn",
    6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
    # Add more if needed, or they may already exist
}

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# ─────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────

print("Logging in...")
r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'})
login_token = r.json()['query']['tokens']['logintoken']

r = session.post(API_URL, data={'action': 'login', 'lgname': USERNAME, 'lgpassword': PASSWORD, 'lgtoken': login_token, 'format': 'json'})
if r.json().get('login', {}).get('result') != 'Success':
    print("Login failed!")
    sys.exit(1)
print("✓ Logged in\n")

r = session.get(API_URL, params={'action': 'query', 'meta': 'tokens', 'type': 'csrf', 'format': 'json'})
csrf_token = r.json()['query']['tokens']['csrftoken']

# ─────────────────────────────────────────────────────────────────────────
# FETCH L61 TEMPLATE
# ─────────────────────────────────────────────────────────────────────────

print("Fetching L61 template...")
try:
    r = session.get(API_URL, params={
        'action': 'query',
        'titles': 'Lexeme:L61',
        'prop': 'revisions',
        'rvprop': 'content',
        'format': 'json'
    })
    pages = r.json()['query']['pages']
    page_id = list(pages.keys())[0]
    l61_content = pages[page_id]['revisions'][0]['*']
    l61_template = json.loads(l61_content)
    print("✓ L61 template loaded")
    print(f"  Template structure: {json.dumps(l61_template, indent=2)}\n")
except Exception as e:
    print(f"✗ Failed to fetch L61: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────
# ADD GLOSSES TO L1-L60
# ─────────────────────────────────────────────────────────────────────────

print("Adding glosses to L1-L60 using L61 template...\n")

count = 0
failed = []

for num in range(1, 61):
    gloss = english_glosses[num]
    lexeme_id = f"L{num}"

    print(f"Processing {lexeme_id}: {gloss}...", end=" ", flush=True)

    try:
        # Fetch current lexeme
        r = session.get(API_URL, params={
            'action': 'query',
            'titles': f'Lexeme:{lexeme_id}',
            'prop': 'revisions',
            'rvprop': 'content',
            'format': 'json'
        })
        pages = r.json()['query']['pages']
        page_id = list(pages.keys())[0]

        if 'revisions' not in pages[page_id]:
            print("✗ (lexeme not found)")
            failed.append(lexeme_id)
            continue

        current_content = pages[page_id]['revisions'][0]['*']
        current_lexeme = json.loads(current_content)

        # Build new data using L61 as template but with current lexeme's lemma
        edit_data = {
            'type': 'lexeme',
            'lemmas': current_lexeme.get('lemmas', {}),  # Keep existing lemma
            'language': current_lexeme.get('language', 'Q1'),
            'lexicalCategory': current_lexeme.get('lexicalCategory', 'Q4'),
            'claims': current_lexeme.get('claims', []),
            'nextFormId': current_lexeme.get('nextFormId', 1),
            'nextSenseId': 2,  # From L61 template
            'forms': current_lexeme.get('forms', []),
            'senses': [
                {
                    'id': f'{lexeme_id}-S1',
                    'glosses': {
                        'en': {
                            'language': 'en',
                            'value': gloss
                        }
                    },
                    'claims': []
                }
            ]
        }

        # Send to API (NOT as wbeditentity - we'll use direct merge)
        r = session.post(API_URL, data={
            'action': 'wbeditentity',
            'id': lexeme_id,
            'data': json.dumps(edit_data),
            'token': csrf_token,
            'format': 'json'
        })
        result = r.json()

        if 'error' in result:
            print(f"✗ ({result['error']['info']})")
            failed.append(lexeme_id)
        elif 'success' in result and result['success']:
            entity = result.get('entity', {})

            # Verify persistence with fetch
            time.sleep(0.5)
            r = session.get(API_URL, params={
                'action': 'query',
                'titles': f'Lexeme:{lexeme_id}',
                'prop': 'revisions',
                'rvprop': 'content',
                'format': 'json'
            })
            pages = r.json()['query']['pages']
            page_id = list(pages.keys())[0]
            saved_content = pages[page_id]['revisions'][0]['*']
            saved_lexeme = json.loads(saved_content)

            saved_senses = saved_lexeme.get('senses', [])
            if saved_senses:
                saved_gloss = saved_senses[0].get('glosses', {}).get('en', {}).get('value', '')
                if saved_gloss == gloss:
                    print("✓")
                    count += 1
                else:
                    print(f"✗ (gloss mismatch: {saved_gloss})")
                    failed.append(lexeme_id)
            else:
                print("✗ (senses not saved)")
                failed.append(lexeme_id)
        else:
            print("✗ (no success indicator)")
            failed.append(lexeme_id)

        time.sleep(1.5)

    except Exception as e:
        print(f"✗ ({e})")
        failed.append(lexeme_id)

print(f"\n✓✓✓ Successfully added glosses to {count} lexemes")
if failed:
    print(f"✗✗✗ Failed: {', '.join(failed)}")
