"""
Generate QuickStatements to add P1027 (conferred by) Q712534 (modern system of ranked Shinto shrines)
qualifier to all P13723 (modern shrine ranking) statements on Wikidata.

This is preparatory work for generalizing P13723 to all shrine ranking systems,
where the qualifier will distinguish which ranking system conferred the rank.
"""

import io
import sys
import json
import requests
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "ModernQuickstatements/1.0 (shrine ranking qualifier generator)",
    "Accept": "application/sparql-results+json",
}

# Fetch all items with P13723, getting the rank value QID
# We fetch in batches since there are 4000+ results
QUERY = """
SELECT ?item ?rankvalue WHERE {
  ?item p:P13723 ?stmt .
  ?stmt ps:P13723 ?rankvalue .
  FILTER NOT EXISTS { ?stmt pq:P1027 ?_ }
}
ORDER BY ?item
"""

# Count total P13723 statements (with and without qualifier)
TOTAL_QUERY = """
SELECT (COUNT(*) AS ?total) WHERE {
  ?item p:P13723 ?stmt .
  ?stmt ps:P13723 ?rankvalue .
}
"""


def fetch_sparql(query):
    """Run a SPARQL query against Wikidata."""
    r = requests.get(
        SPARQL_ENDPOINT,
        params={"query": query, "format": "json"},
        headers=HEADERS,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def qid(uri):
    """Extract QID from Wikidata URI."""
    return uri.split("/")[-1]


def main():
    print("Fetching total P13723 statement count...")
    total_results = fetch_sparql(TOTAL_QUERY)
    total = int(total_results[0]["total"]["value"])
    print(f"Total P13723 statements: {total}")

    print("Fetching all P13723 statements without P1027 qualifier...")
    results = fetch_sparql(QUERY)
    remaining = len(results)
    completed = total - remaining
    print(f"Found {remaining} statements to qualify ({completed}/{total} done).")

    # Write total count for the site build to use
    with open("total_count.txt", "w") as f:
        f.write(str(total))

    if not results:
        print("Nothing to do — all statements already have P1027 qualifier.")
        # Still write empty file so site build doesn't break
        open("modern_shrine_ranking_qualifiers.txt", "w").close()
        return

    # Generate QuickStatements v1 format with pipe delimiters
    # Format: QXXX|P13723|QYYY|P1027|Q712534
    output_file = "modern_shrine_ranking_qualifiers.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
            item = qid(r["item"]["value"])
            rankvalue = qid(r["rankvalue"]["value"])
            f.write(f"{item}|P13723|{rankvalue}|P1027|Q712534\n")

    print(f"Written {remaining} QuickStatements lines to {output_file}")


if __name__ == "__main__":
    main()
