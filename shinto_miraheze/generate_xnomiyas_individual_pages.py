#!/usr/bin/env python3
"""
Generate individual X-no-Miyas tables for each province, posting directly to shinto wiki.

This version creates and overwrites separate pages for each province:
[[User:Immanuelle/X-no-Miyas/Province Name]]

This allows real-time observation of progress as pages are created.
"""

import requests
import json
import sys
import io
import time
import mwclient

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'

# Wiki credentials
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

def get_entity(qid):
    """Fetch entity from Wikidata."""
    params = {
        'action': 'wbgetentities',
        'ids': qid,
        'format': 'json'
    }
    headers = {
        'User-Agent': 'Immanuelle/XNoMiyasTableGenerator (https://shinto.miraheze.org; immanuelleproject@gmail.com)'
    }
    try:
        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data['entities'].get(qid)
    except Exception as e:
        print(f"  Error fetching {qid}: {e}")
        return None

def get_labels_batch(qids):
    """Fetch multiple entities at once for efficiency."""
    if not qids:
        return {}

    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'format': 'json'
    }
    headers = {
        'User-Agent': 'Immanuelle/XNoMiyasTableGenerator (https://shinto.miraheze.org; immanuelleproject@gmail.com)'
    }
    try:
        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        labels = {}
        for qid, entity in data.get('entities', {}).items():
            if 'labels' in entity:
                label_dict = entity['labels']
                if 'en' in label_dict:
                    labels[qid] = label_dict['en']['value']
                else:
                    first_lang = next(iter(label_dict.values()), None)
                    if first_lang:
                        labels[qid] = first_lang['value']
                    else:
                        labels[qid] = qid
            else:
                labels[qid] = qid
        return labels
    except Exception as e:
        print(f"  Error fetching labels: {e}")
        return {qid: qid for qid in qids}

def get_label(qid, label_cache):
    """Get label from cache."""
    return label_cache.get(qid, qid)

def get_property_value(claims, prop):
    """Extract first value from claims."""
    if prop not in claims or not claims[prop]:
        return None
    return claims[prop][0].get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')

def get_property_string(claims, prop):
    """Extract first string value from claims."""
    if prop not in claims or not claims[prop]:
        return None
    return claims[prop][0].get('mainsnak', {}).get('datavalue', {}).get('value')

def get_parts_with_roles(entity):
    """Extract P527 (has parts) organized by P3831 (has role) qualifier."""
    parts_by_role = {}

    if 'P527' not in entity.get('claims', {}):
        return parts_by_role

    for statement in entity['claims']['P527']:
        part_qid = statement.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')

        if not part_qid:
            continue

        qualifiers = statement.get('qualifiers', {})
        role_qid = None

        if 'P3831' in qualifiers:
            role_qid = qualifiers['P3831'][0].get('datavalue', {}).get('value', {}).get('id')

        if role_qid not in parts_by_role:
            parts_by_role[role_qid] = []

        parts_by_role[role_qid].append(part_qid)

    return parts_by_role

def create_table_for_role(role_qid, shrine_qids, province_qid, province_label, label_cache):
    """Create a wikitable for a specific role and its shrines."""
    role_label = get_label(role_qid, label_cache) if role_qid else "Unrolled (No Role)"

    table_lines = [f"=== {role_label} ===\n"]
    table_lines.append("{| class=\"wikitable sortable\"\n")
    table_lines.append("! Part of (P361) !! Shrine !! Located In (P131) !! Coordinates !! Modern Ranking (P13723) !! Beppyo Shrine?\n")
    table_lines.append("|-\n")

    for shrine_qid in shrine_qids:
        shrine_entity = get_entity(shrine_qid)
        if not shrine_entity:
            continue

        shrine_label = get_label(shrine_qid, label_cache)
        claims = shrine_entity.get('claims', {})

        part_of_qid = get_property_value(claims, 'P361')
        located_in_qid = get_property_value(claims, 'P131')
        ranking_qid = get_property_value(claims, 'P13723')

        # Check if Beppyo Shrine
        is_beppyo = "Yes" if any(stmt.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') == 'Q10898274'
                                 for stmt in claims.get('P31', [])) else "No"

        coords = get_property_string(claims, 'P625')
        if coords:
            if isinstance(coords, dict):
                lat = coords.get('latitude', '')
                lon = coords.get('longitude', '')
                coords_text = f"{lat}, {lon}"
            else:
                coords_text = str(coords)
        else:
            coords_text = ""

        part_of_label = get_label(part_of_qid, label_cache) if part_of_qid else ""
        located_in_label = get_label(located_in_qid, label_cache) if located_in_qid else ""
        ranking_label = get_label(ranking_qid, label_cache) if ranking_qid else ""

        table_lines.append(f"| {part_of_label}\n")
        table_lines.append(f"| [[{shrine_label}]]\n")
        table_lines.append(f"| {located_in_label}\n")
        table_lines.append(f"| {coords_text}\n")
        table_lines.append(f"| {ranking_label}\n")
        table_lines.append(f"| {is_beppyo}\n")
        table_lines.append("|-\n")

    table_lines.append("|}\n")

    return ''.join(table_lines)

