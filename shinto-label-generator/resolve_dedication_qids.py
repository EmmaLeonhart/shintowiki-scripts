#!/usr/bin/env python3
"""
resolve_dedication_qids.py
==========================
Resolve the dedication concepts the corpus actually uses to Wikidata QIDs, and
**validate every one against `saint_qids.ALLOWED_CLASSES`** before it is offered.

## Why a script and not another ad-hoc lookup

`paused/table_audit.tsv` was an ad-hoc lookup, and measured against live `P31` it
was **52% wrong** — French communes, a 1984 film, a Sufjan Stevens album, eight
church buildings. There is no reason a second hand lookup would be cleaner, so
this one is reproducible, states its query, and shows every candidate it rejected.

⛔ **It proposes; it does not install.** Output is a report and a JSON. A concept
reaches `saint_qids.SAINT_QIDS` only after a human reads the line. The failure
mode being guarded against is precisely a search engine's first hit being taken
as an answer.

## The unit is the CONCEPT, not the table key

271 table keys are unresolved, but they collapse to **29 concepts**: `assunta`,
`asunción` and `mariä himmelfahrt` are one Assumption; `martin` and `martino` are
one saint; `holy trinity` and `dreifaltigkeit` are one Trinity. Two table entries
that render to the same Japanese string are the same thing, which is the same
join that took the NAMES coverage from 18 keys to 63.

## The acceptance rule

A concept is accepted only when **exactly one** search candidate survives the
class filter. Zero survivors is a refusal; two or more is a refusal, because
choosing between them is the judgement this file exists to avoid making.

Usage:
    python resolve_dedication_qids.py            # report
    python resolve_dedication_qids.py --json out.json
"""

