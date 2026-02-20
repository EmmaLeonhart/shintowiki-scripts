#!/usr/bin/env python3
"""generate_shikinaisha_pages_v23_bulk_xml.py
================================================
Generate standardized shrine pages via XML bulk import
V23: Downloads category XML, processes locally, uploads in 200-page batches via XML import
================================================

This script:
1. Downloads XML of all members in [[Category:Wikidata generated shikinaisha pages]]
2. Parses XML to extract QIDs from {{wikidata link|QID}} templates
3. Generates full page content locally by querying Wikidata for each QID
4. Creates XML export files in 200-page batches
5. Uploads batches sequentially via MediaWiki import API (no timestamp = uses upload time)
6. Much more efficient than individual page edits due to reduced authentication overhead
"""

import mwclient
import requests
import sys
import time
import re
import xml.etree.ElementTree as ET
from datetime import datetime

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

PROPERTIES_TO_IGNORE = ['P11250']
PROPERTIES_TO_OMIT = ['P1448', 'P2671']
BATCH_SIZE = 200  # Upload in chunks of 200 pages

site = mwclient.Site(WIKI_URL, path=WIKI_PATH)
site.login(USERNAME, PASSWORD)

# Retrieve username
try:
    ui = site.api('query', meta='userinfo')
    logged_user = ui['query']['userinfo'].get('name', USERNAME)
    print(f"Logged in as {logged_user}\n")
except Exception:
    print("Logged in (could not fetch username via API, but login succeeded).\n")

# ─── HELPERS ─────────────────────────────────────────────────

