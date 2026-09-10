"""
generate_lost_shrine_parity.py
==============================
GENERATOR ONLY — writes QuickStatements into an atomic .txt for the single daily
submitter. NEVER edits Wikidata; no edit summaries. (CLAUDE.md "Wikidata editing
— ONE path only".)

## Why this exists

`lost_shrine_creates.txt` was delivered TWICE. Emma created the three items by
hand through QuickStatements on 2026-09-06 (`#temporary_batch_1788736…`), and the
`create-items.yml` dispatch on 2026-09-10 created them again, because nothing at
run time asks whether a batch's subjects already exist — `create_items.py` has no
duplicate guard, by Emma's instruction, and `docs/lost-shrines.md` says the
re-check is re-running the generator, which was not done.

| Emma's, 2026-09-06 | the dispatch's, 2026-09-10 | subject |
|---|---|---|
| `Q141335127` | `Q141406052` | Kamo Shrine / 加茂神社 (Odawara) |
| `Q141335121` | `Q141406056` | Kenkō-ji Temple / 見光寺 (Hannō) |
| `Q141335129` | `Q141406059` | Chikadono Shrine / 近殿神社 (Kumagaya) |

Emma's instruction, 2026-09-10, was NOT to merge them: *"You edit them to be as
good as possible … they should be identical in form"*, and *"apply the goddamn
coordinates to all of them, the old ones I created and the ones you created"*.

## What is actually missing

Measured against the live items, the six differ in exactly one statement each:
**the three 09-10 items have no `P625`.** Every other statement, its references,
and every label already match within each pair — the create run reported one
`ERROR: unencodable QS value '@lat/lon'` per block because `parse_qs_value` had
no globe-coordinate case, so the coordinate line was the only one that could not
execute. That case now exists in `direct_daily_edits.py`; this file is what feeds
it the three statements it never wrote.

Each `P625` carries the same `S854` reference as its twin, so the pairs match on
references too — the Kamo pair has none, the other two cite the University of
Tokyo simple-geocoding service, exactly as in `lost_shrine_creates.txt`.

## What cannot be made identical, and why it is not a defect

**Descriptions.** Wikidata enforces uniqueness on the (label, description) PAIR
per language, so two items sharing a label cannot also share a description in
that language — the API refuses the second with
`already has label "…" associated with language code …, using the same
description text`. That is what every `FAIL` in the 09-10 run was. So the
descriptions are necessarily split across each pair (Kamo: `ja` on Emma's, `en`
on the other) and no generator can close that gap while both items exist. This is
the same constraint `docs/description_label_policy.md` is built around.

## Self-healing

Re-asks Wikidata each build and emits only what is genuinely absent, so it goes
empty once the three coordinates land and stays empty. It is ADD-only.

Output: lost_shrine_parity.txt
"""

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from shinto_miraheze.wd_pace import wd_pace
import argparse
import io
import json
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request

API = "https://www.wikidata.org/w/api.php"
UA = WIKIDATA_USER_AGENT
OUTPUT_FILE = "lost_shrine_parity.txt"

# The pairs, and the coordinate each subject should carry. Both values are read
# off lost_shrine_creates.txt, which is where Emma's own batch came from, so the
# twins cannot drift to two different points.
#
# `ref` is the S854 the create batch attaches to that P625. Kamo's has none there
# and none on Emma's item, so it gets none here — parity, not a house style.
PAIRS = [
    {"subject": "Kamo Shrine",
     "items": ["Q141335127", "Q141406052"],
     "p625": "@35.27712826106289/139.17583480745927",
     "ref": None},
    {"subject": "Kenkō-ji Temple",
     "items": ["Q141335121", "Q141406056"],
     "p625": "@35.838036/139.337402",
     "ref": "https://geocode.csis.u-tokyo.ac.jp/home/simple-geocoding/"},
    {"subject": "Chikadono Shrine",
     "items": ["Q141335129", "Q141406059"],
     "p625": "@36.209057/139.336243",
     "ref": "https://geocode.csis.u-tokyo.ac.jp/home/simple-geocoding/"},
]


