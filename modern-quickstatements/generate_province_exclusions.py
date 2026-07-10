#!/usr/bin/env python3
"""Link each Engishiki Jinmyōchō list to the notable shrines inside its province
that the list does *not* contain, saying why they are absent.

Emma 2026-07-09, verbatim:

    "I'm not trying to get you to remove anything. I'm trying to get you to add
    links to the Beppyō Shrines and Kokushi Genzaisha, and Shikigeisha that are
    located within the province. … the idea here is essentially that the excluded
    thing lists the shrines that would be in that list because they're a Beppyō
    shrine or whatever, except they didn't exist back then or whatever. … it
    involves shape files of the provinces … you need to cross-reference the
    coordinates of all members of these classes with the state file in order to
    find which ones are within the future jurisdiction of the province."

THIS SCRIPT ADDS STATEMENTS.  IT REMOVES NOTHING, EVER.  No `-` line is emitted
by any code path here; `assert_add_only()` enforces that on the way out.

THE MODEL
---------
    LIST  (e.g. Q11467693 "List of Shikinaisha in Yamashiro Province")
      P361  part of                  -> Q11064932  Engishiki Jinmyōchō
      P1001 applies to jurisdiction  -> the province
      P3113 does not have part       -> the excluded shrine        <-- ADDED HERE
              P3831 object of statement has role -> its class(es)  <-- ADDED HERE
              P1013 criterion used               -> why it's absent <-- ADDED HERE

`P3113` sits on the LIST, never on the shrine.

WHY IT IS ABSENT — and why one blanket reason would have been wrong
-------------------------------------------------------------------
Wikidata's own class definitions settle this:

* `Q118469772` 式外社 shikigesha — "a shrine that **existed in 927** but was not
  recorded in the Engishiki Jinmyōchō".
* `Q118304363` 国史見在社 kokushi genzaisha — "recorded in the Rikkokushi but not
  in the Engishiki Jinmyōchō".  Also extant at the time.
* `Q10898274` 別表神社 Beppyō Shrine — a *modern* ranking (carried by `P13723`,
  never `P31`).  A shrine that is only this, and is not Shikinaisha, was not
  around in 927.

So "did not exist" is true of the Beppyō-only shrines and **false by definition**
of the other two.  Emma, told this: *"Kokushi genzaisha did exist then, same with
shikigesha, only ones that are just beppyo shrines did not exist at the time. If
something is beppyo and shikigesha it gets criteria of unrecorded."*  Hence:

    beppyō only                     -> P1013 = Q3877969   non-existence
    anything shikigesha/kokushi     -> P1013 = Q110240047 omission
                                       ("non-inclusion of a … set member … whose
                                        inclusion would be expected")

Every role the shrine holds is emitted; there is no precedence order (Emma: *"if
something has all of these properties … do all of them"*).

SCOPE
-----
1. **New exclusions** — the ~307 non-Shikinaisha candidates carrying `P625`, each
   point-in-polygon'd into a province, added to that province's list.
2. **Backfill** — the existing `P3113` statements that carry no `P3831` at all
   (265 of 287 as of 2026-07-09) get their role + criterion.

Heian-kyō (`Q751907`) is the 69th list and is not a province.  Emma: *"Just don't
do it. That one is solved."*  It is skipped.

    python generate_province_exclusions.py [--out FILE] [--print-url] [--open]
"""
import argparse
import collections
import io
import json
import os
import sys
import time
import urllib.parse
import webbrowser

import requests

import province_geometry as pg

SPARQL_ENDPOINT = "https://query-main.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:EmmaBot) shintowiki-scripts",
    "Accept": "application/sparql-results+json",
}
QS_URL = "https://quickstatements.toolforge.org/#/v1="

JINMYOCHO = "Q11064932"     # Engishiki Jinmyōchō
SHIKINAISHA = "Q134917286"  # already on the lists, so never an exclusion
HEIAN_KYO = "Q751907"       # the 69th list: the capital, not a province

