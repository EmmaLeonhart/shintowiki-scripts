# Historical province (令制国) boundary polygons

Written 2026-07-09. This doc is the thing `queue.md` promised and no earlier session
ever delivered — the province-exclusion task referenced `docs/province_shapefiles.md`
for weeks while the file did not exist in any commit on any branch.

## The source

**`旧国・旧郡境界データセット`** — Old Province & Old District Boundary Dataset, published by
ROIS-DS Center for Open Data in the Humanities (CODH).

* Landing page: <https://geoshape.ex.nii.ac.jp/kg/>
* Per-province GeoJSON: `https://geoshape.ex.nii.ac.jp/kg/geojson/K{NN}.geojson`, `NN` = 01…85
* DOI: [10.20676/00000454](https://doi.org/10.20676/00000454)
* Derived from `幕末明治地勢地図境界データ` (人間文化研究機構 / NIHU)
* **Licence: CC BY-NC.**

Required credit line, reproduced in `province_geometry.CREDIT`:

> 『旧国・旧郡境界データセット』（CODH作成） 「幕末明治地勢地図境界データ」（人間文化研究機構作成）を加工

Each file is a `FeatureCollection`; province properties are `{id, name, yomi, pref, number}`.
Most provinces are a single `Polygon`; the island-heavy ones are many features
(薩摩 94, 大隅 81, 琉球 271).

## The licence constraint, and how we satisfy it

Wikidata is CC0. CC BY-NC data cannot be uploaded to it, and the NC clause makes
redistribution awkward regardless.

Emma's decision (2026-07-09): **use it, geometry stays local.**

* The 85 GeoJSON files are cached in `modern-quickstatements/.province_cache/`, which is
  **gitignored**. They are never committed, never mirrored to `_site/`, never republished.
* The only thing that leaves the module is the derived fact *"this shrine's coordinate falls
  inside that province"* — a fact, not the geometry. Facts are not copyrightable, and no
  polygon reaches Wikidata.
* `P3896` (geoshape) is **not** written to the province items. Don't.

## The era mismatch — the trap

The dataset gives **Bakumatsu–Meiji** provinces, not the provinces of 927 CE that the
Engishiki Jinmyōchō describes. Using its 85 names as-is would silently mis-assign every
shrine in Tōhoku and invent twelve provinces that have no Engishiki list.

| Problem | Handling (`province_geometry.py`) |
|---|---|
| Mutsu was split in 1869 into 磐城 / 岩代 / 陸前 / 陸中 / 陸奥 | `MERGES["陸奥"]` unions all five back |
| Dewa was split into 羽前 / 羽後 | `MERGES["出羽"]` unions both back |
| 琉球 + 11 Hokkaidō provinces postdate the Engishiki | `DROPPED` (12 names) |
| Dataset writes Tsushima with the old kanji 對馬 | `ALIASES["対馬"] = "對馬"` |

The arithmetic, asserted in `build_province_index()` rather than trusted:

```
85 features − 12 dropped = 73 mainland/island
73 − 7 merged-away + 2 merge targets = 68 classical provinces
```

68 is exactly the province set the Engishiki lists cover. The 69th list is
**Heian-kyō (`Q751907`)** — the capital, not a province, so it has no polygon. Emma:
*"Just don't do it. That one is solved."* It is skipped.

Boundaries elsewhere are broadly stable between 927 and the Bakumatsu, but not identical.
This is an approximation, and shrines near a province border should be read as such.

## Consumers

`modern-quickstatements/generate_province_exclusions.py` — point-in-polygon over the
~307 non-Shikinaisha candidate shrines (Beppyō / kokushi genzaisha / shikigesha) carrying
`P625`, emitting **ADD-only** `P3113` QuickStatements onto each province's list. See that
script's docstring for the data model and the criterion split.

`province_geometry.locate()` returns *all* containing provinces and never guesses: zero hits
(offshore, bad coordinate, Hokkaidō/Okinawa) and multiple hits are both reported, not resolved.
