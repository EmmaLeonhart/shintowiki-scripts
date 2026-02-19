import requests
import json
import sys
import io
from collections import defaultdict

# Fix Unicode encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Wikidata SPARQL endpoint
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"

# SPARQL query to get all instances of Q845945 with labels
query = """
SELECT ?item ?itemLabel_ja ?itemLabel_zh ?itemLabel_zh_hant ?itemLabel_zh_hk WHERE {
  ?item wdt:P31 wd:Q845945.

  OPTIONAL { ?item rdfs:label ?itemLabel_ja. FILTER(LANG(?itemLabel_ja) = "ja") }
  OPTIONAL { ?item rdfs:label ?itemLabel_zh. FILTER(LANG(?itemLabel_zh) = "zh") }
  OPTIONAL { ?item rdfs:label ?itemLabel_zh_hant. FILTER(LANG(?itemLabel_zh_hant) = "zh-hant") }
  OPTIONAL { ?item rdfs:label ?itemLabel_zh_hk. FILTER(LANG(?itemLabel_zh_hk) = "zh-hk") }
}
"""

print("Querying Wikidata for instances of Q845945...")
response = requests.get(SPARQL_ENDPOINT, params={
    'query': query,
    'format': 'json'
}, headers={'User-Agent': 'WikidataLabelComparisonBot/1.0'})

data = response.json()
results = data['results']['bindings']

print(f"Found {len(results)} results\n")

# Organize the data
items_with_labels = []
stats = {
    'total': 0,
    'has_ja': 0,
    'has_zh': 0,
    'has_zh_hant': 0,
    'has_zh_hk': 0,
    'has_any_chinese': 0,
    'has_both_ja_and_chinese': 0,
    'identical_ja_zh': 0,
    'identical_ja_zh_hant': 0,
    'identical_ja_zh_hk': 0
}

for result in results:
    item_data = {
        'qid': result['item']['value'].split('/')[-1],
        'ja': result.get('itemLabel_ja', {}).get('value'),
        'zh': result.get('itemLabel_zh', {}).get('value'),
        'zh_hant': result.get('itemLabel_zh_hant', {}).get('value'),
        'zh_hk': result.get('itemLabel_zh_hk', {}).get('value')
    }

    stats['total'] += 1

    if item_data['ja']:
        stats['has_ja'] += 1
    if item_data['zh']:
        stats['has_zh'] += 1
    if item_data['zh_hant']:
        stats['has_zh_hant'] += 1
    if item_data['zh_hk']:
        stats['has_zh_hk'] += 1

    has_chinese = item_data['zh'] or item_data['zh_hant'] or item_data['zh_hk']
    if has_chinese:
        stats['has_any_chinese'] += 1
        if item_data['ja']:
            stats['has_both_ja_and_chinese'] += 1
            items_with_labels.append(item_data)

            # Compare labels
            if item_data['ja'] and item_data['zh'] and item_data['ja'] == item_data['zh']:
                stats['identical_ja_zh'] += 1
            if item_data['ja'] and item_data['zh_hant'] and item_data['ja'] == item_data['zh_hant']:
                stats['identical_ja_zh_hant'] += 1
            if item_data['ja'] and item_data['zh_hk'] and item_data['ja'] == item_data['zh_hk']:
                stats['identical_ja_zh_hk'] += 1

# Print statistics
print("=" * 80)
print("STATISTICS")
print("=" * 80)
print(f"Total items: {stats['total']}")
print(f"Items with ja label: {stats['has_ja']}")
print(f"Items with zh label: {stats['has_zh']}")
print(f"Items with zh-hant label: {stats['has_zh_hant']}")
print(f"Items with zh-hk label: {stats['has_zh_hk']}")
print(f"Items with any Chinese label: {stats['has_any_chinese']}")
print(f"Items with both ja and Chinese labels: {stats['has_both_ja_and_chinese']}")
print()
print("COMPARISON RESULTS:")
if stats['has_both_ja_and_chinese'] > 0:
    if stats['has_zh'] > 0:
        print(f"  ja = zh: {stats['identical_ja_zh']}/{stats['has_zh']} ({100*stats['identical_ja_zh']/stats['has_zh']:.1f}%)")
    if stats['has_zh_hant'] > 0:
        print(f"  ja = zh-hant: {stats['identical_ja_zh_hant']}/{stats['has_zh_hant']} ({100*stats['identical_ja_zh_hant']/stats['has_zh_hant']:.1f}%)")
    if stats['has_zh_hk'] > 0:
        print(f"  ja = zh-hk: {stats['identical_ja_zh_hk']}/{stats['has_zh_hk']} ({100*stats['identical_ja_zh_hk']/stats['has_zh_hk']:.1f}%)")
print()

# Show examples of differences
print("=" * 80)
print("EXAMPLES (showing items with both ja and Chinese labels)")
print("=" * 80)
count = 0
for item in items_with_labels[:20]:  # Show first 20 examples
    print(f"\n{item['qid']}:")
    print(f"  ja:      {item['ja']}")
    if item['zh']:
        match = "✓" if item['ja'] == item['zh'] else "✗"
        print(f"  zh:      {item['zh']} {match}")
    if item['zh_hant']:
        match = "✓" if item['ja'] == item['zh_hant'] else "✗"
        print(f"  zh-hant: {item['zh_hant']} {match}")
    if item['zh_hk']:
        match = "✓" if item['ja'] == item['zh_hk'] else "✗"
        print(f"  zh-hk:   {item['zh_hk']} {match}")
    count += 1

if len(items_with_labels) > 20:
    print(f"\n... and {len(items_with_labels) - 20} more items")

print("\nDone!")
