#!/usr/bin/env python3
"""
Remove unqualified P460 (said to be the same as) statements from a shrine.
Used to clean up duplicates where one P460 has a qualifier and one doesn't.
"""

import requests
import json
import sys
import io
import time

# Handle Unicode on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuration
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USERNAME = "Immanuelle@ImmanuelleCommonsBot"
PASSWORD = "r7db82prl8ftds5fo9v5uaiunce5n2cp"

TARGET_SHRINE_QID = "Q106301088"  # Kamo Shrine

session = requests.Session()
session.headers.update({'User-Agent': 'ImmanuelleCommonsBot/1.0'})

def login():
    """Login to Wikidata"""
    print("Logging in to Wikidata...")

    # Get login token
    r = session.get(WIKIDATA_API, params={
        'action': 'query',
        'meta': 'tokens',
        'type': 'login',
        'format': 'json'
    })
    login_token = r.json()['query']['tokens']['logintoken']

    # Perform login using legacy method
    r = session.post(WIKIDATA_API, data={
        'action': 'login',
        'lgname': USERNAME,
        'lgpassword': PASSWORD,
        'lgtoken': login_token,
        'format': 'json'
    })

    result = r.json().get('login', {})
    if result.get('result') != 'Success':
        print(f"Login failed: {r.json()}")
        sys.exit(1)

    print("Successfully logged in")

def get_csrf_token():
    """Get CSRF token for editing"""
    r = session.get(WIKIDATA_API, params={
        'action': 'query',
        'meta': 'tokens',
        'type': 'csrf',
        'format': 'json'
    })
    return r.json()['query']['tokens']['csrftoken']

def get_entity(qid):
    """Fetch an entity from Wikidata"""
    r = session.get(WIKIDATA_API, params={
        'action': 'wbgetentities',
        'ids': qid,
        'format': 'json'
    })
    return r.json()['entities'][qid]

def main():
    """Main script execution"""
    print(f"Removing unqualified P460 statements from {TARGET_SHRINE_QID}")
    print("=" * 60)

    login()

    # Get the target shrine
    print(f"\nFetching {TARGET_SHRINE_QID}...")
    entity = get_entity(TARGET_SHRINE_QID)
    shrine_label = entity.get('labels', {}).get('en', {}).get('value', TARGET_SHRINE_QID)
    print(f"Working with: {shrine_label}\n")

    # Check P460 statements
    claims = entity.get('claims', {})
    p460_claims = claims.get('P460', [])

    if not p460_claims:
        print("No P460 statements found. Nothing to do.")
        return

    print(f"Found {len(p460_claims)} P460 statement(s):\n")

    # Group by target QID
    qid_groups = {}
    for claim in p460_claims:
        if claim['mainsnak']['snaktype'] == 'value':
            target_qid = claim['mainsnak']['datavalue']['value']['id']
            has_qualifier = bool(claim.get('qualifiers'))
            if target_qid not in qid_groups:
                qid_groups[target_qid] = []
            qid_groups[target_qid].append({
                'claim_id': claim['id'],
                'has_qualifier': has_qualifier,
                'claim': claim
            })

    # Process each group
    csrf_token = get_csrf_token()
    removed_count = 0

    for target_qid, statements in qid_groups.items():
        if len(statements) > 1:
            # Multiple statements for same target
            with_qual = [s for s in statements if s['has_qualifier']]
            without_qual = [s for s in statements if not s['has_qualifier']]

            print(f"Target {target_qid}:")
            print(f"  Statements with qualifiers: {len(with_qual)}")
            print(f"  Statements without qualifiers: {len(without_qual)}")

            if len(without_qual) > 0:
                for stmt in without_qual:
                    claim_id = stmt['claim_id']
                    print(f"  Removing unqualified statement: {claim_id}")

                    r = session.post(WIKIDATA_API, data={
                        'action': 'wbremoveclaims',
                        'claim': claim_id,
                        'token': csrf_token,
                        'summary': 'Removing duplicate P460 statement without qualifier',
                        'format': 'json'
                    })

                    response = r.json()
                    if response.get('success') == 1 or 'claims' in response:
                        print(f"    ✓ Successfully removed")
                        removed_count += 1
                        time.sleep(1)
                    else:
                        print(f"    ✗ Error: {response.get('error', {}).get('info', 'Unknown error')}")
            print()
        else:
            stmt = statements[0]
            print(f"Target {target_qid}: 1 statement (no duplicates)")
            if stmt['has_qualifier']:
                print(f"  Has qualifier - keeping as is")
            else:
                print(f"  No qualifier - would remove if there was a duplicate")
            print()

    print("=" * 60)
    print(f"Removed {removed_count} unqualified P460 statement(s)")

if __name__ == '__main__':
    main()
