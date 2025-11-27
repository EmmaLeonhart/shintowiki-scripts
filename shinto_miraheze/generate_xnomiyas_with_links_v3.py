#!/usr/bin/env python3
"""
Generate X-no-Miyas tables with proper interlanguage linking using {{ill|}} template.
VERSION 3: Fixed multiple regions/locations, Engishiki properties, proper linking

This version creates individual pages for each province with full linking:
[[User:Immanuelle/X-no-Miyas/Province Name]]

Table columns:
1. Region (province's P361 - MULTIPLE comma-separated)
2. Province
3. Shrine
4. Location (shrine's P131 - MULTIPLE comma-separated)
5. Engishiki Funding Category (Check P31 for Kokuhei/Kanpei)
6. Engishiki Ranking (from Shikinaisha list)
7. Modern Ranking (shrine's P13723 - LINKED)
8. Beppyo Shrine status
9. Coordinates (shrine's P625)

Links use the {{ill|}} template with simplewiki priority, then enwiki, then en label.
"""

import requests
import json
import sys
import io
import time
import mwclient
import re

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'

# Wiki credentials
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

# QIDs for Engishiki categories
KOKUHEI_SHRINE_QID = 'Q10903609'  # Kokuhei-sha (national shrine)
KANPEI_SHRINE_QID = 'Q10903608'   # Kanpei-sha (government-sanctioned shrine)

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
        print(f"    Error fetching {qid}: {e}")
        return None

def get_labels_batch(qids):
    """Fetch multiple entities at once for efficiency."""
    if not qids:
        return {}

    params = {
        'action': 'wbgetentities',
        'ids': '|'.join(qids),
        'format': 'json',
        'props': 'labels|sitelinks|claims'
    }
    headers = {
        'User-Agent': 'Immanuelle/XNoMiyasTableGenerator (https://shinto.miraheze.org; immanuelleproject@gmail.com)'
    }
    try:
        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get('entities', {})
    except Exception as e:
        print(f"    Error fetching labels: {e}")
        return {}

def get_label(qid, all_entities):
    """Get label from entity cache."""
    if qid in all_entities and 'labels' in all_entities[qid]:
        labels = all_entities[qid]['labels']
        if 'en' in labels:
            return labels['en']['value']
        # Try first available language
        first_lang = next(iter(labels.values()), None)
        if first_lang:
            return first_lang['value']
    return qid

def create_ill_link(qid, entity_data):
    """Create {{ill|}} template link for a QID.

    Priority: simplewiki title > enwiki title > en label
    Includes all language versions except simplewiki and commons.
    """
    if not entity_data:
        return qid

    sitelinks = entity_data.get('sitelinks', {})
    labels = entity_data.get('labels', {})

    # Get the target title (simplewiki > enwiki > en label)
    target = None
    if 'simplewiki' in sitelinks:
        target = sitelinks['simplewiki']['title']
    elif 'enwiki' in sitelinks:
        target = sitelinks['enwiki']['title']
    else:
        if 'en' in labels:
            target = labels['en']['value']
        else:
            # Try first available label
            first_label = next(iter(labels.values()), None)
            if first_label:
                target = first_label['value']

    if not target:
        return qid

    # Build language links (exclude simplewiki and commons)
    lang_links = []
    for site, link_data in sorted(sitelinks.items()):
        # Skip simplewiki (we're on it) and commons (not a language)
        if site in ('simplewiki', 'commonswiki'):
            continue

        # Extract language code from site (e.g., 'enwiki' -> 'en')
        if site.endswith('wiki'):
            lang_code = site[:-4]
            lang_links.append(f"{lang_code}|{link_data['title']}")

    # Build the ill template
    if lang_links:
        ill = f"{{{{ill|{target}|{('|').join(lang_links)}|lt={target}|WD={qid}}}}}"
    else:
        ill = f"{{{{ill|{target}|lt={target}|WD={qid}}}}}"

    return ill

def get_property_value(claims, prop):
    """Extract first value from claims."""
    if prop not in claims or not claims[prop]:
        return None
    return claims[prop][0].get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')

def get_property_values(claims, prop):
    """Extract ALL values from claims (for multi-valued properties)."""
    values = []
    if prop not in claims or not claims[prop]:
        return values
    for claim in claims[prop]:
        value = claim.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
        if value:
            values.append(value)
    return values

