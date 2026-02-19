#!/usr/bin/env python3
"""generate_shikinaisha_pages_v11.py
================================================
Generate standardized shrine pages for Wikidata-generated Shikinaisha entries
V11: Filter out P11250 property, include 90-minute startup delay
================================================

This script:
1. Waits 90 minutes before starting to reduce server load
2. Walks through [[Category:Wikidata generated shikinaisha pages]]
3. For each page with a {{wikidata link|QID}}, fetches Wikidata properties
4. Generates standardized page content with:
   - Proper intro: {{nihongo|'''EN LABEL'''|JA LABEL}} is a [[shinto shrine]] in [[Engishiki Jinmyōchō]]. Located in [[PROVINCE]]
   - Infobox with Wikidata values
   - Sections for each property (P31, P361, P625, P571, etc.)
   - P11250 property IGNORED (filtered out)
   - Sub-bullet qualifiers under each claim
   - Province category from P361 (List of Shikinaisha in X)
   - P31 instances as categories
   - Wikidata link at bottom
"""

import mwclient
import requests
import sys
import time
import re

# Fix Unicode encoding issues on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ─── CONFIG ─────────────────────────────────────────────────
WIKI_URL  = 'shinto.miraheze.org'
WIKI_PATH = '/w/'
USERNAME  = 'Immanuelle'
PASSWORD  = '[REDACTED_SECRET_2]'

WAIT_TIME = 90 * 60  # 90 minutes in seconds
PROPERTIES_TO_IGNORE = ['P11250']  # Skip these properties entirely

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

def format_time_remaining(seconds):
    """Format seconds as human readable time."""
    if seconds <= 0:
        return "0s"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def wait_before_start():
    """Wait 90 minutes before starting the main process."""
    print("="*70)
    print("V11 STARTUP DELAY (Reduce Server Load)")
    print("="*70)
    print(f"\nThis version includes a 90-minute startup delay.")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Will begin processing at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + WAIT_TIME))}")
    print("\n" + "="*70 + "\n")

    start_time = time.time()

    while time.time() - start_time < WAIT_TIME:
        elapsed = time.time() - start_time
        remaining = WAIT_TIME - elapsed

        # Print progress every 5 minutes
        if int(elapsed) % 300 == 0:
            percent = (elapsed / WAIT_TIME) * 100
            print(f"  [{format_time_remaining(elapsed)} elapsed] {format_time_remaining(remaining)} remaining... ({percent:.1f}%)")

        time.sleep(1)

    print(f"\n✓ Wait period complete! Beginning processing...\n")


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

    # Get first claim
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
    """Extract interwiki links from Wikidata sitelinks."""
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
    """Extract province name from P361 (part of) claims.

    Looks for claims like "List of Shikinaisha in Echigo Province"
    and extracts "Echigo Province".
    Handles special cases like "List of Shikinaisha in the Imperial Palace"
    """
    p361_claims = entity.get('claims', {}).get('P361', [])

    for claim in p361_claims:
        datavalue = claim.get('mainsnak', {}).get('datavalue', {})
        if isinstance(datavalue.get('value'), dict):
            list_qid = datavalue['value'].get('id')
            if list_qid:
                list_entity = get_wikidata_entity(list_qid)
                list_label = get_label(list_entity)

                if list_label:
                    # Try to extract province from "List of Shikinaisha in X"
                    match = re.match(r'List of Shikinaisha in (.+)$', list_label)
                    if match:
                        province = match.group(1)
                        return province, list_label

    return None, None


def format_wikidata_link(entity, qid):
    """Format a wikidata link using ILL syntax with WD parameter."""
    sitelinks = get_sitelinks(entity)

    # Try to find shinto wiki page first, then English Wikipedia
    first_link = None
    if 'shintowiki' in sitelinks:
        first_link = sitelinks['shintowiki']
    elif 'enwiki' in sitelinks:
        first_link = sitelinks['enwiki']
    else:
        first_link = get_label(entity, 'en') or qid

    # Build the ILL link
    wd_link = f"{{{{ill|{first_link}"

    # Add all language codes and links
    for lang_code in ['enwiki', 'jawiki', 'dewiki', 'zhwiki', 'frwiki', 'ruwiki']:
        if lang_code in sitelinks:
            lang = lang_code.replace('wiki', '')
            title = sitelinks[lang_code]
            wd_link += f"|{lang}|{title}"

    # Add WD (Wikidata QID) parameter
    label = get_label(entity, 'en') or qid
    wd_link += f"|WD={qid}}}}}"

    return wd_link


