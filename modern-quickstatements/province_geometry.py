#!/usr/bin/env python3
"""Historical province (令制国) polygons, and the point-in-polygon test over them.

SOURCE
------
`旧国・旧郡境界データセット` (CODH), derived from `幕末明治地勢地図境界データ`
(人間文化研究機構 / NIHU).  DOI 10.20676/00000454.  **CC BY-NC.**

    https://geoshape.ex.nii.ac.jp/kg/

Licence consequence, agreed with Emma 2026-07-09: the geometry is **cached
locally and never committed, never republished, and never uploaded to Wikidata**.
Only the derived fact — "this shrine's coordinate falls inside that province" —
leaves this module.  A fact is not the geometry, and Wikidata stays CC0.

THE ERA MISMATCH — the part that would silently corrupt the output
-----------------------------------------------------------------
The dataset gives **Bakumatsu–Meiji** provinces (85 of them), not the provinces
of 927 CE that the Engishiki Jinmyōchō describes.  Two differences matter:

* Mutsu was split in 1869 into 磐城 / 岩代 / 陸前 / 陸中 / 陸奥, and Dewa into
  羽前 / 羽後.  The Engishiki knows only 陸奥国 and 出羽国, so those seven
  polygons are **unioned back** into the two classical provinces.
* 琉球 and the eleven Hokkaidō provinces postdate the Engishiki entirely and
  have no list.  They are dropped.

73 mainland/island features → 68 classical provinces, which is exactly the set
the 69 Engishiki lists cover once Heian-kyō (Q751907, the capital, not a
province) is set aside.  `build_province_index` asserts that arithmetic rather
than trusting it.

Pure standard library on purpose: `shapely` is not a CI dependency here.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.user_agent import USER_AGENT
import io
import json
import os
import time

import requests

GEOSHAPE_URL = "https://geoshape.ex.nii.ac.jp/kg/geojson/K{:02d}.geojson"
N_FEATURES = 85
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".province_cache")
HEADERS = {
    "User-Agent": USER_AGENT,
}

CREDIT = (
    "『旧国・旧郡境界データセット』（CODH作成） "
    "「幕末明治地勢地図境界データ」（人間文化研究機構作成）を加工"
)

# 1869 splits, unioned back into the province the Engishiki knows.
MERGES = {
    "陸奥": ["磐城", "岩代", "陸前", "陸中", "陸奥"],
    "出羽": ["羽前", "羽後"],
}

# Provinces that postdate the Engishiki Jinmyōchō and have no list.
DROPPED = {
    "琉球",
    "石狩", "膽振", "後志", "渡島", "天塩", "北見",
    "日高", "十勝", "釧路", "根室", "千島",
}

# Wikidata's ja label (minus the 国 suffix) vs the dataset's `name`.
ALIASES = {
    "対馬": "對馬",   # dataset uses the old form 對
}


def cache_path(n):
    return os.path.join(CACHE_DIR, "K{:02d}.geojson".format(n))


def download_provinces(throttle=0.3):
    """Fetch all 85 province GeoJSON files into the local cache. Idempotent."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    fetched = 0
    for n in range(1, N_FEATURES + 1):
        path = cache_path(n)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        r = requests.get(GEOSHAPE_URL.format(n), headers=HEADERS, timeout=60)
        if r.status_code == 429:
            raise SystemExit("FATAL: 429 from geoshape — bailing (429 policy)")
        r.raise_for_status()
        io.open(path, "w", encoding="utf-8", newline="\n").write(r.text)
        fetched += 1
        time.sleep(throttle)
    return fetched


def load_raw():
    """{dataset name: [polygon, ...]} for all 85, where polygon = list of rings."""
    out = {}
    for n in range(1, N_FEATURES + 1):
        with io.open(cache_path(n), encoding="utf-8") as fh:
            fc = json.load(fh)
        for feat in fc["features"]:
            name = feat["properties"]["name"]
            out.setdefault(name, []).extend(_polygons(feat["geometry"]))
    return out


def _polygons(geom):
    """Normalise Polygon / MultiPolygon to a list of ring-lists."""
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return list(geom["coordinates"])
    raise ValueError("unexpected geometry type: " + geom["type"])


def build_province_index():
    """{classical province name (no 国 suffix): [polygon, ...]}.

    Applies MERGES and DROPPED, then checks the count is the expected 68.
    """
    raw = load_raw()
    merged_away = {n for names in MERGES.values() for n in names}

    index = {}
    for name, polys in raw.items():
        if name in DROPPED or name in merged_away:
            continue
        index[name] = polys
    for target, sources in MERGES.items():
        polys = []
        for src in sources:
            if src not in raw:
                raise RuntimeError("merge source missing from dataset: " + src)
            polys.extend(raw[src])
        index[target] = polys

    if len(index) != 68:
        raise RuntimeError(
            "expected 68 classical provinces after merge/drop, got {}".format(len(index))
        )
    return index


def wikidata_name_to_dataset(ja_label):
    """'山城国' -> '山城'.  Applies the 対馬/對馬 alias."""
    base = ja_label[:-1] if ja_label.endswith("国") else ja_label
    return ALIASES.get(base, base)


def _point_in_ring(lon, lat, ring):
    """Ray-casting crossing count for a single closed ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        # Does the edge straddle the horizontal ray at `lat`?
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_polygon(lon, lat, polygon):
    """polygon = [outer_ring, hole_ring, ...] (GeoJSON Polygon coordinates)."""
    if not polygon or not _point_in_ring(lon, lat, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(lon, lat, hole):
            return False
    return True


def _bbox(polygon):
    xs = [p[0] for p in polygon[0]]
    ys = [p[1] for p in polygon[0]]
    return min(xs), min(ys), max(xs), max(ys)


def locate(lon, lat, index):
    """Which province contains the point?  Returns a sorted list of names.

    More than one means the point sits in overlapping polygons (should not
    happen), zero means it fell outside every province — offshore, a bad
    coordinate, or Hokkaidō/Okinawa.  The caller decides; this never guesses.
    """
    hits = []
    for name, polys in index.items():
        for poly in polys:
            x0, y0, x1, y1 = _bbox(poly)
            if not (x0 <= lon <= x1 and y0 <= lat <= y1):
                continue
            if point_in_polygon(lon, lat, poly):
                hits.append(name)
                break
    return sorted(hits)


def _haversine_km(lon1, lat1, lon2, lat2):
    from math import asin, cos, radians, sin, sqrt
    dlon = radians(lon2 - lon1)
    dlat = radians(lat2 - lat1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def nearest(lon, lat, index):
    """(province name, km to its nearest boundary vertex) for a point that is
    inside no polygon.

    Diagnostic only — a small offshore island (Kinkasan, Aoshima) is missing
    from the Bakumatsu boundary data and lands a few km from its true province,
    while Hokkaidō and Okinawa land hundreds of km from anything.  The distance
    is what distinguishes the two, so it is reported rather than thresholded:
    nothing here decides what to emit.
    """
    best, best_km = None, float("inf")
    for name, polys in index.items():
        for poly in polys:
            for x, y in poly[0]:
                km = _haversine_km(lon, lat, x, y)
                if km < best_km:
                    best, best_km = name, km
    return best, best_km
