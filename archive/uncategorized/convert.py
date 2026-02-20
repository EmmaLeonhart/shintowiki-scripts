import pandas as pd
import pykakasi

# File names
INPUT_FILE = "query.csv"
OUTPUT_FILE = "query with romaji.csv"

# Load CSV
df = pd.read_csv(INPUT_FILE)

# Legacy pykakasi API (best for kana-only)
kks = pykakasi.kakasi()
kks.setMode("H", "a")
kks.setMode("K", "a")
kks.setMode("J", "a")
kks.setMode("r", "Hepburn")
kks.setMode("s", False)  # no spaces
conv = kks.getConverter()

# Convert function
def to_romaji(text):
    romaji = conv.do(text)
    romaji = (
        romaji.replace("ou", "ō")
              .replace("oo", "ō")
              .replace("uu", "ū")
              .replace("aa", "ā")
              .replace("ii", "ī")
              .replace("ee", "ē")
    )
    return romaji.capitalize()

# Apply conversion
df["romaji"] = df["kana"].astype(str).apply(to_romaji)

# Save result
df.to_csv(OUTPUT_FILE, index=False)
print(f"✅ Done. Output saved to: {OUTPUT_FILE}")