def fetch_claims(qids):
    """{qid: {prop: [value-token]}} for the given items, or None on failure."""
    params = {"action": "wbgetentities", "ids": "|".join(qids), "props": "claims",
              "format": "json", "formatversion": "2"}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    wd_pace()          # one request per build, but the floor is not optional
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
    except Exception as exc:
        print(f"Wikidata read failed ({exc}) — leaving the existing file untouched.")
        return None
    out = {}
    for qid in qids:
        entity = data.get("entities", {}).get(qid, {})
        if "missing" in entity:
            print(f"  {qid} does not exist — skipping its pair")
            out[qid] = None
            continue
        props = {}
        for prop, statements in entity.get("claims", {}).items():
            values = []
            for st in statements:
                dv = st["mainsnak"].get("datavalue", {}).get("value")
                if isinstance(dv, dict) and "latitude" in dv:
                    dv = "@{}/{}".format(dv["latitude"], dv["longitude"])
                values.append(dv)
            props[prop] = values
        out[qid] = props
    return out


def coords_match(existing, wanted):
    """Is `wanted` already among `existing`, to the precision Wikidata stores?

    Compared as floats, not strings: the API returns 35.838036 for what the batch
    wrote as `@35.838036/…`, but it would return 35.27712826106289 rounded if the
    stored precision were coarser, and a string compare would then re-add a
    coordinate that is already there on every single build.
    """
    lat, _, lon = wanted.partition("@")[2].partition("/")
    for value in existing:
        if not isinstance(value, str) or not value.startswith("@"):
            continue
        elat, _, elon = value[1:].partition("/")
        try:
            if abs(float(elat) - float(lat)) < 1e-6 and abs(float(elon) - float(lon)) < 1e-6:
                return True
        except ValueError:
            continue
    return False


def build_lines(claims):
    """(lines, report) — a P625 add for each item of each pair that lacks one."""
    lines, report = [], []
    for pair in PAIRS:
        for qid in pair["items"]:
            props = claims.get(qid)
            if props is None:
                report.append((qid, pair["subject"], "item missing"))
                continue
            if coords_match(props.get("P625", []), pair["p625"]):
                report.append((qid, pair["subject"], "already has it"))
                continue
            line = f'{qid}|P625|{pair["p625"]}'
            if pair["ref"]:
                line += f'|S854|"{pair["ref"]}"'
            lines.append(line)
            report.append((qid, pair["subject"], "ADD P625"))
    return lines, report


def publish_to_site(path):
    """Copy the batch into _site/ for the GitHub Pages browser. The file the daily
    editor reads is the bare-name one in this directory; this is only the published
    copy. Guarded against SameFileError so it is safe if handed the _site path."""
    os.makedirs("_site", exist_ok=True)
    dest = os.path.join("_site", os.path.basename(path))
    if os.path.abspath(dest) != os.path.abspath(path):
        shutil.copy(path, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUTPUT_FILE)
    args = ap.parse_args()

    print("=== Generate lost-shrine twin-parity QuickStatements (no direct edits) ===\n")
    qids = [q for pair in PAIRS for q in pair["items"]]
    claims = fetch_claims(qids)
    if claims is None:
        return
    lines, report = build_lines(claims)
    for qid, subject, verdict in report:
        print(f"  {qid:<12} {subject:<20} [{verdict}]")

    path = args.out if os.path.dirname(args.out) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), args.out)
    with open(path, "w", encoding="utf-8") as f:
        # Sorted at the writer, per DEVLOG 2026-08-21: result order is not stable,
        # so emitting in it rewrites the whole file on every build.
        f.write("\n".join(sorted(set(lines))) + ("\n" if lines else ""))
    publish_to_site(path)
    print(f"\nWrote {len(lines)} lines to {path} (0 means the twins already match)")


if __name__ == "__main__":
    # Rebound here rather than at import time: at module level it replaces the
    # caller's stdout, which breaks pytest's capture in every test that imports this.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    main()
