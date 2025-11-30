#!/usr/bin/env python3
"""
Deprecate properties incorrectly applied to Shikinai Ronsha (Engishiki shrines) on Wikidata.
Specifically targets Mita Hachiman Shrine (Q545397).

This script:
1. Checks for P460 (said to be the same as) property
2. Validates that there's a single QID linked (after removing duplicates with/without qualifiers)
3. Adds P3831 (object of statement has role) with value Disputed Shikinaisha/Shikigeisha
4. Deprecates specific properties with qualifiers indicating they refer to the Engishiki shrine
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

# Target shrine
TARGET_SHRINE_QID = "Q545397"  # Mita Hachiman Shrine

# QID values for properties to deprecate
ENGISHIKI_SHRINE_TYPES = [
    "Q134917286",  # Shikinaisha
    "Q135160342",  # Kokuhei-sha (Engishiki Jinmyocho)
    "Q135160338",  # Kanpei-sha (Engishiki Jinmyocho)
    "Q135009152",  # Shrines receiving Hoe and Quiver
    "Q135009205",  # Shrines receiving hoe offering
    "Q135009221",  # Shrines receiving Quiver offering
    "Q135009132",  # Shrine receiving Tsukinami-sai and Niiname-sai offerings
    "Q135009157",  # Shrine receiving Tsukinami-sai and Niiname-sai and Ainame-sai offerings
    "Q134917287",  # Shikinai Shosha
    "Q134917288",  # Shikinai Taisha
    "Q9610964",    # Myōjin Taisha
    "Q135018062",  # Engishiki seat
]

ENGISHIKI_JINMYOCHO_QID = "Q11064932"
HEIAN_PERIOD_QID = "Q193292"
DISPUTED_SHIKINAISHA_QID = "Q135038714"  # Disputed Shikinaisha or Shikigeisha

REASON_REFERS_DIFFERENT = "Q28091153"  # refers to different subject
ROLE_QUALIFIER = "P3831"  # object of statement has role

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

def check_p460_property(entity):
    """
    Check P460 (said to be the same as) property.

    Returns:
        QID if valid single target found, None otherwise
    """
    claims = entity.get('claims', {})
    p460_claims = claims.get('P460', [])

    if not p460_claims:
        print("  No P460 (said to be the same as) property found. Aborting.")
        return None

    print(f"  Found {len(p460_claims)} P460 statement(s)")

    # Extract QID targets
    p460_targets = []
    for claim in p460_claims:
        if claim['mainsnak']['snaktype'] == 'value':
            target_qid = claim['mainsnak']['datavalue']['value']['id']
            has_qualifier = bool(claim.get('qualifiers'))
            p460_targets.append({
                'qid': target_qid,
                'has_qualifier': has_qualifier,
                'claim': claim
            })

    if not p460_targets:
        print("  No valid P460 values. Aborting.")
        return None

    # Check for duplicates with same QID but different qualifier status
    qid_groups = {}
    for target in p460_targets:
        qid = target['qid']
        if qid not in qid_groups:
            qid_groups[qid] = []
        qid_groups[qid].append(target)

    # Check if we have multiple different QIDs
    unique_qids = list(qid_groups.keys())
    if len(unique_qids) > 1:
        print(f"  Multiple different QIDs linked via P460: {unique_qids}")
        print("  Aborting - too many targets.")
        return None

    # We have exactly one QID - check for duplicate with/without qualifiers
    single_qid = unique_qids[0]
    qid_targets = qid_groups[single_qid]

    if len(qid_targets) > 1:
        # Check if one has qualifier and one doesn't
        with_qual = [t for t in qid_targets if t['has_qualifier']]
        without_qual = [t for t in qid_targets if not t['has_qualifier']]

        if len(with_qual) == 1 and len(without_qual) == 1:
            print(f"  Found duplicate P460 for {single_qid}: one with qualifier, one without")
            print(f"  Removing statement without qualifier")
            # Remove the one without qualifier
            remove_claim(entity['id'], without_qual[0]['claim'])
        else:
            print(f"  Multiple P460 statements for {single_qid} with unexpected qualifier pattern")
            print(f"  Aborting - cannot safely resolve.")
            return None

    print(f"  Single valid P460 target: {single_qid}")
    return single_qid

def remove_claim(entity_id, claim):
    """Remove a claim from an entity"""
    csrf_token = get_csrf_token()
    claim_id = claim['id']

    r = session.post(WIKIDATA_API, data={
        'action': 'wbremoveclaims',
        'claims': claim_id,
        'token': csrf_token,
        'summary': 'Removing duplicate P460 statement without qualifier',
        'format': 'json'
    })

    if r.json().get('success') == 1:
        print(f"    Removed claim {claim_id}")
        time.sleep(1)
    else:
        print(f"    Error removing claim: {r.json()}")

def add_role_qualifier(entity_id, p460_qid):
    """Add P3831 (role) qualifier to P460 statement with the disputed role"""
    entity = get_entity(entity_id)
    claims = entity.get('claims', {})
    p460_claims = claims.get('P460', [])

    csrf_token = get_csrf_token()

    # Find the P460 claim linking to p460_qid
    for claim in p460_claims:
        if claim['mainsnak']['snaktype'] == 'value':
            target_qid = claim['mainsnak']['datavalue']['value']['id']
            if target_qid == p460_qid:
                claim_id = claim['id']

                # Add the role qualifier
                r = session.post(WIKIDATA_API, data={
                    'action': 'wbsetqualifier',
                    'claim': claim_id,
                    'property': ROLE_QUALIFIER,
                    'snaktype': 'value',
                    'value': json.dumps({'entity-type': 'item', 'numeric-id': int(DISPUTED_SHIKINAISHA_QID[1:])}),
                    'token': csrf_token,
                    'summary': f'Adding role qualifier: Disputed Shikinaisha/Shikigeisha',
                    'format': 'json'
                })

                if r.json().get('success') == 1:
                    print(f"  Added P3831 qualifier to P460 statement")
                    time.sleep(1)
                else:
                    print(f"  Error adding qualifier: {r.json()}")
                return

    print(f"  Could not find P460 statement linking to {p460_qid}")

def deprecate_property_statements(entity_id, p460_qid):
    """
    Deprecate statements of specified properties.
    Add qualifiers indicating they refer to the Engishiki shrine via P460.
    """
    entity = get_entity(entity_id)
    claims = entity.get('claims', {})
    csrf_token = get_csrf_token()

    deprecated_count = 0

    # Properties to check and their target QIDs
    properties_to_deprecate = {
        'P31': ENGISHIKI_SHRINE_TYPES,  # instance of
        'P361': None,  # part of - special handling (must be part of Engishiki Jinmyocho)
        'P1448': None,  # official name - special handling (must have Heian period qualifier)
        'P13677': None,  # Kokugakuin University Digital Museum entry ID
    }

    for prop, target_qids in properties_to_deprecate.items():
        prop_claims = claims.get(prop, [])

        if not prop_claims:
            print(f"  No {prop} statements found")
            continue

        print(f"  Found {len(prop_claims)} {prop} statement(s)")

        for claim in prop_claims:
            should_deprecate = False

            if prop == 'P31':
                # Check if value is in ENGISHIKI_SHRINE_TYPES
                if claim['mainsnak']['snaktype'] == 'value':
                    target_qid = claim['mainsnak']['datavalue']['value']['id']
                    if target_qid in ENGISHIKI_SHRINE_TYPES:
                        should_deprecate = True

            elif prop == 'P361':
                # Check if this is part of something that is part of Engishiki Jinmyocho
                if claim['mainsnak']['snaktype'] == 'value':
                    target_qid = claim['mainsnak']['datavalue']['value']['id']
                    # Check if target is part of Engishiki Jinmyocho
                    target_entity = get_entity(target_qid)
                    target_claims = target_entity.get('claims', {})

                    for p361_claim in target_claims.get('P361', []):
                        if p361_claim['mainsnak']['snaktype'] == 'value':
                            p361_target = p361_claim['mainsnak']['datavalue']['value']['id']
                            if p361_target == ENGISHIKI_JINMYOCHO_QID:
                                should_deprecate = True
                                break

                    time.sleep(0.5)  # Rate limiting

            elif prop == 'P1448':
                # Check if has valid in period qualifier with Heian period
                qualifiers = claim.get('qualifiers', {})
                if 'P1264' in qualifiers:
                    for qual in qualifiers['P1264']:
                        if qual['snaktype'] == 'value':
                            qual_qid = qual['datavalue']['value']['id']
                            if qual_qid == HEIAN_PERIOD_QID:
                                should_deprecate = True
                                break

            elif prop == 'P13677':
                # Always deprecate Kokugakuin entries
                should_deprecate = True

            if should_deprecate:
                deprecate_claim(entity_id, claim, p460_qid, csrf_token)
                deprecated_count += 1
                time.sleep(1)

    print(f"  Deprecated {deprecated_count} statements")

def deprecate_claim(entity_id, claim, p460_qid, csrf_token):
    """Deprecate a claim and add qualifiers"""
    claim_id = claim['id']

    # Set rank to deprecated using wbsetclaim with the proper structure
    claim_copy = claim.copy()
    claim_copy['rank'] = 'deprecated'

    r = session.post(WIKIDATA_API, data={
        'action': 'wbsetclaim',
        'claim': json.dumps(claim_copy),
        'token': csrf_token,
        'summary': 'Deprecating statement - refers to Engishiki shrine properties',
        'format': 'json'
    })

    if 'error' in r.json():
        # Try alternative: fetch fresh entity and update via wbeditentity
        entity = get_entity(entity_id)
        claims = entity.get('claims', {})

        # Find the property this claim belongs to
        for prop, prop_claims in claims.items():
            for idx, c in enumerate(prop_claims):
                if c['id'] == claim_id:
                    # Found it - set rank and update
                    claims[prop][idx]['rank'] = 'deprecated'

                    edit_data = {'claims': claims[prop]}
                    r2 = session.post(WIKIDATA_API, data={
                        'action': 'wbeditentity',
                        'id': entity_id,
                        'data': json.dumps(edit_data),
                        'token': csrf_token,
                        'summary': 'Deprecating statement - refers to Engishiki shrine properties',
                        'format': 'json'
                    })

                    if 'error' in r2.json():
                        print(f"    Error setting rank: {r2.json()['error']}")
                        return
                    break

    # Add reason for deprecated rank qualifier
    r = session.post(WIKIDATA_API, data={
        'action': 'wbsetqualifier',
        'claim': claim_id,
        'property': 'P2241',
        'snaktype': 'value',
        'value': json.dumps({'entity-type': 'item', 'numeric-id': int(REASON_REFERS_DIFFERENT[1:])}),
        'token': csrf_token,
        'summary': 'Adding reason for deprecation',
        'format': 'json'
    })

    if r.json().get('success') != 1:
        print(f"    Error adding P2241 qualifier: {r.json()}")
        return

    # Add intended subject qualifier
    r = session.post(WIKIDATA_API, data={
        'action': 'wbsetqualifier',
        'claim': claim_id,
        'property': 'P8327',
        'snaktype': 'value',
        'value': json.dumps({'entity-type': 'item', 'numeric-id': int(p460_qid[1:])}),
        'token': csrf_token,
        'summary': 'Adding intended subject of deprecated statement',
        'format': 'json'
    })

    if r.json().get('success') != 1:
        print(f"    Error adding P8327 qualifier: {r.json()}")
        return

    print(f"    Deprecated {claim_id} with qualifiers")

def main():
    """Main script execution"""
    print(f"Starting deprecation script for {TARGET_SHRINE_QID}")
    print("=" * 60)

    # Login
    login()

    # Get the target shrine
    print(f"\nFetching {TARGET_SHRINE_QID}...")
    entity = get_entity(TARGET_SHRINE_QID)
    shrine_label = entity.get('labels', {}).get('en', {}).get('value', TARGET_SHRINE_QID)
    print(f"Working with: {shrine_label}")

    # Check P460 property
    print(f"\nChecking P460 (said to be the same as) property...")
    p460_qid = check_p460_property(entity)

    if not p460_qid:
        print("\nAborted: No valid P460 property found")
        return

    # Add role qualifier to P460
    print(f"\nAdding role qualifier to P460 statement...")
    add_role_qualifier(TARGET_SHRINE_QID, p460_qid)

    # Deprecate properties
    print(f"\nDeprecating related properties...")
    deprecate_property_statements(TARGET_SHRINE_QID, p460_qid)

    print("\n" + "=" * 60)
    print("Script completed successfully")

if __name__ == '__main__':
    main()
