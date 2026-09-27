#!/usr/bin/env python3
"""Remove lines that are already fully on Wikidata from the drip's STATIC files.

Emma, 2026-09-27, choosing "one weekly prune step". A static file is one whose
generator never drops lines that have landed: it rebuilds from its source (reisai,
bunrei, jinjacho, hisousha, shintai), was run once by hand (the hobby-site bunrei
files), is appended to by a collector (beppyo, sonnet labels, typo fixes,
name_in_kana, ronsha rankings), or is frozen (the two wiki link files). Measured
that day: 7,065 of 35,368 lines (20%) were already on Wikidata, so ~7% of each
day's 500 draws were no-ops (`--refresh` prints the same per-file counts).

Two modes, because CI rebuilds several of these files from source EVERY day:

  --refresh   (weekly) ask WDQS which lines are fully landed and save them to
              landed_lines.json. VALUES-batched through wdqs_transport (2.5s floor, bail on 429).
  (default)   (daily) drop every line listed in landed_lines.json from its file.
              No network.

"Fully landed" means the drip would change nothing: a statement with the line's
value exists, AND that statement carries every qualifier the line has, AND it
carries every reference value the line has. A value that landed without its
qualifier or reference keeps its line, so the drip can finish it. For a label line
(Lxx), the live label must equal the line's. Anything this cannot parse or
compare is KEPT. It removes finished lines, never pending work.
"""
import argparse
import datetime
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "landed_lines.json")
BATCH = 300

STATIC_FILES = [
    "reisai.txt", "bunrei.txt", "beppyo_p612.txt", "bunrei_shinwa_otaku.txt",
    "bunrei_ikkojin.txt", "bunrei_animism.txt", "bunrei_onkamui.txt",
    "bunrei_nicovideo.txt", "bunrei_toranomaki.txt", "shintai_p825.txt",
    "jinjacho_p973.txt", "hisousha_p119_p547.txt", "en_labels_sonnet.txt",
    "label_typo_fixes.txt", "name_in_kana.txt", "ronsha_ranking_qualifiers.txt",
    "p6262_fandom_links.txt", "p11250_miraheze_links.txt",
]

ENTITY = "http://www.wikidata.org/entity/"


# ---- parsing ----------------------------------------------------------------

def split(line):
    line = line.split("    #")[0].strip()
    if "\t" in line and "|" not in line:
        line = line.replace("\t", "|")
    return re.split(r'\|(?=(?:[^"]*"[^"]*")*[^"]*$)', line)


def norm(v):
    """Comparable form of a QuickStatements value, or None if it can't be compared."""
    v = v.strip()
    if re.fullmatch(r"Q\d+", v):
        return v
    if re.fullmatch(r'[a-z][a-z-]*:"[^"]*"', v):          # monolingual text
        return v.split(":", 1)[1][1:-1]
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return None                                            # times, coords, etc.


def parse(line):
    """{'s','p','v','quals':[(p,v)],'refs':[(p,v)]} or None when not comparable."""
    parts = split(line)
    if len(parts) < 3 or not re.fullmatch(r"Q\d+", parts[0]) or parts[0].startswith("-"):
        return None
    s, p, v = parts[0], parts[1], norm(parts[2])
    if v is None:
        return None
    if re.fullmatch(r"L[a-z-]+", p):
        return {"s": s, "p": p, "v": v, "quals": [], "refs": []}
    if not re.fullmatch(r"P\d+", p):
        return None
    quals, refs = [], []
    rest = parts[3:]
    for i in range(0, len(rest) - 1, 2):
        k, val = rest[i], norm(rest[i + 1])
        if val is None:
            return None
        if k.startswith("S"):
            refs.append(("P" + k[1:], val))
        elif k.startswith("P"):
            quals.append((k, val))
        else:
            return None
    return {"s": s, "p": p, "v": v, "quals": quals, "refs": refs}


def fully_landed(line, live):
    """True only when the drip would change nothing for this line.

    live[(s, p)] = list of {'v': value, 'quals': set((p, v)), 'refs': set((p, v))}
    live[(s, 'Lxx')] = the label string
    """
    if line["p"].startswith("L"):
        return live.get((line["s"], line["p"])) == line["v"]
    for st in live.get((line["s"], line["p"]), []):
        if st["v"] != line["v"]:
            continue
        if all(q in st["quals"] for q in line["quals"]) and all(r in st["refs"] for r in line["refs"]):
            return True
    return False


# ---- WDQS ---------------------------------------------------------------------

def _clean(x):
    return x[len(ENTITY):] if x.startswith(ENTITY) else x


def sparql(q):
    """WDQS through the repo's shared transport: 2.5s floor, 15/45/135s backoff,
    SystemExit on 429. POST, because a 300-item VALUES block is a long query."""
    import wdqs_transport
    return wdqs_transport.query(q, post=True)


