#!/usr/bin/env python3
"""
Generate X-no-Miyas master table with ALL provinces.

Generates both:
1. Individual province pages with all shrines (for debugging/detail view)
2. Master compiled table at [[User:Immanuelle/X-no-Miyas]] (one row per province)

Master table columns:
Region | Province | Ichinomiya | Modern Ranking | Engishiki Rank | Beppyo Status | Coordinates
"""

import requests
import json
import sys
import io
import time
import mwclient
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'

# Wiki credentials
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

# Engishiki Designation QIDs
KANPEI_QID = "Q135160338"      # Kanpei-sha
KOKUHEI_QID = "Q135160342"     # Kokuhei-sha

# Engishiki Rank QIDs
RANK_SHOSHA_QID = "Q134917287" # Shosha
RANK_TAISHA_QID = "Q134917288" # Taisha
RANK_OTHER_QID = "Q9610964"    # (other rank)

# Celebration/Offering QIDs (for Engishiki funding category)
CELEB_MAP = {
    "Q135009132": "Q135009132",  # Tsukinami-/Niiname-sai
    "Q135009152": "Q135009152",  # Hoe & Quiver
    "Q135009157": "Q135009157",  # Tsukinami-/Niiname-/Ainame-sai
    "Q135009205": "Q135009205",  # Hoe offering
    "Q135009221": "Q135009221",  # Quiver offering
}

CELEB_LABELS = {
    "Q135009132": ("Tsukinami", "{{efn|gets offerings for the yearly {{ill|Niiname-no-Matsuri|en|Niiname-no-Matsuri|ja|新嘗祭|WD=Q11501518}} and the monthly {{ill|Tsukinami-no-Matsuri|simple|Tsukinami-no-Matsuri|ja|月次祭|WD=Q11516161}}.}}"),
    "Q135009152": ("Hoe and Quiver", ""),
    "Q135009157": ("Ainame", "{{efn|gets offerings for the {{ill|Ainame Festival|ja|相嘗祭|zh|相嘗祭|WD=Q11581944}} and the lower ranked {{ill|Tsukinami-no-Matsuri|simple|Tsukinami-no-Matsuri|ja|月次祭|WD=Q11516161}} and {{ill|Niiname-no-Matsuri|en|Niiname-no-Matsuri|ja|新嘗祭|WD=Q11501518}}.}}"),
    "Q135009205": ("Hoe", ""),
    "Q135009221": ("Quiver", ""),
}

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
        first_lang = next(iter(labels.values()), None)
        if first_lang:
            return first_lang['value']
    return qid

def create_ill_link(qid, entity_data):
    """Create {{ill|}} template link for a QID."""
    if not entity_data or not qid:
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
            first_label = next(iter(labels.values()), None)
            if first_label:
                target = first_label['value']

    if not target:
        return qid

    # Build language links (exclude simplewiki and commons)
    lang_links = []
    for site, link_data in sorted(sitelinks.items()):
        if site in ('simplewiki', 'commonswiki'):
            continue
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
    """Extract ALL values from claims."""
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

def get_celebration_link(celeb_qid, all_entities):
    """Get celebration/festival QID as ill link with custom lt= parameters and inline footnote."""
    if not celeb_qid or celeb_qid not in CELEB_MAP:
        return ""

    celeb_ent = all_entities.get(celeb_qid)
    if not celeb_ent:
        return ""

    celeb_name = get_label(celeb_qid, all_entities)
    lt_param, footnote = CELEB_LABELS.get(celeb_qid, ("", ""))

    if lt_param:
        link = f"{{{{ill|{celeb_name}|WD={celeb_qid}|lt={lt_param}}}}}"
    else:
        link = f"{{{{ill|{celeb_name}|WD={celeb_qid}}}}}"

    # Append footnote inline if it exists
    if footnote:
        link += footnote

    return link

