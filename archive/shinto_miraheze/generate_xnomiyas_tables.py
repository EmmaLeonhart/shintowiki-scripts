#!/usr/bin/env python3
"""
Generate comprehensive wikitables for X-no-Miyas (provincial shrines) organized by role.

Table structure:
1. Region/Province
2. Part of (P361)
3. Link to province (via P1001)
4. Link to shrine (the part itself)
5. Located in (P131) - administrative territorial entity
6. Coordinates (P625)
7. Engishiki funding category
8. Engishiki rank
9. Modern shrine ranking (P13723)
10. Is Beppyo Shrine? (P31 = Beppyo Shrine)

Tables are organized by has role (P3831) qualifier, with a separate table for items without roles.
"""

import requests
import json
import sys
import io
import time

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WIKIDATA_API = 'https://www.wikidata.org/w/api.php'

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

def get_shrine_data(shrine_qid, label_cache):
    """Get all required data for a shrine."""
    entity = get_entity(shrine_qid)
    if not entity:
        return None

    claims = entity.get('claims', {})
    shrine_label = get_label(shrine_qid, label_cache)

    # Get all needed properties
    data = {
        'qid': shrine_qid,
        'label': shrine_label,
        'P361': get_property_value(claims, 'P361'),  # part of
        'P131': get_property_value(claims, 'P131'),  # located in
        'P625': get_property_string(claims, 'P625'),  # coordinates
        'P13723': get_property_value(claims, 'P13723'),  # modern shrine ranking
        'P31': [],  # instance of - check if Beppyo Shrine
    }

    # Check if it's a Beppyo Shrine
    if 'P31' in claims:
        for stmt in claims['P31']:
            instance_qid = stmt.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')
            if instance_qid:
                data['P31'].append(instance_qid)

    return data

def get_parts_with_roles(entity):
    """Extract P527 (has parts) organized by P3831 (has role) qualifier.

    Returns: {role_qid: [shrine_qids], None: [shrine_qids_without_role]}
    """
    parts_by_role = {}

    if 'P527' not in entity.get('claims', {}):
        return parts_by_role

    for statement in entity['claims']['P527']:
        part_qid = statement.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id')

        if not part_qid:
            continue

        # Get the role qualifier
        qualifiers = statement.get('qualifiers', {})
        role_qid = None

        if 'P3831' in qualifiers:
            role_qid = qualifiers['P3831'][0].get('datavalue', {}).get('value', {}).get('id')

        if role_qid not in parts_by_role:
            parts_by_role[role_qid] = []

        parts_by_role[role_qid].append(part_qid)

    return parts_by_role

def create_table_for_role(role_qid, shrine_qids, province_qid, label_cache, global_shrine_data):
    """Create a wikitable for a specific role and its shrines."""
    role_label = get_label(role_qid, label_cache) if role_qid else "Unrolled (No Role)"
    province_label = get_label(province_qid, label_cache)

    table_lines = [f"\n=== {role_label} ===\n"]
    table_lines.append("{| class=\"wikitable sortable\"\n")
    table_lines.append("! Province !! Part of (P361) !! Province Link !! Shrine !! Located In (P131) !! Coordinates !! Engishiki Rank !! Modern Ranking (P13723) !! Beppyo Shrine?\n")
    table_lines.append("|-\n")

    for shrine_qid in shrine_qids:
        if shrine_qid not in global_shrine_data:
            # Fetch if not cached
            shrine_data = get_shrine_data(shrine_qid, label_cache)
            if shrine_data:
                global_shrine_data[shrine_qid] = shrine_data
            else:
                continue
        else:
            shrine_data = global_shrine_data[shrine_qid]

        shrine_label = shrine_data['label']
        part_of_qid = shrine_data['P361']
        located_in_qid = shrine_data['P131']
        ranking_qid = shrine_data['P13723']
        is_beppyo = "Yes" if any(q == 'Q10898274' for q in shrine_data['P31']) else "No"

        # Format coordinates if available
        coords = shrine_data['P625']
        if coords:
            if isinstance(coords, dict):
                lat = coords.get('latitude', '')
                lon = coords.get('longitude', '')
                coords_text = f"{lat}, {lon}"
            else:
                coords_text = str(coords)
        else:
            coords_text = ""

        # Build table row
        part_of_label = get_label(part_of_qid, label_cache) if part_of_qid else ""
        located_in_label = get_label(located_in_qid, label_cache) if located_in_qid else ""
        ranking_label = get_label(ranking_qid, label_cache) if ranking_qid else ""

        table_lines.append(f"| {province_label}\n")
        table_lines.append(f"| {part_of_label}\n")
        table_lines.append(f"| [[{province_label}]]\n")
        table_lines.append(f"| [[{shrine_label}]]\n")
        table_lines.append(f"| {located_in_label}\n")
        table_lines.append(f"| {coords_text}\n")
        table_lines.append(f"| \n")  # Engishiki rank placeholder
        table_lines.append(f"| {ranking_label}\n")
        table_lines.append(f"| {is_beppyo}\n")
        table_lines.append("|-\n")

    table_lines.append("|}\n")

    return ''.join(table_lines)