BEPPYO = "Q10898274"        # via P13723 (a ranking), NOT P31
KOKUSHI = "Q118304363"      # via P31
SHIKIGESHA = "Q118469772"   # via P31

P_EXCLUDES = "P3113"        # does not have part
P_ROLE = "P3831"            # object of statement has role
P_CRITERION = "P1013"       # criterion used

NON_EXISTENCE = "Q3877969"  # "quality or state of not existing"
OMISSION = "Q110240047"     # "non-inclusion of a … set member … expected"

OUTPUT_FILE = "province_exclusions.txt"

# Two shrines stand on small islands that the Bakumatsu boundary data simply
# does not draw, so they fall inside no polygon at all. Both province
# attributions are historically certain, and the distances are not close: these
# two sit 0.3 km and 1.5 km from their province, while the next-nearest
# outside-everything shrine is 28.6 km away across the Tsugaru Strait. Named
# rather than thresholded — a distance rule would fire on data nobody has seen.
# Emma 2026-07-09: "Include both, hardcoded."
ISLAND_EXCEPTIONS = {
    "Q2857985": "日向",    # Aoshima Shrine — Aoshima islet, Miyazaki (Hyūga)
    "Q11677857": "陸奥",   # Koganeyama Shrine — Kinkasan island (Mutsu)
}

_last = 0.0


def sparql(query):
    global _last
    for attempt in range(5):
        gap = time.time() - _last
        if gap < 3:
            time.sleep(3 - gap)
        r = requests.get(SPARQL_ENDPOINT, params={"query": query, "format": "json"},
                         headers=HEADERS, timeout=180)
        _last = time.time()
        if r.status_code == 429:
            raise SystemExit("FATAL: 429 Too Many Requests — bailing (429 policy)")
        if r.status_code >= 500:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        try:
            return json.loads(r.text, strict=False)["results"]["bindings"]
        except (ValueError, KeyError):
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("SPARQL kept returning truncated bodies")


def qid(binding):
    return binding["value"].rsplit("/", 1)[-1]


# ---------------------------------------------------------------- queries

def fetch_lists():
    """{province ja label: (list qid, province qid)} — Heian-kyō excluded."""
    rows = sparql("""
    SELECT ?l ?prov ?provJa WHERE {
      ?l wdt:P361 wd:%s ; wdt:P1001 ?prov .
      ?prov rdfs:label ?provJa FILTER(LANG(?provJa) = "ja")
    }""" % JINMYOCHO)
    out = {}
    for r in rows:
        prov = qid(r["prov"])
        if prov == HEIAN_KYO:
            continue
        out[r["provJa"]["value"]] = (qid(r["l"]), prov)
    return out


def fetch_candidates():
    """[(shrine qid, lon, lat, {classes})] — non-Shikinaisha, coordinate-bearing."""
    rows = sparql("""
    SELECT ?s ?coord ?beppyo ?kokushi ?shikige WHERE {
      { ?s wdt:P13723 wd:%s } UNION { ?s wdt:P31 wd:%s } UNION { ?s wdt:P31 wd:%s }
      ?s wdt:P625 ?coord .
      FILTER NOT EXISTS { ?s wdt:P31 wd:%s }
      BIND(EXISTS { ?s wdt:P13723 wd:%s } AS ?beppyo)
      BIND(EXISTS { ?s wdt:P31 wd:%s }    AS ?kokushi)
      BIND(EXISTS { ?s wdt:P31 wd:%s }    AS ?shikige)
    }""" % (BEPPYO, KOKUSHI, SHIKIGESHA, SHIKINAISHA, BEPPYO, KOKUSHI, SHIKIGESHA))
    # The three-branch UNION yields one row per matching class, so a shrine that
    # is (say) both Beppyō and shikigesha comes back twice. Deduplicate by QID —
    # the EXISTS flags are identical across a shrine's rows, so the last wins.
    out = {}
    for r in rows:
        lon, lat = parse_point(r["coord"]["value"])
        if lon is None:
            continue
        out[qid(r["s"])] = (lon, lat, classes_from_flags(
            r["beppyo"]["value"], r["kokushi"]["value"], r["shikige"]["value"]))
    return [(s, lon, lat, cls) for s, (lon, lat, cls) in out.items()]