def fetch_live(needs):
    """needs: {prop: set(items)} -> live dict for fully_landed()."""
    live = {}
    for prop, items in needs.items():
        items = sorted(items)
        for i in range(0, len(items), BATCH):
            vals = " ".join("wd:" + q for q in items[i:i + BATCH])
            if prop.startswith("L"):
                rows = sparql(f'SELECT ?s ?l WHERE {{ VALUES ?s {{ {vals} }} '
                                       f'?s rdfs:label ?l FILTER(LANG(?l)="{prop[1:]}") }}')
                for b in rows:
                    live[(_clean(b["s"]["value"]), prop)] = b["l"]["value"]
                continue
            stmts = {}
            rows = sparql(f"SELECT ?s ?st ?o ?qp ?qv WHERE {{ VALUES ?s {{ {vals} }} "
                                   f"?s p:{prop} ?st . ?st ps:{prop} ?o . "
                                   f"OPTIONAL {{ ?st ?qp ?qv . FILTER(STRSTARTS(STR(?qp), "
                                   f"\"http://www.wikidata.org/prop/qualifier/P\")) }} }}")
            for b in rows:
                st = stmts.setdefault(b["st"]["value"], {"s": _clean(b["s"]["value"]),
                                                         "v": _clean(b["o"]["value"]),
                                                         "quals": set(), "refs": set()})
                if "qp" in b:
                    st["quals"].add((b["qp"]["value"].rsplit("/", 1)[-1], _clean(b["qv"]["value"])))
            rows = sparql(f"SELECT ?st ?rp ?rv WHERE {{ VALUES ?s {{ {vals} }} "
                                   f"?s p:{prop} ?st . ?st prov:wasDerivedFrom ?ref . ?ref ?rp ?rv . "
                                   f"FILTER(STRSTARTS(STR(?rp), \"http://www.wikidata.org/prop/reference/P\")) }}")
            for b in rows:
                st = stmts.get(b["st"]["value"])
                if st:
                    st["refs"].add((b["rp"]["value"].rsplit("/", 1)[-1], _clean(b["rv"]["value"])))
            for st in stmts.values():
                live.setdefault((st["s"], prop), []).append(st)
        print(f"  {prop}: {len(items)} item(s) checked", flush=True)
    return live


# ---- modes ---------------------------------------------------------------------

def read_lines(fn):
    path = os.path.join(HERE, fn)
    if not os.path.exists(path):
        return []
    return [l.rstrip("\n") for l in io.open(path, encoding="utf-8")]


def refresh():
    parsed = {}
    needs = {}
    for fn in STATIC_FILES:
        for l in read_lines(fn):
            if not l.strip() or l.lstrip().startswith("#"):
                continue
            p = parse(l)
            if p:
                parsed.setdefault(fn, []).append((l, p))
                needs.setdefault(p["p"], set()).add(p["s"])
    live = fetch_live(needs)
    state = {"_refreshed": datetime.date.today().isoformat()}
    for fn, rows in parsed.items():
        state[fn] = sorted({l for l, p in rows if fully_landed(p, live)})
        print(f"{fn}: {len(state[fn])} of {len(rows)} line(s) fully landed", flush=True)
    io.open(STATE, "w", encoding="utf-8", newline="\n").write(
        json.dumps(state, ensure_ascii=False, indent=1) + "\n")


REFRESH_EVERY_DAYS = 6


def _load_state():
    try:
        return json.load(io.open(STATE, encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def refresh_due(today=None):
    """Weekly, not every run: wikidata-drip runs on every push, and on 2026-09-27 a
    refresh in each Sunday run was part of the WDQS load behind three 429 bails.
    Due when the last completed refresh is REFRESH_EVERY_DAYS old, and not already
    attempted today (a refresh that 429s is not retried in every later run)."""
    today = today or datetime.date.today()
    st = _load_state()
    if st.get("_attempted") == today.isoformat():
        return False
    last = st.get("_refreshed")
    if not last:
        return True
    return (today - datetime.date.fromisoformat(last)).days >= REFRESH_EVERY_DAYS


def _mark_attempt(today=None):
    st = _load_state()
    st["_attempted"] = (today or datetime.date.today()).isoformat()
    io.open(STATE, "w", encoding="utf-8", newline="\n").write(
        json.dumps(st, ensure_ascii=False, indent=1) + "\n")


def apply():
    try:
        state = json.load(io.open(STATE, encoding="utf-8"))
    except FileNotFoundError:
        print("no landed_lines.json yet - nothing to prune")
        return
    for fn in STATIC_FILES:
        landed = set(state.get(fn, []))
        if not landed:
            continue
        lines = read_lines(fn)
        kept = [l for l in lines if l not in landed]
        if len(kept) != len(lines):
            io.open(os.path.join(HERE, fn), "w", encoding="utf-8", newline="\n").write(
                "\n".join(kept) + ("\n" if kept else ""))
        print(f"{fn}: pruned {len(lines) - len(kept)} landed line(s), {len(kept)} kept")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-query WDQS (weekly)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.refresh and refresh_due():
        try:
            refresh()
        except (SystemExit, Exception) as e:          # a 429 bails with SystemExit
            print(f"::warning::landed-lines refresh did not finish ({e!r}); "
                  f"pruning with the existing list")
            _mark_attempt()
    apply()


if __name__ == "__main__":
    main()
