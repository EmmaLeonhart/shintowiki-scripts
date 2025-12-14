import pandas as pd
import requests
import time
import urllib.parse

# Load the file
df = pd.read_csv("shrine_wikipedia_excerpt.csv")

# Decode URL-encoded article titles
df["decoded_title"] = df["ja_title"].apply(urllib.parse.unquote)

# Function to get first 1000 characters from ja.wikipedia
def get_excerpt(title):
    url = "https://ja.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "exchars": 1000,
        "explaintext": 1,
        "format": "json",
        "titles": title
    }
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        pages = r.json()["query"]["pages"]
        return next(iter(pages.values())).get("extract", "")
    except Exception as e:
        return f"ERROR: {e}"

# Apply to all articles with delay
excerpts = []
for title in df["decoded_title"]:
    excerpts.append(get_excerpt(title))
    time.sleep(0.5)

df["excerpt_ja"] = excerpts

# Save result
df.to_csv("shrine_wikipedia_excerpt_fixed.csv", index=False)