def get_engishiki_funding(claims, all_entities):
    """Get Engishiki funding category from P31 (Kanpei/Kokuhei with celebration in brackets)."""
    # Get the designation (Kanpei or Kokuhei) with proper lt= label
    desig = ""
    for p31_claim in claims.get('P31', []):
        p31_qid = p31_claim.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
        if p31_qid == KANPEI_QID:
            kanpei_entity = all_entities.get(KANPEI_QID)
            if kanpei_entity:
                kanpei_name = get_label(KANPEI_QID, all_entities)
                desig = f"{{{{ill|{kanpei_name}|WD={KANPEI_QID}|lt=Kanpei}}}}"
                break
        elif p31_qid == KOKUHEI_QID:
            kokuhei_entity = all_entities.get(KOKUHEI_QID)
            if kokuhei_entity:
                kokuhei_name = get_label(KOKUHEI_QID, all_entities)
                desig = f"{{{{ill|{kokuhei_name}|WD={KOKUHEI_QID}|lt=Kokuhei}}}}"
                break

    # Get the celebration/offering
    celeb_link = ""
    for p31_claim in claims.get('P31', []):
        p31_qid = p31_claim.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
        if p31_qid in CELEB_MAP:
            celeb_link = get_celebration_link(p31_qid, all_entities)
            if celeb_link:
                break

    # Combine: "Kanpei (Tsukinami...)" or just "Tsukinami..." if no designation
    if desig and celeb_link:
        return f"{desig} ({celeb_link})"
    elif celeb_link:
        return celeb_link
    elif desig:
        return desig
    else:
        return ""

def create_province_link(qid, entity_data, all_entities):
    """Create province link with lt= parameter for just the province name."""
    if not entity_data:
        return qid

    province_label = get_label(qid, all_entities)
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
            first_label = next(iter(labels.values()), None)
            if first_label:
                target = first_label['value']

    if not target:
        return qid

    # Build language links (exclude simplewiki and commons)
    lang_links = []
    for site, link_data in sorted(sitelinks.items()):
        if site in ('simplewiki', 'commonswiki'):
            continue
        if site.endswith('wiki'):
            lang_code = site[:-4]
            lang_links.append(f"{lang_code}|{link_data['title']}")

    # Build the ill template with lt= for just the province name
    if lang_links:
        ill = f"{{{{ill|{target}|{('|').join(lang_links)}|lt={province_label}|WD={qid}}}}}"
    else:
        ill = f"{{{{ill|{target}|lt={province_label}|WD={qid}}}}}"

    return ill

