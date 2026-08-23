"""Pull the evidence needed to write an English description for each pending work-file.

Sibling of `fetch_label_typo_evidence.py`, and it exists for the same reason: the answer to
"what is this shrine" must come from the item and its article, not from the shape of its
name. 八幡神社 names hundreds of shrines; guessing from a label is how a description ends up
attached to the wrong place.

WHY `wbgetentities` AND NOT SPARQL. `CLAUDE.md` is explicit -- Wikidata is a destination for
the drip, not a database to query, and a large batched SPARQL sweep is the thing that drew
repeated 503s and got that rule written. This needs specific known QIDs, which
`wbgetentities` returns 50 at a time: 63 items is two requests. A SPARQL sweep for the same
data would be both slower and worse citizenship.

What it collects per item, in the order a description actually gets built from:

  P31   what it is            -- shrine / former shrine / temple, and the class matters
  P131  where it is           -- resolved up the chain, since the municipality is usually the
                                 cheapest distinguisher between same-named members
  P17   country               -- not all of these are in Japan; several are colonial-era
                                 shrines in Taiwan and Korea, where "in Japan" would be wrong
  P825  deity                 -- the fallback distinguisher when members share a municipality
  P571 / P576                 -- founded / dissolved, which is what separates a former shrine
  sitelinks + other-language descriptions -- free context already written by someone

Read-only. It never edits, and it writes its output into the repo rather than anywhere else.

Usage:
    python shinto_miraheze/fetch_description_evidence.py [--limit N] [--out FILE]
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT  # noqa: E402

WORKDIR = os.path.join(ROOT, "description_enrichment_en")
DEFAULT_OUT = os.path.join(ROOT, "description_enrichment_en", "_evidence.json")
API = "https://www.wikidata.org/w/api.php"

# Pace even though this is only a couple of requests -- the rule is that request loops are
# paced, not that a loop is only paced when it feels big enough to matter.
PACE = 1.5

ANSWERS_RE = re.compile(r"<!--\s*ANSWERS:\s*(.*?)-->", re.S)
LINE_RE = re.compile(r"^(Q\d+):\s*(.*)$", re.M)
MEMBER_RE = re.compile(r"^\*\s*\[\[d:(Q\d+)\]\]\s*—\s*(.*)$", re.M)


def pending():
    """-> [(filename, qid, member_context_line)] for every unanswered QID."""
    out = []
    for name in sorted(os.listdir(WORKDIR)):
        if not name.endswith(".wiki"):
            continue
        path = os.path.join(WORKDIR, name)
        body = io.open(path, encoding="utf-8").read()
        block = ANSWERS_RE.search(body)
        if not block:
            continue
        members = dict(MEMBER_RE.findall(body))
        for qid, answer in LINE_RE.findall(block.group(1)):
            if not answer.strip():
                out.append((name, qid, members.get(qid, "")))
    return out


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": WIKIDATA_USER_AGENT})
    return json.load(urllib.request.urlopen(req, timeout=60))


def entities(qids):
    """Fetch in batches of 50 -- the API's own limit, and the reason this is two requests."""
    got = {}
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        got.update(_get({"action": "wbgetentities", "ids": "|".join(chunk),
                         "props": "labels|descriptions|claims|sitelinks",
                         "languages": "en|ja|zh|ko", "format": "json"})["entities"])
        time.sleep(PACE)
    return got


def _values(entity, prop):
    out = []
    for claim in entity.get("claims", {}).get(prop, []):
        snak = claim["mainsnak"]
        if snak.get("snaktype") != "value":
            continue
        v = snak["datavalue"]["value"]
        if isinstance(v, dict):
            # entity ref -> id; monolingual text (P1448) -> text; anything else stays raw
            out.append(v.get("id") or v.get("text") or v)
        else:
            out.append(v)
    return out


def summarise(qid, entity, label_cache):
    def lbl(q):
        return label_cache.get(q, q)
    return {
        "qid": qid,
        "en_label": entity.get("labels", {}).get("en", {}).get("value"),
        "ja_label": entity.get("labels", {}).get("ja", {}).get("value"),
        "en_desc": entity.get("descriptions", {}).get("en", {}).get("value"),
        "other_desc": {k: v["value"] for k, v in entity.get("descriptions", {}).items()
                       if k != "en"},
        "P31_class": [lbl(q) for q in _values(entity, "P31")],
        "P131_in": [lbl(q) for q in _values(entity, "P131")],
        "P17_country": [lbl(q) for q in _values(entity, "P17")],
        "P825_deity": [lbl(q) for q in _values(entity, "P825")],
        "P571_founded": [v.get("time") if isinstance(v, dict) else v
                         for v in _values(entity, "P571")],
        "P576_dissolved": [v.get("time") if isinstance(v, dict) else v
                           for v in _values(entity, "P576")],
        "sitelinks": {k: v["title"] for k, v in entity.get("sitelinks", {}).items()},
        # The four fields the review page needs to answer "what is this, and where".
        # Coordinates matter most: half of these carry real ones, so "where" has a concrete
        # answer for them rather than only an ancient district name.
        "_coords": _coords(entity),
        "_p1448": (_values(entity, "P1448") or [None])[0] if _values(entity, "P1448") else None,
        "_list": ", ".join(lbl(q) for q in _values(entity, "P361")) or None,
        "_kokugakuin": (_values(entity, "P13677") or [None])[0],
    }


def _coords(entity):
    for claim in entity.get("claims", {}).get("P625", []):
        snak = claim["mainsnak"]
        if snak.get("snaktype") == "value":
            v = snak["datavalue"]["value"]
            return [v["latitude"], v["longitude"]]
    return None


def main(argv=None):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    todo = pending()
    if args.limit:
        todo = todo[:args.limit]
    print("%d unanswered QIDs across %d work-files"
          % (len(todo), len({f for f, _, _ in todo})))
    if not todo:
        return 0

    qids = [q for _, q, _ in todo]
    ents = entities(qids)

    # Second pass: resolve every referenced QID to a label, so P131/P825 read as places and
    # deities rather than as Q-numbers. Same batching, same pacing.
    refs = set()
    for e in ents.values():
        for prop in ("P31", "P131", "P17", "P825", "P361"):
            refs.update(v for v in _values(e, prop) if isinstance(v, str) and v.startswith("Q"))
    refs -= set(qids)
    labels = {}
    ref_list = sorted(refs)
    for i in range(0, len(ref_list), 50):
        chunk = ref_list[i:i + 50]
        got = _get({"action": "wbgetentities", "ids": "|".join(chunk),
                    "props": "labels", "languages": "en|ja", "format": "json"})["entities"]
        for q, e in got.items():
            lab = e.get("labels", {})
            labels[q] = (lab.get("en") or lab.get("ja") or {}).get("value", q)
        time.sleep(PACE)

    rows = []
    for fname, qid, context in todo:
        e = ents.get(qid, {})
        row = summarise(qid, e, labels)
        row["work_file"] = fname
        row["context_line"] = context
        rows.append(row)

    with io.open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)
    print("wrote %s (%d rows, %d referenced labels resolved)"
          % (os.path.relpath(args.out, ROOT), len(rows), len(labels)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