import argparse
import collections
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# The repo-root bootstrap, so `python shinto-label-generator/resolve_dedication_qids.py`
# can do a package-absolute `shinto_miraheze` import. ⚠ Written with the `_uos`
# alias because that is the idiom the rest of the repo uses and
# tests/test_sys_path_bootstrap_ordering.py matches it literally — it caught this
# file first with no bootstrap at all, then again with the same logic spelled
# `os.path`.
import os as _uos, sys as _usys  # noqa: E402
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(
        _uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

import religious_building_morphemes as m      # noqa: E402
import saint_qids as sq                        # noqa: E402
import generate_religious_building_multilang as G  # noqa: E402

API = "https://www.wikidata.org/w/api.php"
THROTTLE = 1.0

# English query for a concept whose table key is not English. Keyed by the ja
# rendering, which is what identifies a concept here.
QUERY_BY_JA = {
    "聖母": "Mary mother of Jesus",
    "聖母被昇天": "Assumption of Mary",
    "至聖三者": "Trinity",
    "マルティヌス": "Martin of Tours",
    "イエスの聖心": "Sacred Heart",
    "ラウレンティウス": "Saint Lawrence",
    "聖十字架": "True Cross",
    "生神女庇護": "Intercession of the Theotokos",
    "ペトロとパウロ": "Saints Peter and Paul",
    "ヨハネ": "John the Evangelist",
    "キリスト": "Jesus Christ",
    "洗礼者ヨハネ": "John the Baptist",
    "ロクス": "Saint Roch",
    "主の昇天": "Ascension of Jesus",
    "主の変容": "Transfiguration of Jesus",
    "十字架挙栄": "Exaltation of the Holy Cross",
    "生神女誕生": "Nativity of Mary",
    "生神女就寝": "Dormition of the Mother of God",
    "恩寵の聖母": "Our Lady of Graces",
    "平和": "Our Lady of Peace",
    "カルメル山の聖母": "Our Lady of Mount Carmel",
    "聖母訪問": "Visitation of the Blessed Virgin Mary",
    # Second round, 2026-09-20. ⚠ `Mary mother of Jesus` returned ZERO hits —
    # wbsearchentities is not a sentence parser — while `Blessed Virgin Mary`
    # returns Q345 and nothing else survives the class filter. A query that finds
    # nothing looks exactly like a concept Wikidata does not have.
    "ヨセフ": "Saint Joseph",
    "無原罪の御宿り": "Immaculate Conception",
    "聖霊": "Holy Spirit",
    "バルトロマイ": "Bartholomew the Apostle",
    "復活": "Resurrection of Jesus",
    "セバスティアヌス": "Saint Sebastian",
    "王たるキリスト": "Christ the King",
    "諸聖人": "All Saints' Day",
    "聖家族": "Holy Family",
    "ロザリオの聖母": "Our Lady of the Rosary",
    "雪の聖母": "Our Lady of the Snows",
    "マグダラのマリア": "Mary Magdalene",
    "受胎告知": "Annunciation",
    "降誕": "Nativity of Jesus",
    "天の元后": "Queen of Heaven",
    "悲しみの聖母": "Our Lady of Sorrows",
    "レオンハルト": "Leonard of Noblac",
    "ウィトゥス": "Saint Vitus",
    "パウロ": "Paul the Apostle",
    "聖母の汚れなき御心": "Immaculate Heart of Mary",
    "パラスケヴィ": "Paraskevi of Iconium",
    "ニコラオス": "Nicholas of Myra",
    "アントニオ": "Anthony of Padua",
    "フランチェスコ": "Francis of Assisi",
}


def _api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def search(term, limit=8):
    """[(qid, label, description)] — Wikidata's own search, unfiltered."""
    out = _api({"action": "wbsearchentities", "format": "json",
                "language": "en", "uselang": "en", "type": "item",
                "limit": limit, "search": term})
    return [(h["id"], h.get("label", ""), h.get("description", ""))
            for h in out.get("search", [])]


def classes(qids):
    """{qid: [P31 values]} for a batch."""
    if not qids:
        return {}
    ents = _api({"action": "wbgetentities", "format": "json",
                 "ids": "|".join(qids), "props": "claims"}).get("entities", {})
    out = {}
    for q, e in ents.items():
        out[q] = [c["mainsnak"]["datavalue"]["value"]["id"]
                  for c in (e.get("claims") or {}).get("P31", [])
                  if c.get("mainsnak", {}).get("datavalue")]
    return out


def unresolved_concepts():
    """{ja_rendering: (item_slots, [table keys])} for what has no QID yet.

    ⛔ Asks `saint_qids._index()` rather than rebuilding the term join. The first
    version rebuilt it, and a rebuilt join is how `qid_for_match` came to read
    one map while the measurement read two — 2,168 statements against a measured
    4,155. One join, one answer.
    """
    rows = G.source_labels()
    with io.open(G.CACHE, encoding="utf-8") as fh:
        cache = json.load(fh)
    index = sq._index()
    un = collections.Counter()
    kinds = {}
    for qid, label in rows:
        meta = cache["items"].get(qid) or {}
        if m.is_category_shaped(label):
            continue
        if not G.building_type(meta, m.TYPES):
            continue
        hit = m.match_dedication(label)
        if not hit:
            continue
        if sq.qid_for_match(hit):
            continue                      # already resolved, by either map
        kind, key, _ = hit
        if kind == "names":
            if len(key) != 1:
                continue                  # two dedicatees is a caller problem
            key = key[0]
        un[key] += 1
        kinds[key] = kind

    def render(k):
        kind = kinds[k]
        if kind in ("specific", "generic"):
            return m.DEDICATIONS[k]["ja"]
        if kind == "names":
            return m.NAMES[k]["ja"]
        return m.NAME_PHRASES[k]["ja"]

    grouped = collections.defaultdict(lambda: [0, []])
    for k, n in un.items():
        try:
            r = render(k)
        except KeyError:
            continue
        if r in index:
            continue
        grouped[r][0] += n
        grouped[r][1].append(k)
    return {r: (n, sorted(ks)) for r, (n, ks) in grouped.items()}


def resolve(ja, query):
    """(qid, why) — a single validated candidate, or (None, why not)."""
    hits = search(query)
    if not hits:
        return None, "search returned nothing for %r" % query
    cls = classes([h[0] for h in hits])
    time.sleep(THROTTLE)
    kept = [h for h in hits if set(cls.get(h[0], [])) & set(sq.ALLOWED_CLASSES)]
    if not kept:
        got = "; ".join("%s %s (%s)" % (h[0], h[1], h[2][:30]) for h in hits[:3])
        return None, "no candidate is a dedicatee class — %s" % got
    if len(kept) > 1:
        got = "; ".join("%s %s" % (h[0], h[1]) for h in kept[:4])
        return None, "%d candidates survive, choosing is not this file's job — %s" % (
            len(kept), got)
    q, label, desc = kept[0]
    return q, "%s — %s" % (label, desc[:52])


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", help="Write the accepted map here.")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    concepts = unresolved_concepts()
    ranked = sorted(concepts.items(), key=lambda kv: -kv[1][0])
    if args.limit:
        ranked = ranked[:args.limit]
    print("unresolved concepts: %d, covering %d item-slots\n"
          % (len(concepts), sum(v[0] for v in concepts.values())))

    accepted, refused = {}, []
    for ja, (slots, keys) in ranked:
        query = QUERY_BY_JA.get(ja)
        if not query:
            refused.append((ja, slots, "no English query written for this concept"))
            continue
        qid, why = resolve(ja, query)
        if qid:
            accepted[ja] = {"qid": qid, "slots": slots, "keys": keys, "why": why}
            print("  ✓ %-14s %5d  %-11s %s" % (ja, slots, qid, why))
        else:
            refused.append((ja, slots, why))
            print("  ✗ %-14s %5d  %s" % (ja, slots, why))

    print("\naccepted %d covering %d slots; refused %d covering %d"
          % (len(accepted), sum(v["slots"] for v in accepted.values()),
             len(refused), sum(r[1] for r in refused)))
    print("\n⛔ Read every accepted line before adding it to saint_qids.")
    if args.json:
        with io.open(args.json, "w", encoding="utf-8") as fh:
            json.dump(accepted, fh, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