def get_property_string(claims, prop):
    """Extract first string value from claims."""
    if prop not in claims or not claims[prop]:
        return None
    return claims[prop][0].get('mainsnak', {}).get('datavalue', {}).get('value')

def format_coordinates(coords_data):
    """Format coordinates for {{coord|}} template."""
    if not coords_data:
        return ""

    if isinstance(coords_data, dict):
        lat = coords_data.get('latitude', '')
        lon = coords_data.get('longitude', '')
    else:
        return ""

    return f"{{{{coord|{lat}|{lon}|display=inline}}}}"

def get_engishiki_funding(claims):
    """Get Engishiki funding category by checking P31 (instance of) for Kokuhei or Kanpei."""
    if 'P31' not in claims:
        return None

    instance_qids = get_property_values(claims, 'P31')
    for qid in instance_qids:
        if qid == KOKUHEI_SHRINE_QID:
            return "Kokuhei"
        elif qid == KANPEI_SHRINE_QID:
            return "Kanpei"
    return None

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

def create_table_for_role(role_qid, shrine_qids, province_qid, all_entities):
    """Create a wikitable for a specific role and its shrines."""
    role_label = get_label(role_qid, all_entities) if role_qid else "Unrolled (No Role)"
    role_link = create_ill_link(role_qid, all_entities.get(role_qid)) if role_qid else "Unrolled"

    # Get the province's regions (P361 - can be multiple)
    province_entity = all_entities.get(province_qid)
    province_region_qids = get_property_values(province_entity.get('claims', {}), 'P361') if province_entity else []
    province_region_links = [create_ill_link(qid, all_entities.get(qid)) for qid in province_region_qids if qid]
    province_region_text = ", ".join(province_region_links) if province_region_links else ""

    # Get province link
    province_link = create_ill_link(province_qid, province_entity) if province_entity else ""

    table_lines = [f"=== {role_label} ===\n"]
    table_lines.append("{| class=\"wikitable sortable\"\n")
    table_lines.append("! Region !! Province !! Shrine !! Location (P131) !! Engishiki Funding !! Engishiki Rank !! Modern Ranking (P13723) !! Beppyo Shrine? !! Coordinates\n")
    table_lines.append("|-\n")

    for shrine_qid in shrine_qids:
        shrine_entity = all_entities.get(shrine_qid)
        if not shrine_entity:
            continue

        shrine_link = create_ill_link(shrine_qid, shrine_entity)
        claims = shrine_entity.get('claims', {})

        # Get all locations (P131 - can be multiple)
        located_in_qids = get_property_values(claims, 'P131')
        located_in_links = [create_ill_link(qid, all_entities.get(qid)) for qid in located_in_qids if qid]
        located_in_text = ", ".join(located_in_links) if located_in_links else ""

        # Get ranking
        ranking_qid = get_property_value(claims, 'P13723')
        ranking_link = create_ill_link(ranking_qid, all_entities.get(ranking_qid)) if ranking_qid else ""

        # Check if Beppyo Shrine
        is_beppyo = "Yes" if any(stmt.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') == 'Q10898274'
                                 for stmt in claims.get('P31', [])) else "No"

        # Get Engishiki funding
        engishiki_funding = get_engishiki_funding(claims) or ""

        # Get coordinates
        coords = get_property_string(claims, 'P625')
        coords_text = format_coordinates(coords)

        table_lines.append(f"| {province_region_text}\n")
        table_lines.append(f"| {province_link}\n")
        table_lines.append(f"| {shrine_link}\n")
        table_lines.append(f"| {located_in_text}\n")
        table_lines.append(f"| {engishiki_funding}\n")
        table_lines.append(f"| \n")  # Engishiki rank placeholder (from Shikinaisha list)
        table_lines.append(f"| {ranking_link}\n")
        table_lines.append(f"| {is_beppyo}\n")
        table_lines.append(f"| {coords_text}\n")
        table_lines.append("|-\n")

    table_lines.append("|}\n")

    return ''.join(table_lines)