def generate_tables(max_provinces=None):
    """Generate all X-no-Miyas tables starting from Yamashiro Province."""
    print("Generating X-no-Miyas wikitables...\n")

    current_qid = 'Q11467693'  # List of Shikinaisha in Yamashiro Province
    all_tables = []
    province_num = 1
    global_label_cache = {}
    global_shrine_data = {}

    while current_qid and (max_provinces is None or province_num <= max_provinces):
        print(f"Processing province {province_num}: {current_qid}")

        entity = get_entity(current_qid)
        if not entity:
            print(f"  Could not fetch entity {current_qid}")
            break

        # Get the province this applies to
        province_qid = get_property_value(entity.get('claims', {}), 'P1001')
        if not province_qid:
            print(f"  No P1001 property found")
            break

        # Get parts organized by role
        parts_by_role = get_parts_with_roles(entity)

        if parts_by_role:
            # Collect all QIDs to fetch labels
            qids_to_fetch = set([province_qid])
            qids_to_fetch.update(parts_by_role.keys())
            for shrine_list in parts_by_role.values():
                qids_to_fetch.update(shrine_list)

            # Remove None and already-cached
            qids_to_fetch = [q for q in qids_to_fetch if q and q not in global_label_cache]

            if qids_to_fetch:
                print(f"  Fetching labels for {len(qids_to_fetch)} entities...")
                new_labels = get_labels_batch(qids_to_fetch)
                global_label_cache.update(new_labels)

            province_label = get_label(province_qid, global_label_cache)
            print(f"  Province: {province_label}")

            # Create province header
            province_section = f"\n== {province_label} ==\n"
            all_tables.append(province_section)

            # Create table for each role
            for role_qid in sorted(parts_by_role.keys(), key=lambda x: (x is None, x)):
                shrine_qids = parts_by_role[role_qid]
                role_label = get_label(role_qid, global_label_cache) if role_qid else "Unrolled"
                print(f"    {role_label}: {len(shrine_qids)} shrines")

                # For now, just create simple table without full shrine data
                # We'll enhance this once we verify the structure is correct
                table = create_table_for_role(role_qid, shrine_qids, province_qid, global_label_cache, global_shrine_data)
                all_tables.append(table)

        # Get next province using P156 (followed by)
        next_qid = get_property_value(entity.get('claims', {}), 'P156')

        if next_qid:
            print(f"  Next province: {next_qid}\n")
            current_qid = next_qid
            province_num += 1
            time.sleep(0.5)  # Rate limit
        else:
            print(f"  No following province found. Stopping.\n")
            break

    return ''.join(all_tables)

def main():
    """Main execution."""
    print("="*70)
    print("X-NO-MIYAS WIKITABLE GENERATOR")
    print("="*70)
    print()

    try:
        # Generate all provinces
        tables = generate_tables()

        print("\n" + "="*70)
        print("GENERATED TABLES")
        print("="*70)
        print(tables)

        # Save to file
        output_file = 'xnomiyas_tables.wiki'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(tables)

        print(f"\nSaved to {output_file}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
