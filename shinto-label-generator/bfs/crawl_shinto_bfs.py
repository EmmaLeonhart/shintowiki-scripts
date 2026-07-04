"""
Layered breadth-first crawl of the Wikidata Shinto neighbourhood.

Seeds (depth 0) are the shrine-ranking / classification concepts in
seeds_raw.txt (that file is a Wikidata "What links here" dump, but that was only
how the seed LIST was gathered — the crawl itself follows FORWARD links).

From each item we expand along its OUTGOING links: every wikibase-item value in
the item's statements, qualifiers and references (same rule as
latent-space-cartography's random_walk.py). Backlinks are intentionally NOT
followed (they explode into all of Japanese geography); `--backlinks` can turn
them back on for experiments.

An item's depth is its shortest hop distance from any seed. Each depth level is
written to levels/level_NN.tsv (qid<TAB>en-label) once it is fully discovered.

The crawl is INCREMENTAL and RESUMABLE. A single run expands at most --max-nodes
nodes then checkpoints to state.json; re-run (the default resumes) to continue.
Reads are throttled and the crawl bails immediately on HTTP 429 (repo policy).

Usage:
  python crawl_shinto_bfs.py --status                 # show progress, no network
  python crawl_shinto_bfs.py --max-nodes 60           # expand up to 60 nodes
  python crawl_shinto_bfs.py --max-depth 5 --max-nodes 500
  python crawl_shinto_bfs.py --reset                  # wipe state, restart at seeds
"""

import os
import re
import sys
import io
import json
import time
import argparse
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
LEVELS_DIR = os.path.join(HERE, "levels")
SEEDS_RAW = os.path.join(HERE, "seeds_raw.txt")
STATE_PATH = os.path.join(HERE, "state.json")

API = "https://www.wikidata.org/w/api.php"
ENTITYDATA = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
UA = {"User-Agent": "ShintoWikiBFS/1.0 (immanuelleleonhart@gmail.com; shinto label corpus)"}
THROTTLE = 0.3            # seconds between network calls (read-only politeness)
QID_RE = re.compile(r"^Q\d+$")
SEED_LINE_RE = re.compile(r"\((Q\d+)\)")


def _utf8():
    if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class RateLimited(SystemExit):
    """Raised on HTTP 429 — repo policy is to bail immediately, no retries."""


def _get(url, params=None):
    time.sleep(THROTTLE)
    r = requests.get(url, params=params, headers=UA, timeout=60)
    if r.status_code == 429:
        raise RateLimited("HTTP 429 from Wikidata — bailing (repo policy: no retries).")
    r.raise_for_status()
    return r


# ---------------------------------------------------------------------------
# Seed parsing
# ---------------------------------------------------------------------------

def parse_seeds():
    """Return an ordered, de-duplicated list of seed QIDs from seeds_raw.txt.
    Lines without a (Qxxx) token (User:/Wikidata:/property pages) are skipped."""
    seeds, seen = [], set()
    with open(SEEDS_RAW, encoding="utf-8") as f:
        for line in f:
            m = SEED_LINE_RE.search(line)
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                seeds.append(m.group(1))
    return seeds


# ---------------------------------------------------------------------------
# Wikidata access
# ---------------------------------------------------------------------------

def outgoing_links(qid):
    """Every wikibase-item QID referenced by qid's statements, qualifiers and
    references. Returns a set (may be empty; never raises on a missing item)."""
    r = _get(ENTITYDATA.format(qid))
    ent = r.json().get("entities", {}).get(qid)
    if not ent or "missing" in ent:
        return set()
    out = set()

    def _take(snak):
        dv = snak.get("datavalue", {})
        if dv.get("type") == "wikibase-entityid":
            v = dv.get("value", {}).get("id", "")
            if QID_RE.match(v):
                out.add(v)

    for statements in ent.get("claims", {}).values():
        for st in statements:
            _take(st.get("mainsnak", {}))
            for quals in st.get("qualifiers", {}).values():
                for q in quals:
                    _take(q)
            for ref in st.get("references", []):
                for snaks in ref.get("snaks", {}).values():
                    for s in snaks:
                        _take(s)
    return out


def backlinks(qid, cap=None):
    """Every Q-item that links to qid ("what links here", ns0), paginated.
    Returns (set_of_qids, truncated_bool). `cap` bounds a single mega-node."""
    out, cont, truncated = set(), None, False
    while True:
        params = {"action": "query", "list": "backlinks", "bltitle": qid,
                  "blnamespace": "0", "bllimit": "500", "format": "json"}
        if cont:
            params["blcontinue"] = cont
        data = _get(API, params).json()
        for b in data.get("query", {}).get("backlinks", []):
            t = b.get("title", "")
            if QID_RE.match(t):
                out.add(t)
        if cap is not None and len(out) >= cap:
            truncated = True
            break
        cont = data.get("continue", {}).get("blcontinue")
        if not cont:
            break
    return out, truncated


def resolve_labels(qids):
    """Batch-resolve en labels (falls back to the QID). {qid: label}."""
    labels = {}
    qids = list(qids)
    for i in range(0, len(qids), 50):
        batch = qids[i:i + 50]
        data = _get(API, {"action": "wbgetentities", "ids": "|".join(batch),
                          "props": "labels", "languages": "en", "format": "json"}).json()
        ents = data.get("entities", {})
        for q in batch:
            labels[q] = ents.get(q, {}).get("labels", {}).get("en", {}).get("value", q)
    return labels


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(state):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, STATE_PATH)