def get_engishiki_rank(claims, all_entities):
    """Get Engishiki rank (Shosha, Taisha, or other) from P31."""
    for p31_claim in claims.get('P31', []):
        p31_qid = p31_claim.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
        if p31_qid == RANK_SHOSHA_QID:
            rank_entity = all_entities.get(RANK_SHOSHA_QID)
            return create_ill_link(RANK_SHOSHA_QID, rank_entity) if rank_entity else "Shosha"
        elif p31_qid == RANK_TAISHA_QID:
            rank_entity = all_entities.get(RANK_TAISHA_QID)
            return create_ill_link(RANK_TAISHA_QID, rank_entity) if rank_entity else "Taisha"
        elif p31_qid == RANK_OTHER_QID:
            rank_entity = all_entities.get(RANK_OTHER_QID)
            return create_ill_link(RANK_OTHER_QID, rank_entity) if rank_entity else "Other"
    return ""

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

    # Get the province's region (what province is part of)
    province_entity = all_entities.get(province_qid)
    province_region_qids = get_property_values(province_entity.get('claims', {}), 'P361') if province_entity else []
    province_region_text = ", ".join([create_ill_link(qid, all_entities.get(qid)) for qid in province_region_qids if qid])

    # Get province link
    province_link = create_ill_link(province_qid, province_entity) if province_entity else ""

    table_lines = [f"=== {role_label} ===\n"]
    table_lines.append('{| class="wikitable sortable"\n')
    table_lines.append('! Region !! Province !! Shrine !! Location !! Engishiki Funding !! Engishiki Rank !! Modern Ranking !! Beppyo Shrine? !! Coordinates\n')
    table_lines.append('|-\n')

    for shrine_qid in shrine_qids:
        shrine_entity = all_entities.get(shrine_qid)
        if not shrine_entity:
            continue

        shrine_link = create_ill_link(shrine_qid, shrine_entity)
        claims = shrine_entity.get('claims', {})

        located_in_qids = get_property_values(claims, 'P131')
        ranking_qid = get_property_value(claims, 'P13723')

        # Check if Beppyo Shrine
        is_beppyo = "Yes" if any(stmt.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') == 'Q10898274' for stmt in claims.get('P31', [])) else "No"

        coords = get_property_string(claims, 'P625')
        coords_text = format_coordinates(coords)

        located_in_text = ", ".join([create_ill_link(qid, all_entities.get(qid)) for qid in located_in_qids if qid])
        ranking_link = create_ill_link(ranking_qid, all_entities.get(ranking_qid)) if ranking_qid else ""

        engishiki_funding = get_engishiki_funding(claims, all_entities)
        engishiki_rank = get_engishiki_rank(claims, all_entities)

        table_lines.append(f"| {province_region_text}\n")
        table_lines.append(f"| {province_link}\n")
        table_lines.append(f"| {shrine_link}\n")
        table_lines.append(f"| {located_in_text}\n")
        table_lines.append(f"| {engishiki_funding}\n")
        table_lines.append(f"| {engishiki_rank}\n")
        table_lines.append(f"| {ranking_link}\n")
        table_lines.append(f"| {is_beppyo}\n")
        table_lines.append(f"| {coords_text}\n")
        table_lines.append('|-\n')

    table_lines.append('|}\n')

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

    # Add category and timestamp
    page_content += "\n[[Category:generated x-no-miya lists]]\n"
    utc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    page_content += f"\n<!-- Generated: {utc_time} -->\n"

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
    print("X-NO-MIYAS MASTER TABLE GENERATOR (WITH PROVINCE PAGES)")
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
        table_rows_by_role = {}  # Organize shrines by role

        # First pass: collect all data and generate province pages
        while current_qid and province_num <= 68:
            print(f"Processing province {province_num}: {current_qid}")

            # Fetch the LIST entity
            list_entity = get_entity(current_qid)
            if not list_entity:
                print(f"  Could not fetch list entity {current_qid}")
                break

            all_entities[current_qid] = list_entity

            # Get the province QID from the list via P1001
            current_province_qid = get_property_value(list_entity.get('claims', {}), 'P1001')
            if not current_province_qid:
                print(f"  Could not find P1001 on list")
                break

            # Fetch the PROVINCE entity
            province_entity = get_entity(current_province_qid)
            if not province_entity:
                print(f"  Could not fetch province entity {current_province_qid}")
                break

            all_entities[current_province_qid] = province_entity
            province_label = get_label(current_province_qid, all_entities)

            # Get parts organized by role
            parts_by_role = get_parts_with_roles(province_entity)

            # Collect all shrine QIDs and related entities
            shrine_qids_to_fetch = set()
            role_qids_to_fetch = set()
            related_qids_to_fetch = set()

            for role_qid, shrine_list in parts_by_role.items():
                if role_qid:
                    role_qids_to_fetch.add(role_qid)
                shrine_qids_to_fetch.update(shrine_list)

            # Get province's regions
            province_region_qids = get_property_values(province_entity.get('claims', {}), 'P361')
            related_qids_to_fetch.update(qid for qid in province_region_qids if qid)

            # Always fetch Engishiki QIDs
            related_qids_to_fetch.add(KANPEI_QID)
            related_qids_to_fetch.add(KOKUHEI_QID)
            related_qids_to_fetch.add(RANK_SHOSHA_QID)
            related_qids_to_fetch.add(RANK_TAISHA_QID)
            related_qids_to_fetch.add(RANK_OTHER_QID)
            related_qids_to_fetch.update(CELEB_MAP.keys())

            # Pre-fetch shrine entities
            print(f"  Pre-fetching {len(shrine_qids_to_fetch)} shrines...")
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

            # Fetch roles and related entities
            print(f"  Fetching {len(role_qids_to_fetch)} roles and {len(related_qids_to_fetch)} related entities...")
            other_qids = list(role_qids_to_fetch) + list(related_qids_to_fetch)

            for i in range(0, len(other_qids), 50):
                batch = other_qids[i:i+50]
                batch_entities = get_labels_batch(batch)
                all_entities.update(batch_entities)

            # Get province region
            province_region_qids = get_property_values(province_entity.get('claims', {}), 'P361')
            province_region_text = ", ".join([create_ill_link(qid, all_entities.get(qid)) for qid in province_region_qids if qid])
            province_link = create_province_link(current_province_qid, province_entity, all_entities)

            # Collect all shrines organized by role
            for role_qid, shrine_qids in parts_by_role.items():
                if role_qid not in table_rows_by_role:
                    table_rows_by_role[role_qid] = []

                for shrine_qid in shrine_qids:
                    shrine_entity = all_entities.get(shrine_qid)
                    if not shrine_entity:
                        continue

                    shrine_link = create_ill_link(shrine_qid, shrine_entity)
                    claims = shrine_entity.get('claims', {})

                    ranking_qid = get_property_value(claims, 'P13723')
                    ranking_link = create_ill_link(ranking_qid, all_entities.get(ranking_qid)) if ranking_qid else ""
                    beppyo = "Yes" if any(stmt.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') == 'Q10898274' for stmt in claims.get('P31', [])) else "No"
                    coords = get_property_string(claims, 'P625')
                    coords_text = format_coordinates(coords)
                    engishiki_rank = get_engishiki_rank(claims, all_entities)
                    engishiki_funding = get_engishiki_funding(claims, all_entities)

                    table_rows_by_role[role_qid].append({
                        'province_num': province_num,
                        'region': province_region_text,
                        'province': province_link,
                        'shrine': shrine_link,
                        'funding': engishiki_funding,
                        'rank': engishiki_rank,
                        'ranking': ranking_link,
                        'beppyo': beppyo,
                        'coords': coords_text
                    })

            # Generate and post province page (for debugging/detail)
            generate_and_post_province_page(current_province_qid, current_qid, all_entities, site)

            # Get next list via P156
            next_qid = get_property_value(list_entity.get('claims', {}), 'P156')

            if next_qid:
                print(f"  Next: {next_qid}\n")
                current_qid = next_qid
                province_num += 1
                time.sleep(1.5)
            else:
                print(f"  No following province found. Stopping.\n")
                break

        # Build and post master table
        print("\nBuilding master table...")
        table_content = "== X-no-Miyas Master List ==\n\n"

        # Create tables for each role
        for role_qid in sorted(table_rows_by_role.keys(), key=lambda x: (x is None, x)):
            rows = table_rows_by_role[role_qid]
            if not rows:
                continue

            role_label = get_label(role_qid, all_entities) if role_qid else "Unrolled (No Role)"
            table_content += f"=== {role_label} ===\n"
            table_content += '{| class="wikitable sortable"\n'
            table_content += "! Region !! Province !! Shrine !! Engishiki Funding !! Engishiki Rank !! Modern Ranking !! Beppyo Shrine? !! Coordinates\n"
            table_content += "|-\n"

            for row in rows:
                table_content += f"| {row['region']}\n"
                table_content += f"| {row['province']}\n"
                table_content += f"| {row['shrine']}\n"
                table_content += f"| {row['funding']}\n"
                table_content += f"| {row['rank']}\n"
                table_content += f"| {row['ranking']}\n"
                table_content += f"| {row['beppyo']}\n"
                table_content += f"| {row['coords']}\n"
                table_content += "|-\n"

            table_content += "|}\n\n"

        table_content += "[[Category:generated x-no-miya lists]]\n"
        utc_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        table_content += f"\n<!-- Generated: {utc_time} -->\n"

        # Post to wiki
        page_title = "User:Immanuelle/X-no-Miyas"
        print(f"Posting master table to {page_title}...")
        try:
            page = site.pages[page_title]
            page.edit(table_content, summary="Generate X-no-Miyas master table with all provinces")
            print(f"[OK] Posted master table")
        except Exception as e:
            print(f"[ERROR] Failed to post master table: {e}")

        print("="*70)
        total_rows = sum(len(rows) for rows in table_rows_by_role.values())
        print(f"Generated master table with {len(table_rows_by_role)} roles and {total_rows} shrine entries")
        print("="*70)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