def generate_and_post_province_page(province_qid, province_list_qid, all_entities, site):
    """Generate and post a single province page."""
    # Get the PROVINCE entity (not the list)
    province_entity = all_entities.get(province_qid)
    if not province_entity:
        return False

    # Get the province label and link
    province_label = get_label(province_qid, all_entities)

    print(f"  Generating page for {province_label}...")

    # Get parts organized by role FROM THE PROVINCE ENTITY
    parts_by_role = get_parts_with_roles(province_entity)

    if not parts_by_role:
        print(f"  No shrine data found")
        return False

    # Build page content
    page_content = f"== {province_label} ==\n\n"

    # Create table for each role
    for role_qid in sorted(parts_by_role.keys(), key=lambda x: (x is None, x)):
        shrine_qids = parts_by_role[role_qid]
        table = create_table_for_role(role_qid, shrine_qids, province_qid, all_entities)
        page_content += table + "\n"

    # Add category
    page_content += "\n[[Category:generated x-no-miya lists]]\n"

    # Post to wiki
    page_title = f"User:Immanuelle/X-no-Miyas/{province_label}"
    try:
        page = site.pages[page_title]
        page.edit(page_content, summary=f"Generate X-no-Miyas table for {province_label}")
        print(f"  [OK] Posted to {page_title}")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to post to {page_title}: {e}")
        return False

def main():
    """Main execution."""
    print("="*70)
    print("X-NO-MIYAS INDIVIDUAL PAGE GENERATOR V3")
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
        province_num = 1
        all_entities = {}

        while current_qid and province_num <= 68:
            print(f"Province {province_num}: {current_qid}")

            # Fetch the LIST entity
            list_entity = get_entity(current_qid)
            if not list_entity:
                print(f"  Could not fetch list entity {current_qid}")
                break

            all_entities[current_qid] = list_entity

            # Get the province QID from the list via P1001
            current_province_qid = get_property_value(list_entity.get('claims', {}), 'P1001')
            if not current_province_qid:
                print(f"  Could not find P1001 (applies to jurisdiction) on list")
                break

            # Fetch the PROVINCE entity
            province_entity = get_entity(current_province_qid)
            if not province_entity:
                print(f"  Could not fetch province entity {current_province_qid}")
                break

            all_entities[current_province_qid] = province_entity

            # Get parts organized by role FROM THE PROVINCE
            parts_by_role = get_parts_with_roles(province_entity)

            if parts_by_role:
                # Collect all shrine QIDs and other referenced entities
                shrine_qids_to_fetch = set()
                role_qids_to_fetch = set()
                related_qids_to_fetch = set()

                for role_qid, shrine_list in parts_by_role.items():
                    if role_qid:
                        role_qids_to_fetch.add(role_qid)
                    shrine_qids_to_fetch.update(shrine_list)

                # Also fetch province's regions and location references
                province_region_qids = get_property_values(province_entity.get('claims', {}), 'P361')
                related_qids_to_fetch.update(qid for qid in province_region_qids if qid)

                # Fetch shrine entities first to get their P131 and P13723 references
                print(f"  Pre-fetching {len(shrine_qids_to_fetch)} shrines for property extraction...")
                for i in range(0, len(shrine_qids_to_fetch), 50):
                    batch = list(shrine_qids_to_fetch)[i:i+50]
                    batch_entities = get_labels_batch(batch)
                    all_entities.update(batch_entities)

                    # Extract referenced location and ranking QIDs
                    for shrine_qid, shrine_entity in batch_entities.items():
                        location_qids = get_property_values(shrine_entity.get('claims', {}), 'P131')
                        related_qids_to_fetch.update(qid for qid in location_qids if qid)
                        ranking_qid = get_property_value(shrine_entity.get('claims', {}), 'P13723')
                        if ranking_qid:
                            related_qids_to_fetch.add(ranking_qid)

                # Now fetch the roles and related entities (locations, rankings) that we extracted
                print(f"  Fetching {len(role_qids_to_fetch)} roles and {len(related_qids_to_fetch)} related entities...")
                other_qids = list(role_qids_to_fetch) + list(related_qids_to_fetch)

                # Batch fetch in groups of 50 (API limit)
                for i in range(0, len(other_qids), 50):
                    batch = other_qids[i:i+50]
                    batch_entities = get_labels_batch(batch)
                    all_entities.update(batch_entities)

                # Generate and post page
                success = generate_and_post_province_page(current_province_qid, current_qid, all_entities, site)

                if not success:
                    print(f"  Warning: Failed to generate page for province {province_num}")

            # Get next list via P156 (followed by)
            next_qid = get_property_value(list_entity.get('claims', {}), 'P156')

            if next_qid:
                print(f"  Next: {next_qid}\n")
                current_qid = next_qid
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