def write_level(depth, qid_to_label):
    path = os.path.join(LEVELS_DIR, f"level_{depth:02d}.tsv")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for q in sorted(qid_to_label, key=lambda x: int(x[1:])):
            f.write(f"{q}\t{qid_to_label[q]}\n")
    return path


def init_state():
    os.makedirs(LEVELS_DIR, exist_ok=True)
    seeds = parse_seeds()
    print(f"Parsed {len(seeds)} seed QIDs.")
    labels = resolve_labels(seeds)
    write_level(0, labels)
    state = {
        "max_depth": 5,
        "current_level": 0,          # the level whose nodes are being expanded
        "depth_of": {q: 0 for q in seeds},
        "frontier": list(seeds),     # level-0 nodes not yet expanded
        "next_set": [],              # accumulating level-1 discoveries
        "backlink_cap": None,
        "counts": {"0": len(seeds)},
    }
    save_state(state)
    print(f"Initialised: level 0 = {len(seeds)} seeds -> {os.path.join(LEVELS_DIR, 'level_00.tsv')}")
    return state


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def status(state):
    if not state:
        print("No state yet. Run without --status to initialise from seeds.")
        return
    print(f"max_depth={state['max_depth']}  current_level={state['current_level']}")
    print(f"visited (all depths): {len(state['depth_of'])}")
    print(f"frontier (level {state['current_level']} unexpanded): {len(state['frontier'])}")
    print(f"next_set (level {state['current_level']+1} so far): {len(state['next_set'])}")
    print("per-level counts:")
    for d in sorted(state["counts"], key=int):
        done = os.path.exists(os.path.join(LEVELS_DIR, f"level_{int(d):02d}.tsv"))
        print(f"  level {d}: {state['counts'][d]}{'' if done else '  (in progress)'}")


def run(max_nodes, max_depth, backlink_cap, use_backlinks):
    state = load_state() or init_state()
    state["max_depth"] = max_depth
    state["backlinks"] = use_backlinks
    if backlink_cap is not None:
        state["backlink_cap"] = backlink_cap
    depth_of = state["depth_of"]
    frontier = state["frontier"]
    next_set = set(state["next_set"])
    cap = state["backlink_cap"]
    processed = 0
    truncated_nodes = []

    while processed < max_nodes:
        if not frontier:
            # level complete — finalise the next level
            lvl = state["current_level"]
            if lvl >= max_depth:
                print(f"Reached max_depth={max_depth}; nothing left to expand within budget.")
                break
            newd = lvl + 1
            print(f"\nLevel {lvl} fully expanded. Resolving {len(next_set)} labels for level {newd}...")
            labels = resolve_labels(next_set)
            path = write_level(newd, labels)
            state["counts"][str(newd)] = len(next_set)
            print(f"  wrote {len(next_set)} items -> {path}")
            state["current_level"] = newd
            frontier = sorted(next_set, key=lambda x: int(x[1:]))
            next_set = set()
            if newd >= max_depth:
                print(f"Level {newd} written; at max_depth. Stop.")
                state["frontier"] = frontier
                state["next_set"] = []
                save_state(state)
                break
            continue

        qid = frontier.pop()
        try:
            neigh = outgoing_links(qid)
            trunc = False
            if use_backlinks:
                inc, trunc = backlinks(qid, cap)
                neigh |= inc
        except RateLimited as e:
            print(f"\n{e}\nCheckpointing and exiting.")
            state["frontier"] = frontier + [qid]   # re-queue the unfinished node
            state["next_set"] = sorted(next_set, key=lambda x: int(x[1:]))
            save_state(state)
            return
        if trunc:
            truncated_nodes.append(qid)
        fresh = 0
        for nb in neigh:
            if nb not in depth_of:
                depth_of[nb] = state["current_level"] + 1
                next_set.add(nb)
                fresh += 1
        processed += 1
        print(f"[{processed}/{max_nodes}] {qid}: +{fresh} new "
              f"(frontier {len(frontier)}, next {len(next_set)})"
              f"{'  [backlinks truncated]' if trunc else ''}")

        if processed % 20 == 0:
            state["frontier"] = frontier
            state["next_set"] = sorted(next_set, key=lambda x: int(x[1:]))
            save_state(state)

    # checkpoint at end of run
    state["frontier"] = frontier
    state["next_set"] = sorted(next_set, key=lambda x: int(x[1:]))
    save_state(state)
    print(f"\nRun done: expanded {processed} nodes this run. "
          f"visited={len(depth_of)}, frontier={len(frontier)}, next_set={len(next_set)}")
    if truncated_nodes:
        print(f"[NOTE] backlinks truncated at cap for {len(truncated_nodes)} node(s): "
              f"{truncated_nodes[:10]}")


def main():
    _utf8()
    ap = argparse.ArgumentParser(description="Layered BFS crawl of the Wikidata Shinto neighbourhood.")
    ap.add_argument("--max-nodes", type=int, default=60, help="max nodes to expand this run")
    ap.add_argument("--max-depth", type=int, default=5, help="deepest level to discover")
    ap.add_argument("--backlinks", action="store_true",
                    help="ALSO follow backlinks (off by default; forward links only)")
    ap.add_argument("--backlink-cap", type=int, default=None,
                    help="cap backlinks per node when --backlinks (logs truncation)")
    ap.add_argument("--status", action="store_true", help="print progress and exit")
    ap.add_argument("--reset", action="store_true", help="wipe state and restart from seeds")
    args = ap.parse_args()

    if args.reset and os.path.exists(STATE_PATH):
        os.remove(STATE_PATH)
        print("State reset.")
    if args.status:
        status(load_state())
        return
    run(args.max_nodes, args.max_depth, args.backlink_cap, args.backlinks)


if __name__ == "__main__":
    main()