def fetch_existing():
    """{(list qid, shrine qid): n_role_qualifiers} for every current P3113."""
    rows = sparql("""
    SELECT ?l ?s (COUNT(DISTINCT ?role) AS ?nroles) WHERE {
      ?l wdt:P361 wd:%s ; p:%s ?st .
      ?st ps:%s ?s .
      OPTIONAL { ?st pq:%s ?role }
    } GROUP BY ?l ?s""" % (JINMYOCHO, P_EXCLUDES, P_EXCLUDES, P_ROLE))
    return {(qid(r["l"]), qid(r["s"])): int(r["nroles"]["value"]) for r in rows}


def fetch_classes(shrine_qids):
    """{shrine qid: {classes}} for an arbitrary set (used for the backfill)."""
    out = {}
    qids = sorted(shrine_qids)
    for i in range(0, len(qids), 200):
        chunk = qids[i:i + 200]
        values = " ".join("wd:" + q for q in chunk)
        rows = sparql("""
        SELECT ?s ?beppyo ?kokushi ?shikige WHERE {
          VALUES ?s { %s }
          BIND(EXISTS { ?s wdt:P13723 wd:%s } AS ?beppyo)
          BIND(EXISTS { ?s wdt:P31 wd:%s }    AS ?kokushi)
          BIND(EXISTS { ?s wdt:P31 wd:%s }    AS ?shikige)
        }""" % (values, BEPPYO, KOKUSHI, SHIKIGESHA))
        for r in rows:
            out[qid(r["s"])] = classes_from_flags(
                r["beppyo"]["value"], r["kokushi"]["value"], r["shikige"]["value"])
    return out


# ---------------------------------------------------------------- model

def classes_from_flags(beppyo, kokushi, shikige):
    got = set()
    if beppyo == "true":
        got.add(BEPPYO)
    if kokushi == "true":
        got.add(KOKUSHI)
    if shikige == "true":
        got.add(SHIKIGESHA)
    return got


def parse_point(literal):
    """'Point(139.7 35.6)' -> (139.7, 35.6).  Anything else -> (None, None)."""
    if not literal.startswith("Point(") or not literal.endswith(")"):
        return None, None
    try:
        lon, lat = literal[6:-1].split()
        return float(lon), float(lat)
    except ValueError:
        return None, None


def criterion_for(classes):
    """Beppyō alone means it wasn't there yet; the other classes were, and were
    merely left out of the register."""
    if classes == {BEPPYO}:
        return NON_EXISTENCE
    return OMISSION


def qs_lines(list_qid, shrine_qid, classes):
    """One line per role.  The first also carries the criterion.

    QuickStatements matches an existing statement by its main value, so repeating
    the same `list|P3113|shrine` triple with a different qualifier adds that
    qualifier to the one statement rather than creating a second.
    """
    roles = sorted(classes)
    if not roles:
        return []
    crit = criterion_for(classes)
    head = "{}|{}|{}|{}|{}|{}|{}".format(
        list_qid, P_EXCLUDES, shrine_qid, P_ROLE, roles[0], P_CRITERION, crit)
    rest = ["{}|{}|{}|{}|{}".format(list_qid, P_EXCLUDES, shrine_qid, P_ROLE, r)
            for r in roles[1:]]
    return [head] + rest


def assert_add_only(lines):
    """The one invariant Emma stated three times.  Fail loudly, never emit."""
    bad = [l for l in lines if l.lstrip().startswith("-")]
    if bad:
        raise RuntimeError(
            "REMOVAL LINE GENERATED — this task is ADD-ONLY: {!r}".format(bad[:3]))


def qs_batch_url(lines):
    return QS_URL + urllib.parse.quote("||".join(lines), safe="")


# ---------------------------------------------------------------- main