def generate_and_post_province_page(province_qid, province_list_qid, label_cache, site):
    """Generate and post a single province page."""
    entity = get_entity(province_list_qid)
    if not entity:
        return False

    # Get the province label
    province_label = get_label(province_qid, label_cache)
    print(f"  Generating page for {province_label}...")

    # Get parts organized by role
    parts_by_role = get_parts_with_roles(entity)

    if not parts_by_role:
        print(f"  No shrine data found")
        return False

    # Collect all QIDs to fetch labels
    qids_to_fetch = set()
    for role_list in parts_by_role.values():
        qids_to_fetch.update(role_list)

    # Remove already-cached
    qids_to_fetch = [q for q in qids_to_fetch if q not in label_cache]

    if qids_to_fetch:
        print(f"    Fetching {len(qids_to_fetch)} shrine labels...")
        new_labels = get_labels_batch(qids_to_fetch)
        label_cache.update(new_labels)

    # Build page content
    page_content = f"== {province_label} ==\n\n"

    # Create table for each role
    for role_qid in sorted(parts_by_role.keys(), key=lambda x: (x is None, x)):
        shrine_qids = parts_by_role[role_qid]
        table = create_table_for_role(role_qid, shrine_qids, province_qid, province_label, label_cache)
        page_content += table + "\n"

    # Post to wiki
    page_title = f"User:Immanuelle/X-no-Miyas/{province_label}"
    try:
        page = site.pages[page_title]
        page.edit(page_content, summary=f"Generate X-no-Miyas table for {province_label}")
        print(f"  [OK] Posted to {page_title}")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to post to {page_title}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main execution."""
    print("="*70)
    print("X-NO-MIYAS INDIVIDUAL PAGE GENERATOR")
    print("="*70)
    print()

    try:
        # Login to wiki
        print(f"Connecting to {WIKI_URL}...")
        site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
        site.login(USERNAME, PASSWORD)

        # Retrieve username
        try:
            ui = site.api('query', meta='userinfo')
            logged_user = ui['query']['userinfo'].get('name', USERNAME)
            print(f"Logged in as {logged_user}\n")
        except Exception:
            print("Logged in (could not fetch username via API, but login succeeded).\n")

        # Start with Yamashiro Province
        current_qid = 'Q11467693'
        current_province_qid = 'Q749276'
        province_num = 1
        global_label_cache = {}

        while current_qid and province_num <= 68:
            print(f"Province {province_num}: {current_qid}")

            entity = get_entity(current_qid)
            if not entity:
                print(f"  Could not fetch entity {current_qid}")
                break

            # Fetch province label
            qids_to_fetch = [current_province_qid]
            new_labels = get_labels_batch(qids_to_fetch)
            global_label_cache.update(new_labels)

            # Generate and post page
            success = generate_and_post_province_page(current_province_qid, current_qid, global_label_cache, site)

            if not success:
                print(f"  Warning: Failed to generate page for province {province_num}")

            # Get next province
            next_qid = get_property_value(entity.get('claims', {}), 'P156')
            next_province_qid = get_property_value(entity.get('claims', {}), 'P1001')

            if next_qid and next_province_qid:
                print(f"  Next: {next_qid}\n")
                current_qid = next_qid
                current_province_qid = next_province_qid
                province_num += 1
                time.sleep(1.5)  # Rate limit for wiki
            else:
                print(f"  No following province found. Stopping.\n")
                break

        print("="*70)
        print(f"Generated {province_num - 1} province pages")
        print("="*70)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