def get_property_heading(property_id):
    """Get heading text for a property in format: EN_LABEL (PID)"""
    # Try to fetch from Wikidata first
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

    # Fall back to known labels
    property_labels = {
        'P31': 'Instance of',
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


def format_qualifier_value(qualifier_value):
    """Format a qualifier value for display."""
    # Handle QID references
    if isinstance(qualifier_value, dict) and 'id' in qualifier_value:
        qid = qualifier_value['id']
        ref_entity = get_wikidata_entity(qid)
        return format_wikidata_link(ref_entity or {}, qid)

    # Handle strings
    if isinstance(qualifier_value, str):
        return qualifier_value

    # Handle other types
    return str(qualifier_value)


def get_qualifiers_text(claim):
    """Extract and format qualifiers from a claim as sub-bullets.

    Returns a list of formatted qualifier strings.
    """
    qualifiers = claim.get('qualifiers', {})
    qualifier_lines = []

    if not qualifiers:
        return qualifier_lines

    # Get qualifier property labels
    qualifier_labels = {
        'P580': 'Start time',
        'P582': 'End time',
        'P585': 'Point in time',
        'P585': 'Sourcing circumstances',
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
                # Get label for this qualifier property
                qual_label = qualifier_labels.get(qualifier_id, qualifier_id)
                formatted_qual_value = format_qualifier_value(qualifier_value)
                qualifier_lines.append(f"** {qual_label}: {formatted_qual_value}")

    return qualifier_lines


def format_claim_value(claim, entity, property_id=None):
    """Format a single claim value for display.

    Special handling for P13677 (Kokugakuin University Digital Museum entry ID).
    """
    mainsnak = claim.get('mainsnak', {})
    datavalue = mainsnak.get('datavalue', {})
    value = datavalue.get('value')

    if not value:
        return None, []

    formatted_value = None

    # Special handling for P13677 - Kokugakuin University Digital Museum entry ID
    if property_id == 'P13677' and isinstance(value, str):
        url = f"https://jmapps.ne.jp/kokugakuin/det.html?data_id={value}"
        formatted_value = f"[{url} Kokugakuin Digital Museum Item]"

    # Handle QID references
    elif isinstance(value, dict) and 'id' in value:
        qid = value['id']
        ref_entity = get_wikidata_entity(qid)
        formatted_value = format_wikidata_link(ref_entity or {}, qid)

    # Handle strings
    elif isinstance(value, str):
        formatted_value = value

    # Handle other types
    else:
        formatted_value = str(value)

    # Get qualifiers
    qualifiers = get_qualifiers_text(claim)

    return formatted_value, qualifiers


def format_page_content(page_name, qid, entity):
    """Generate standardized page content from Wikidata entity."""
    content_parts = []

    # Get basic info
    native_name = get_label(entity, 'ja')
    english_label = get_label(entity, 'en')

    # Extract province from P361
    province_name, list_label = extract_province_from_p361(entity)

    # ADD INFOBOX FIRST
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

    # THEN ADD INTRO TEXT
    # Build intro sentence with proper format:
    # {{nihongo|'''EN LABEL'''|JA LABEL}} is a [[shinto shrine]] in [[Engishiki Jinmyōchō]]. It is located in [[PROVINCE]].
    if native_name:
        intro = f"{{{{nihongo|'''{english_label}'''|{native_name}}}}}"
    else:
        intro = f"'''{english_label}'''"

    intro += " is a [[shinto shrine]] in the [[Engishiki Jinmyōchō]]."

    if province_name:
        intro += f" It is located in [[{province_name}]]."

    content_parts.append(intro)
    content_parts.append("")

    # Add sections for ALL properties (except those in PROPERTIES_TO_IGNORE)
    all_claims = get_all_property_claims(entity)
    property_order = ['P31', 'P361', 'P1448', 'P131', 'P625', 'P571', 'P580', 'P582', 'P856', 'P18', 'P825']

    # Add ordered properties first
    for prop_id in property_order:
        if prop_id in all_claims and prop_id not in PROPERTIES_TO_IGNORE:
            claims = all_claims[prop_id]
            prop_heading = get_property_heading(prop_id)
            content_parts.append(f"== {prop_heading} ==")
            content_parts.append("")

            for claim in claims:
                formatted_value, qualifiers = format_claim_value(claim, entity, prop_id)
                if formatted_value:
                    content_parts.append(f"* {formatted_value}")
                    # Add qualifiers as sub-bullets
                    for qualifier in qualifiers:
                        content_parts.append(qualifier)

            content_parts.append("")

    # Add remaining properties (except those in PROPERTIES_TO_IGNORE)
    for prop_id in sorted(all_claims.keys()):
        if prop_id not in property_order and prop_id not in PROPERTIES_TO_IGNORE:
            claims = all_claims[prop_id]
            prop_heading = get_property_heading(prop_id)
            content_parts.append(f"== {prop_heading} ==")
            content_parts.append("")

            for claim in claims:
                formatted_value, qualifiers = format_claim_value(claim, entity, prop_id)
                if formatted_value:
                    content_parts.append(f"* {formatted_value}")
                    # Add qualifiers as sub-bullets
                    for qualifier in qualifiers:
                        content_parts.append(qualifier)

            content_parts.append("")

    # Categories
    categories = ["[[Category:Wikidata generated shikinaisha pages]]"]

    # Add categories from P31 (instance of)
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

    # Add province category from P361
    if province_name:
        categories.append(f"[[Category:Shikinaisha in {province_name}]]")

    content_parts.append("\n".join(categories))
    content_parts.append("")

    # Interwiki links at the bottom
    sitelinks = get_sitelinks(entity)
    interwiki_parts = []

    # Handle commons
    if 'commonswiki' in sitelinks:
        commons_page = sitelinks['commonswiki']
        interwiki_parts.append(f"{{{{commons category|{commons_page}}}}}")

    # Add other interwiki links
    for lang_code in ['enwiki', 'jawiki', 'dewiki', 'zhwiki', 'frwiki', 'ruwiki']:
        if lang_code in sitelinks:
            lang_title = sitelinks[lang_code]
            lang_prefix = lang_code.replace('wiki', '').upper()
            interwiki_parts.append(f"[[{lang_prefix}:{lang_title}]]")

    if interwiki_parts:
        content_parts.append("\n".join(interwiki_parts))
        content_parts.append("")

    # Wikidata link at the very bottom
    content_parts.append(f"{{{{wikidata link|{qid}}}}}")

    # Add version comment at the very beginning
    final_content = "<!--generated by generate_shikinaisha_pages_v11.py-->\n" + "\n".join(content_parts)
    return final_content


def main():
    """Process all pages in [[Category:Wikidata generated shikinaisha pages]]."""

    # Wait before starting
    wait_before_start()

    print("Generating standardized Shikinaisha pages (V11 - P11250 filtered, qualifier sub-bullets)\n")
    print("=" * 60)

    # Get the category
    category = site.pages['Category:Wikidata generated shikinaisha pages']

    print(f"\nFetching mainspace pages in [[Category:Wikidata generated shikinaisha pages]]...")
    try:
        all_members = list(category.members())
        # Filter to mainspace only (namespace 0)
        members = [page for page in all_members if page.namespace == 0]
    except Exception as e:
        print(f"ERROR: Could not fetch category members – {e}")
        return

    print(f"Found {len(members)} mainspace pages (filtered from {len(all_members)} total)\n")

    processed_count = 0
    error_count = 0

    for idx, page in enumerate(members, 1):
        try:
            page_name = page.name
            print(f"{idx}. {page_name}", end="")

            # Get page text
            text = page.text()

            # Extract QID
            qid = extract_wikidata_qid(text)
            if not qid:
                print(f" ... • No QID found")
                continue

            print(f" ({qid})", end="")

            # Fetch Wikidata entity
            entity = get_wikidata_entity(qid)
            if not entity:
                print(f" ... ! Error fetching entity")
                error_count += 1
                continue

            # Generate content
            new_content = format_page_content(page_name, qid, entity)

            # Save the page
            try:
                page.edit(new_content, summary="Bot: Generate standardized Shikinaisha page (V11 - filter P11250, qualifier sub-bullets)")
                processed_count += 1
                print(f" ... ✓ Updated")
            except mwclient.errors.EditConflict:
                print(f" ! Edit conflict")
                error_count += 1
            except Exception as e:
                print(f" ! Error saving: {e}")
                error_count += 1

            # Rate limiting
            time.sleep(1.0)

        except Exception as e:
            try:
                print(f"\n   ! ERROR: {e}")
            except UnicodeEncodeError:
                print(f"\n   ! ERROR: {str(e)}")
            error_count += 1

    print(f"\n{'=' * 60}")
    print(f"\nSummary:")
    print(f"  Total pages: {len(members)}")
    print(f"  Processed: {processed_count}")
    print(f"  Errors: {error_count}")


if __name__ == "__main__":
    main()