def extract_wikidata_qid(page_text):
    """Extract Wikidata QID from page text."""
    match = re.search(r'{{wikidata link\|([Qq](\d+))}}', page_text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def get_wikidata_entity(qid):
    """Fetch full entity data from Wikidata."""
    try:
        url = f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, timeout=10, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if 'entities' in data and qid in data['entities']:
            return data['entities'][qid]
        return None
    except Exception as e:
        print(f"     ! Error fetching {qid}: {e}")
        return None


def get_property_value(entity, property_id):
    """Extract value from a property in entity data."""
    if not entity or 'claims' not in entity:
        return None

    claims = entity.get('claims', {})
    prop_claims = claims.get(property_id, [])

    if not prop_claims:
        return None

    claim = prop_claims[0]
    mainsnak = claim.get('mainsnak', {})
    datavalue = mainsnak.get('datavalue', {})

    return datavalue.get('value')


def get_label(entity, lang='en'):
    """Get label in specific language."""
    if not entity:
        return None
    labels = entity.get('labels', {})
    if lang in labels:
        return labels[lang].get('value')
    return None


def get_sitelinks(entity):
    """Extract interwiki links from Wikidata sitelinks - returns only titles."""
    sitelinks = {}
    if entity and 'sitelinks' in entity:
        for site_code, site_data in entity['sitelinks'].items():
            sitelinks[site_code] = site_data.get('title', '')
    return sitelinks


def get_all_property_claims(entity):
    """Get all claims organized by property ID."""
    if not entity or 'claims' not in entity:
        return {}
    return entity.get('claims', {})


def extract_province_from_p361(entity):
    """Extract province name from P361 (part of) claims."""
    p361_claims = entity.get('claims', {}).get('P361', [])

    for claim in p361_claims:
        datavalue = claim.get('mainsnak', {}).get('datavalue', {})
        if isinstance(datavalue.get('value'), dict):
            list_qid = datavalue['value'].get('id')
            if list_qid:
                list_entity = get_wikidata_entity(list_qid)
                list_label = get_label(list_entity)

                if list_label:
                    match = re.match(r'List of Shikinaisha in (.+)$', list_label)
                    if match:
                        province = match.group(1)
                        return province, list_label

    return None, None


def format_wikidata_link(entity, qid):
    """Format a wikidata link using ILL syntax with lt= and WD parameters."""
    sitelinks = get_sitelinks(entity)

    # Try to find shinto wiki page first, then English Wikipedia
    first_link = None
    if 'shintowiki' in sitelinks:
        first_link = sitelinks['shintowiki']
    elif 'enwiki' in sitelinks:
        first_link = sitelinks['enwiki']
    else:
        first_link = get_label(entity, 'en') or qid

    # Get English label for lt= parameter
    en_label = get_label(entity, 'en') or qid

    # Build the ILL link with lt= parameter
    wd_link = f"{{{{ill|{first_link}|lt={en_label}"

    # Add all language codes and links dynamically
    for lang_code in sorted(sitelinks.keys()):
        if lang_code != 'commonswiki':
            lang = lang_code.replace('wiki', '')
            title = sitelinks[lang_code]
            wd_link += f"|{lang}|{title}"

    # Add WD parameter
    wd_link += f"|WD={qid}}}}}"

    return wd_link


def get_property_heading(property_id):
    """Get heading text for a property in format: EN_LABEL (PID)"""
    try:
        url = f'https://www.wikidata.org/wiki/Special:EntityData/{property_id}.json'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, timeout=5, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if 'entities' in data and property_id in data['entities']:
                labels = data['entities'][property_id].get('labels', {})
                if 'en' in labels:
                    label = labels['en'].get('value')
                    return f"{label} ({property_id})"
    except Exception:
        pass

    property_labels = {
        'P31': 'Instance of',
        'P155': 'Follows',
        'P156': 'Followed by',
        'P361': 'Part of',
        'P1448': 'Official name',
        'P131': 'Located in',
        'P625': 'Coordinate location',
        'P571': 'Inception',
        'P580': 'Start time',
        'P582': 'End time',
        'P585': 'Point in time',
        'P856': 'Official website',
        'P18': 'Image',
        'P825': 'Dedicated to',
        'P1566': 'GeoNames ID',
    }

    label = property_labels.get(property_id, property_id)
    return f"{label} ({property_id})"


def get_source_reference_with_url(claim):
    """Extract source reference from claim references, including URLs."""
    references = claim.get('references', [])
    if not references:
        return None

    for ref in references:
        ref_snaks = ref.get('snaks', {})

        # Check for direct reference URL (P854)
        url = None
        if 'P854' in ref_snaks:
            for snak in ref_snaks['P854']:
                datavalue = snak.get('datavalue', {})
                url = datavalue.get('value')
                if url:
                    source_label = None
                    source_qid = None
                    if 'P248' in ref_snaks:
                        for source_snak in ref_snaks['P248']:
                            source_datavalue = source_snak.get('datavalue', {})
                            if isinstance(source_datavalue.get('value'), dict):
                                source_qid = source_datavalue['value'].get('id')
                                if source_qid:
                                    source_entity = get_wikidata_entity(source_qid)
                                    if source_entity:
                                        source_label = get_label(source_entity)
                                        break

                    if source_label and source_qid:
                        return f"{source_label} ({source_qid}) {url}"
                    elif source_label:
                        return f"{source_label} {url}"
                    else:
                        return url

            if url:
                break

        # Check for P248 + P2699
        if 'P248' in ref_snaks:
            source_label = None
            source_qid = None
            source_url = None

            for source_snak in ref_snaks['P248']:
                source_datavalue = source_snak.get('datavalue', {})
                if isinstance(source_datavalue.get('value'), dict):
                    source_qid = source_datavalue['value'].get('id')
                    if source_qid:
                        source_entity = get_wikidata_entity(source_qid)
                        if source_entity:
                            source_label = get_label(source_entity)
                            break

            if 'P2699' in ref_snaks:
                for url_snak in ref_snaks['P2699']:
                    datavalue = url_snak.get('datavalue', {})
                    source_url = datavalue.get('value')
                    if source_url:
                        break

            if not source_url and source_qid:
                source_entity = get_wikidata_entity(source_qid)
                if source_entity:
                    source_claims = source_entity.get('claims', {})
                    p2699_claims = source_claims.get('P2699', [])
                    if p2699_claims:
                        source_dataval = p2699_claims[0].get('mainsnak', {}).get('datavalue', {})
                        source_url = source_dataval.get('value')

            if source_url and source_label and source_qid:
                return f"{source_label} ({source_qid}) {source_url}"
            elif source_url and source_label:
                return f"{source_label} {source_url}"
            elif source_url:
                return source_url
            elif source_label:
                return source_label

    return None


def format_qualifier_value(qualifier_value):
    """Format a qualifier value for display."""
    if isinstance(qualifier_value, dict) and 'id' in qualifier_value:
        qid = qualifier_value['id']
        ref_entity = get_wikidata_entity(qid)
        return format_wikidata_link(ref_entity or {}, qid)

    if isinstance(qualifier_value, str):
        return qualifier_value

    return str(qualifier_value)


def get_qualifiers_text(claim):
    """Extract and format qualifiers from a claim as sub-bullets."""
    qualifiers = claim.get('qualifiers', {})
    qualifier_lines = []

    if not qualifiers:
        return qualifier_lines

    qualifier_labels = {
        'P580': 'Start time',
        'P582': 'End time',
        'P585': 'Point in time',
        'P407': 'Language of work',
        'P1545': 'Series ordinal',
        'P813': 'Retrieved',
        'P854': 'Reference URL',
    }

    for qualifier_id, qualifier_claims in qualifiers.items():
        for qualifier_claim in qualifier_claims:
            qualifier_datavalue = qualifier_claim.get('datavalue', {})
            qualifier_value = qualifier_datavalue.get('value')

            if qualifier_value:
                qual_label = qualifier_labels.get(qualifier_id, qualifier_id)
                formatted_qual_value = format_qualifier_value(qualifier_value)
                qualifier_lines.append(f"** {qual_label}: {formatted_qual_value}")

    return qualifier_lines


def format_claim_value(claim, entity, property_id=None):
    """Format a single claim value for display."""
    mainsnak = claim.get('mainsnak', {})
    datavalue = mainsnak.get('datavalue', {})
    value = datavalue.get('value')

    if not value:
        return None, [], None

    formatted_value = None

    if property_id == 'P13677' and isinstance(value, str):
        url = f"https://jmapps.ne.jp/kokugakuin/det.html?data_id={value}"
        formatted_value = f"[{url} Kokugakuin Digital Museum Item]"

    elif property_id == 'P625' and isinstance(value, dict):
        lat = value.get('latitude')
        lon = value.get('longitude')
        if lat and lon:
            formatted_value = f"{{{{coord|{lat}|{lon}}}}}"
        else:
            formatted_value = None

    elif isinstance(value, dict) and 'id' in value:
        qid = value['id']
        ref_entity = get_wikidata_entity(qid)
        formatted_value = format_wikidata_link(ref_entity or {}, qid)

    elif isinstance(value, str):
        formatted_value = value

    else:
        formatted_value = str(value)

    qualifiers = get_qualifiers_text(claim)
    source = get_source_reference_with_url(claim)

    return formatted_value, qualifiers, source


def format_page_content(page_name, qid, entity):
    """Generate standardized page content from Wikidata entity."""
    content_parts = []

    # Get basic info
    native_name = get_label(entity, 'ja')
    english_label = get_label(entity, 'en')

    # Extract sitelinks for interwiki handling
    sitelinks = get_sitelinks(entity)
    has_jawiki = 'jawiki' in sitelinks
    has_zhwiki = 'zhwiki' in sitelinks
    has_enwiki = 'enwiki' in sitelinks
    has_simplewiki = 'simplewiki' in sitelinks

    # Extract province from P361
    province_name, list_label = extract_province_from_p361(entity)

    # ADD EXPAND TEMPLATES AT TOP if needed
    if has_jawiki:
        jawiki_title = sitelinks['jawiki']
        content_parts.append(f"{{{{Expand Japanese|{jawiki_title}}}}}")
        content_parts.append("")
    elif has_zhwiki:
        zhwiki_title = sitelinks['zhwiki']
        content_parts.append(f"{{{{Expand Chinese|{zhwiki_title}}}}}")
        content_parts.append("")

    # ADD INFOBOX
    infobox_parts = ["{{Infobox religious building"]
    infobox_parts.append(f"| name = {page_name}")

    if native_name:
        infobox_parts.append(f"| native_name = {native_name}")

    # Image (P18)
    image = get_property_value(entity, 'P18')
    if image:
        infobox_parts.append(f"| image = {image}")

    infobox_parts.append("| mapframe = yes")
    infobox_parts.append("| mapframe-zoom = 15")
    infobox_parts.append("| mapframe-wikidata = yes")
    infobox_parts.append("| mapframe-point = none")
    infobox_parts.append("| map_type = Japan")
    infobox_parts.append(f"| map_caption = {page_name}")

    # Coordinates (P625)
    coords = get_property_value(entity, 'P625')
    if coords and isinstance(coords, dict):
        lat = coords.get('latitude')
        lon = coords.get('longitude')
        if lat and lon:
            infobox_parts.append(f"| coordinates = {{{{coord|{lat}|{lon}}}}}")

    infobox_parts.append("| map_relief = 1")
    infobox_parts.append("| religious_affiliation = [[Shinto]]")

    # Deity (P825)
    deity = get_property_value(entity, 'P825')
    if deity and isinstance(deity, dict):
        deity_qid = deity.get('id')
        if deity_qid:
            deity_entity = get_wikidata_entity(deity_qid)
            deity_link = format_wikidata_link(deity_entity or {}, deity_qid)
            infobox_parts.append(f"| deity = {deity_link}")

    # Established (P571)
    established = get_property_value(entity, 'P571')
    if established:
        infobox_parts.append(f"| established = {established}")

    # Website (P856)
    website = get_property_value(entity, 'P856')
    if website:
        infobox_parts.append(f"| website = {{{{Official website|{website}}}}}")

    infobox_parts.append("}}")

    content_parts.append("\n".join(infobox_parts))
    content_parts.append("")

    # INTRO TEXT
    if native_name:
        intro = f"{{{{nihongo|'''{english_label}'''|{native_name}}}}}"
    else:
        intro = f"'''{english_label}'''"

    intro += " is a [[shinto shrine]] in the [[Engishiki Jinmyōchō]]."

    if province_name:
        intro += f" It is located in [[{province_name}]]."

    content_parts.append(intro)
    content_parts.append("")

    # Add properties
    all_claims = get_all_property_claims(entity)
    property_order = ['P31', 'P361', 'P1448', 'P131', 'P625', 'P571', 'P580', 'P582', 'P856', 'P18', 'P825']

    # Ordered properties
    for prop_id in property_order:
        if prop_id in all_claims and prop_id not in PROPERTIES_TO_IGNORE and prop_id not in PROPERTIES_TO_OMIT:
            claims = all_claims[prop_id]
            prop_heading = get_property_heading(prop_id)
            content_parts.append(f"== {prop_heading} ==")
            content_parts.append("")

            for claim in claims:
                formatted_value, qualifiers, source = format_claim_value(claim, entity, prop_id)
                if formatted_value:
                    if source:
                        content_parts.append(f"* {formatted_value}<ref>{source}</ref>")
                    else:
                        content_parts.append(f"* {formatted_value}")

                    for qualifier in qualifiers:
                        content_parts.append(qualifier)

            content_parts.append("")

    # Remaining properties
    for prop_id in sorted(all_claims.keys()):
        if prop_id not in property_order and prop_id not in PROPERTIES_TO_IGNORE and prop_id not in PROPERTIES_TO_OMIT:
            claims = all_claims[prop_id]
            prop_heading = get_property_heading(prop_id)
            content_parts.append(f"== {prop_heading} ==")
            content_parts.append("")

            for claim in claims:
                formatted_value, qualifiers, source = format_claim_value(claim, entity, prop_id)
                if formatted_value:
                    if source:
                        content_parts.append(f"* {formatted_value}<ref>{source}</ref>")
                    else:
                        content_parts.append(f"* {formatted_value}")

                    for qualifier in qualifiers:
                        content_parts.append(qualifier)

            content_parts.append("")

    # Categories
    categories = ["[[Category:Wikidata generated shikinaisha pages]]"]

    # Interwiki categories
    if has_enwiki or has_simplewiki:
        categories.append("[[Category:Autogenerated pages with simplewiki or enwiki interwikis, possibly accidentally overwritten]]")

    if has_jawiki:
        categories.append("[[Category:Autogenerated pages with jawiki interwikis, possibly accidentally overwritten]]")

    # P31 categories
    p31_values = entity.get('claims', {}).get('P31', [])
    for claim in p31_values:
        datavalue = claim.get('mainsnak', {}).get('datavalue', {})
        if isinstance(datavalue.get('value'), dict):
            instance_qid = datavalue['value'].get('id')
            if instance_qid:
                instance_entity = get_wikidata_entity(instance_qid)
                instance_label = get_label(instance_entity)
                if instance_label:
                    categories.append(f"[[Category:{instance_label}]]")

    # Province category
    if province_name:
        categories.append(f"[[Category:Shikinaisha in {province_name}]]")

    content_parts.append("\n".join(categories))
    content_parts.append("")

    # Interwiki links
    interwiki_parts = []

    if 'commonswiki' in sitelinks:
        commons_page = sitelinks['commonswiki']
        interwiki_parts.append(f"{{{{commons category|{commons_page}}}}}")

    for lang_code in sorted(sitelinks.keys()):
        if lang_code != 'commonswiki':
            lang_title = sitelinks[lang_code]
            lang_prefix = lang_code.replace('wiki', '').upper()
            interwiki_parts.append(f"[[{lang_prefix}:{lang_title}]]")

    if interwiki_parts:
        content_parts.append("\n".join(interwiki_parts))
        content_parts.append("")

    # Wikidata link
    content_parts.append(f"{{{{wikidata link|{qid}}}}}")

    final_content = "<!--generated by generate_shikinaisha_pages_v23_bulk_xml.py-->\n" + "\n".join(content_parts)
    return final_content


def download_category_xml():
    """Download all category members using mwclient."""
    print("Downloading category members...")
    try:
        category = site.pages['Category:Wikidata generated shikinaisha pages']
        all_members = list(category.members())
        members = [{'title': page.name, 'ns': page.namespace} for page in all_members]
        print(f"Found {len(members)} category members")
        return members
    except Exception as e:
        print(f"Error downloading category: {e}")
        return []


def main():
    """Main process: download category, generate XML, upload in batches."""

    print("Generating standardized Shikinaisha pages (V23 - Bulk XML import)\n")
    print("=" * 60)

    # Download category members
    members = download_category_xml()
    if not members:
        print("No members found!")
        return

    # Filter to mainspace only
    members = [m for m in members if m.get('ns') == 0]
    print(f"\nFiltered to {len(members)} mainspace pages\n")

    # Process in batches
    batch_num = 1
    current_batch = []
    processed_count = 0
    error_count = 0

    for idx, member in enumerate(members, 1):
        try:
            page_name = member.get('title', '')
            print(f"{idx}. {page_name}", end="")

            # Get current page text to extract QID
            page = site.pages[page_name]
            text = page.text()

            qid = extract_wikidata_qid(text)
            if not qid:
                print(f" ... • No QID found")
                continue

            print(f" ({qid})", end="")

            # Fetch Wikidata
            entity = get_wikidata_entity(qid)
            if not entity:
                print(f" ... ! Error fetching entity")
                error_count += 1
                continue

            # Generate content
            new_content = format_page_content(page_name, qid, entity)

            # Add to current batch
            current_batch.append({
                'title': page_name,
                'content': new_content
            })

            processed_count += 1
            print(f" ... ✓ Generated")

            # When batch is full, upload it
            if len(current_batch) >= BATCH_SIZE:
                print(f"\n[Batch {batch_num}] Uploading {len(current_batch)} pages...")
                upload_batch(current_batch, batch_num)
                batch_num += 1
                current_batch = []
                print()

        except Exception as e:
            try:
                print(f"\n   ! ERROR: {e}")
            except:
                print(f"\n   ! ERROR")
            error_count += 1

    # Upload remaining batch
    if current_batch:
        print(f"\n[Batch {batch_num}] Uploading final {len(current_batch)} pages...")
        upload_batch(current_batch, batch_num)

    print(f"\n{'=' * 60}")
    print(f"\nSummary:")
    print(f"  Total pages: {len(members)}")
    print(f"  Processed: {processed_count}")
    print(f"  Errors: {error_count}")
    print(f"  Batches uploaded: {batch_num}")


def upload_batch(batch, batch_num):
    """Upload a batch of pages via XML import."""
    try:
        # Create XML export format
        xml_root = ET.Element('mediawiki')
        xml_root.set('xmlns', 'http://www.mediawiki.org/xml/export-0.10/')
        xml_root.set('version', '0.10')

        for page_data in batch:
            page_elem = ET.SubElement(xml_root, 'page')

            title_elem = ET.SubElement(page_elem, 'title')
            title_elem.text = page_data['title']

            revision_elem = ET.SubElement(page_elem, 'revision')

            text_elem = ET.SubElement(revision_elem, 'text')
            text_elem.set('xml:space', 'preserve')
            text_elem.text = page_data['content']

            comment_elem = ET.SubElement(revision_elem, 'comment')
            comment_elem.text = f"Bot: V23 - Bulk XML import with Expand templates, interwiki categories, source URLs"

        # Convert to string
        xml_string = ET.tostring(xml_root, encoding='unicode')

        # Upload via XML import using mwclient
        try:
            result = site.api(
                'import',
                xml=xml_string,
                format='json'
            )

            if 'import' in result:
                print(f"  ✓ Batch {batch_num} uploaded successfully")
            else:
                print(f"  ! Batch {batch_num} upload failed: {result}")
        except Exception as e:
            print(f"  ! Batch {batch_num} API error: {e}")

    except Exception as e:
        print(f"  ! Error uploading batch {batch_num}: {e}")

    # Rate limiting
    time.sleep(2)


if __name__ == "__main__":
    main()
