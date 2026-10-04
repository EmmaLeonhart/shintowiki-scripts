"""Fallback source for the wiki-link fetchers when shinto.miraheze.org can't be read.

`fetch_p6262_from_wiki.py` and `fetch_p11250_from_wiki.py` read their lines from
[[QuickStatements/P6262]] / [[QuickStatements/P11250]]. Those pages are only a rendering of
`shinto_miraheze/orchestrators/duplicate_qids.state` (title -> QID, committed in this repo) by
`generate_p6262_quickstatements.py` / `generate_p11250_quickstatements.py`. Miraheze blocks the
GitHub Actions runners, so both the render and the read fail, and the fetchers used to crash on
the 403 (file frozen) or empty the file on a 429.

Measured 2026-10-03 against live Wikidata: the staged files were nearly complete (P6262 4,095 of
4,133 needed, P11250 1,096 of 1,228), so this is a small top-up, not a new pipeline.

The fallback is ADD-ONLY to the staged file: it keeps every existing line (including the P11250
label lines) and appends a line only for a QID the file does not already hold, once the caller has
filtered out items that already carry the property and Wikidata redirects.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(os.path.dirname(HERE), "shinto_miraheze", "orchestrators",
                     "duplicate_qids.state")


def lines_from_state(prop, line_re, state_path=STATE):
    """QS lines `Qid|prop|"shinto:<title>"` for every title in the map that `line_re` accepts
    (the fetchers' own patterns refuse Category: and Template: pages)."""
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    out = []
    for title, qid in sorted(state.items()):
        if '"' in title:
            # A quote inside a QuickStatements string can't be expressed. The old wiki round
            # trip escaped `List of Kofun in Japan with the Name "Hyō"` on every pass until the
            # line was 1 MB of backslashes and stalled the whole home-page batch.
            continue
        line = '%s|%s|"shinto:%s"' % (qid, prop, title)
        if line_re.match(line):
            out.append(line)
    return out


def merge_into(path, new_lines, line_re):
    """Append `new_lines` whose QID has no line in `path` yet. Returns the number added."""
    existing = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            existing = [l.rstrip("\n") for l in f if l.strip()]
    held = {m.group(1) for m in (line_re.match(l) for l in existing) if m}
    added = []
    for line in new_lines:
        qid = line_re.match(line).group(1)
        if qid not in held:
            added.append(line)
            held.add(qid)
    with open(path, "w", encoding="utf-8") as f:
        for line in existing + added:
            f.write(line + "\n")
    return len(added)


def state_fallback(prop, line_re, output_file, existing_qids, fetch_redirect_qids):
    """Run the fallback end to end. `existing_qids` is the caller's set of items that already
    carry `prop` (None means the SPARQL check failed: add nothing, keep the file)."""
    if existing_qids is None:
        print("Fallback: SPARQL check failed; keeping the staged file unchanged")
        return
    candidates = [l for l in lines_from_state(prop, line_re)
                  if line_re.match(l).group(1) not in existing_qids]
    redirects = fetch_redirect_qids({line_re.match(l).group(1) for l in candidates})
    candidates = [l for l in candidates if line_re.match(l).group(1) not in redirects]
    n = merge_into(output_file, candidates, line_re)
    print("Fallback from duplicate_qids.state: %d candidate(s), %d redirect(s) dropped, "
          "%d line(s) added to %s" % (len(candidates) + len(redirects), len(redirects), n,
                                      output_file))