def build(lists, candidates, existing, index):
    """Returns (lines, report). Lines are interleaved per shrine."""
    by_province = {}
    for ja_label, (list_qid, prov_qid) in lists.items():
        by_province[pg.wikidata_name_to_dataset(ja_label)] = (list_qid, prov_qid, ja_label)

    unmatched = sorted(set(by_province) - set(index))
    if unmatched:
        raise RuntimeError("province polygons missing for: {}".format(unmatched))

    lines, report = [], {
        "added": [], "outside": [], "ambiguous": [], "already": [],
        "backfilled": [], "backfill_no_class": [], "island": [],
    }

    for shrine, lon, lat, classes in sorted(candidates):
        hits = pg.locate(lon, lat, index)
        hits = [h for h in hits if h in by_province]
        if not hits and shrine in ISLAND_EXCEPTIONS:
            hits = [ISLAND_EXCEPTIONS[shrine]]
            report["island"].append((shrine, hits[0]))
        if not hits:
            near, km = pg.nearest(lon, lat, index)
            report["outside"].append((shrine, lon, lat, near, round(km, 1)))
            continue
        if len(hits) > 1:
            report["ambiguous"].append((shrine, hits))
            continue
        list_qid, prov_qid, ja = by_province[hits[0]]
        if (list_qid, shrine) in existing:
            report["already"].append((shrine, list_qid))
            continue
        new = qs_lines(list_qid, shrine, classes)
        lines.extend(new)
        report["added"].append((shrine, list_qid, ja, sorted(classes)))

    # Backfill: existing statements with zero role qualifiers.
    bare = [(l, s) for (l, s), n in sorted(existing.items()) if n == 0]
    if bare:
        classes_by_shrine = fetch_classes({s for _, s in bare})
        for list_qid, shrine in bare:
            classes = classes_by_shrine.get(shrine, set())
            if not classes:
                report["backfill_no_class"].append((shrine, list_qid))
                continue
            lines.extend(qs_lines(list_qid, shrine, classes))
            report["backfilled"].append((shrine, list_qid, sorted(classes)))

    assert_add_only(lines)
    return lines, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    ap.add_argument("--print-url", action="store_true")
    ap.add_argument("--open", action="store_true",
                    help="open the whole batch in one QuickStatements tab")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("Downloading province polygons (cached, never committed)...", flush=True)
    fetched = pg.download_provinces()
    print("  {} newly fetched; {}".format(fetched, pg.CREDIT))

    index = pg.build_province_index()
    print("  {} classical provinces after merging the 1869 splits".format(len(index)))

    print("Querying Engishiki lists...", flush=True)
    lists = fetch_lists()
    print("  {} province lists (Heian-kyō excluded)".format(len(lists)))

    print("Querying candidate shrines...", flush=True)
    candidates = fetch_candidates()
    print("  {} non-Shikinaisha candidates with coordinates".format(len(candidates)))

    print("Querying existing P3113 statements...", flush=True)
    existing = fetch_existing()
    bare = sum(1 for n in existing.values() if n == 0)
    print("  {} existing, {} of them without a role qualifier".format(len(existing), bare))

    print("Locating shrines in provinces...", flush=True)
    lines, report = build(lists, candidates, existing, index)

    path = args.out
    if os.path.dirname(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

    print("\n  {} new exclusions ({} via the island exceptions)".format(
        len(report["added"]), len(report["island"])))
    print("  {} existing statements backfilled with a role".format(len(report["backfilled"])))
    print("  {} already listed".format(len(report["already"])))
    print("  {} fell outside every province polygon".format(len(report["outside"])))
    print("  {} landed in more than one province".format(len(report["ambiguous"])))
    print("  {} existing statements have none of the three classes".format(
        len(report["backfill_no_class"])))
    print("  {} QuickStatements lines -> {}".format(len(lines), path))

    io.open(os.path.splitext(path)[0] + "_report.json", "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=2))

    if lines and (args.print_url or args.open):
        url = qs_batch_url(lines)
        print("\n  batch URL is {} characters".format(len(url)))
        if args.print_url:
            print(url)
        if args.open:
            webbrowser.open(url)


if __name__ == "__main__":
    main()
