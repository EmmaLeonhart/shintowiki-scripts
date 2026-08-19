#!/usr/bin/env python3
"""
collect_beppyo_p612.py
======================
Collector for the `beppyo_p612/` work-queue (queue item A0b). Turns filled
`<!-- ANSWER: ... -->` markers into QuickStatements for the mother-house model:

    <shrine>|P612|<head>|P1013|Q195793|S854|"<jawiki article url>"

ONE P612 statement with the P1013=Q195793 criterion qualifier in the SAME
statement — the invariant in docs/wikidata_shrine_festival_model.md. A bare P612
is never emitted.

Answers:
  * `MOTHER: Qxxx # <name>` -> that shrine as the mother house.
  * `AUTOCHTHONOUS:`        -> Q135508874 (Autocthonous shrine). This is a real
    finding, not a null one: the article positively describes an in-situ
    founding with no parent shrine.
  * `UNCLEAR: <note>`       -> recorded in the log, NO statement. The article
    does not settle it, and a guessed mother house is a wrong statement on a
    major shrine — the expensive direction.

GATES. A MOTHER answer is written out only if the target is a syntactically
valid Q-id, is not the subject itself, and is not Q135508874 (which belongs in
the AUTOCHTHONOUS branch). Everything else goes to the log. The collector does
NOT verify that the target is really a shrine — that check needs the network and
this script is deliberately offline; `--verify` opts into a SPARQL pass that
confirms each target is a Shinto shrine before writing.

Usage: python collect_beppyo_p612.py [--dry-run] [--verify]
"""
import argparse
import io
import os
import re
import sys
from shinto_miraheze.ua_contact import contact
from shinto_miraheze.wd_pace import wd_pace, SPARQL_INTERVAL

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)

WORKDIR = os.path.join(ROOT, "beppyo_p612")
QS_OUT = os.path.join(ROOT, "modern-quickstatements", "beppyo_p612.txt")
LOG = os.path.join(WORKDIR, "_resolved.log")

BUNREI = "Q195793"               # criterion used: Bunrei
AUTOCHTHONOUS = "Q135508874"     # Autocthonous shrine

ANSWER_RE = re.compile(r"<!--\s*ANSWER:\s*(.*?)\s*-->", re.S)
QID_RE = re.compile(r"^(Q\d+)\.wiki$")
ARTICLE_RE = re.compile(r"<!--\s*ARTICLE:\s*(\S+)\s*-->")
TARGET_RE = re.compile(r"^(Q\d+)\b")


def parse_answer(text):
    """(kind, payload) from a work-file body, or None while ANSWER is empty."""
    m = ANSWER_RE.search(text)
    if not m or not m.group(1).strip():
        return None
    ans = m.group(1).strip()
    km = re.match(r"(MOTHER|AUTOCHTHONOUS|UNCLEAR)\s*:\s*(.*)", ans, re.S)
    if not km:
        return ("MALFORMED", ans)
    return (km.group(1), km.group(2).strip())


def mother_target(payload, subject):
    """The Q-id a MOTHER answer names, or (None, reason)."""
    m = TARGET_RE.match(payload or "")
    if not m:
        return None, "no Q-id in the answer"
    q = m.group(1)
    if q == subject:
        return None, "names the subject itself"
    if q == AUTOCHTHONOUS:
        return None, "use the AUTOCHTHONOUS answer, not MOTHER"
    return q, ""


def verify_shrines(qids):
    """{qid -> True} for targets that really are Shinto shrines (SPARQL)."""
    import requests
    ok = set()
    uniq = sorted(qids)
    hdr = {"User-Agent": "ShintoWikiBeppyo/1.0 "
                         "(https://github.com/EmmaLeonhart/shintowiki-scripts; "
                         f"{contact('miraheze')})",
           "Accept": "application/sparql-results+json"}
    for i in range(0, len(uniq), 50):
        vals = " ".join("wd:%s" % q for q in uniq[i:i + 50])
        query = ("SELECT ?item WHERE { VALUES ?item { %s } "
                 "?item wdt:P31/wdt:P279* wd:Q845945 }" % vals)
        wd_pace(SPARQL_INTERVAL)
        r = requests.post("https://query-main.wikidata.org/sparql",
                          data={"query": query, "format": "json"},
                          headers=hdr, timeout=120)
        if r.status_code == 429:
            raise SystemExit("429 from WDQS — bailing (CLAUDE.md 429 policy).")
        r.raise_for_status()
        for b in r.json()["results"]["bindings"]:
            ok.add(b["item"]["value"].rsplit("/", 1)[-1])
    return ok


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="SPARQL-confirm each MOTHER target is a Shinto shrine")
    args = ap.parse_args()

    if not os.path.isdir(WORKDIR):
        print("no beppyo_p612/ dir; nothing to collect")
        return

    staged, resolved, done_files = [], [], []
    pending = rejected = 0
    for name in sorted(os.listdir(WORKDIR)):
        qm = QID_RE.match(name)
        if not qm:
            continue
        qid = qm.group(1)
        path = os.path.join(WORKDIR, name)
        body = open(path, encoding="utf-8").read()
        ans = parse_answer(body)
        if ans is None:
            pending += 1
            continue
        kind, payload = ans
        art = ARTICLE_RE.search(body)
        url = art.group(1) if art else ""

        if kind == "MOTHER":
            target, why = mother_target(payload, qid)
            if not target:
                rejected += 1
                resolved.append(f"{qid}\tREJECTED\t{why}: {payload[:80]}")
                done_files.append(path)
                continue
            staged.append((qid, target, url, payload))
        elif kind == "AUTOCHTHONOUS":
            staged.append((qid, AUTOCHTHONOUS, url, payload))
        else:
            resolved.append(f"{qid}\t{kind}\t{payload[:120]}")
        done_files.append(path)

    if args.verify and staged:
        targets = {t for _, t, _, _ in staged if t != AUTOCHTHONOUS}
        print(f"verifying {len(targets)} mother-house targets are shrines...",
              flush=True)
        good = verify_shrines(targets) | {AUTOCHTHONOUS}
        kept = []
        for row in staged:
            if row[1] in good:
                kept.append(row)
            else:
                rejected += 1
                resolved.append(f"{row[0]}\tREJECTED\tnot a Shinto shrine: {row[1]}")
        staged = kept

    qs_lines = [f'{q}|P612|{t}|P1013|{BUNREI}|S854|"{u}"' for q, t, u, _ in staged]
    for q, t, _, payload in staged:
        resolved.append(f"{q}\t{'AUTOCHTHONOUS' if t == AUTOCHTHONOUS else 'MOTHER'}"
                        f"\t{t}\t{payload[:80]}")

    print(f"pending={pending} resolved={len(resolved)} qs-lines={len(qs_lines)} "
          f"rejected={rejected}" + (" [DRY]" if args.dry_run else ""))
    for line in qs_lines[:12]:
        print("   " + line)

    if args.dry_run or not resolved:
        return
    if qs_lines:
        with open(QS_OUT, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(qs_lines) + "\n")
    with open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(resolved) + "\n")
    for p in done_files:
        os.remove(p)
    print(f"appended {len(qs_lines)} QS lines; removed {len(done_files)} work-files")


if __name__ == "__main__":
    main()
