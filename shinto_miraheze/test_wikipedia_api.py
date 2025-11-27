"""Test Wikipedia API queries with User-Agent header"""

import requests
import sys

# Test the specific case that was failing
lang_code = "en"
category_title = "1004 establishments"
normalized_title = category_title.replace(' ', '_')

url = f"https://{lang_code}.wikipedia.org/w/api.php"
params = {
    "action": "query",
    "titles": f"Category:{normalized_title}",
    "prop": "pageprops",
    "format": "json"
}
headers = {
    "User-Agent": "WikidataBot/1.0 (https://shinto.miraheze.org/; bot for adding wikidata links)"
}

print(f"Testing Wikipedia API query...")
print(f"URL: {url}")
print(f"Params: {params}")
print(f"Headers: {headers}\n")

try:
    response = requests.get(url, params=params, headers=headers, timeout=10)
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}\n")

    response.raise_for_status()
    data = response.json()

    print(f"Response Data:\n{data}\n")

    if "query" in data and "pages" in data["query"]:
        pages = data["query"]["pages"]
        print(f"Pages found: {len(pages)}")

        for page_id, page_data in pages.items():
            print(f"\n  Page ID: {page_id}")
            print(f"  Page Data: {page_data}")

            if int(page_id) < 0:
                print(f"  -> Page doesn't exist")
            elif "pageprops" in page_data and "wikibase_item" in page_data["pageprops"]:
                qid = page_data["pageprops"]["wikibase_item"]
                print(f"  -> Found Wikidata: {qid}")
            else:
                print(f"  -> No wikidata found in pageprops")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
