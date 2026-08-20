"""
Entity-resolution → P14391 (Shinmei database ID) for DEITIES.

The Shinmei database (Kokugakuin University god-name DB, ~338 kami) at
kojiki.kokugakuin.ac.jp. P14391's formatter is ?p=$1 (numeric WordPress id), but the
public pages use romaji slugs (/shinmei/<romaji>/) — each page's shortlink exposes
its numeric id (e.g. .../shinmei/akaruhimenokami/ -> ?p=18) and its kanji name in the
<title>.

Pipeline:
  1. Read the index for the ~338 deity slug URLs.
  2. Fetch each page; extract the numeric id (shortlink ?p=N) + kanji name (<title>).
  3. Match kanji name -> our Wikidata item by EXACT ja label or alias. Emit only when
     exactly ONE item matches (skip ambiguous — high precision, some misses).
  4. THEN drop any survivor that is not deity-like, or that is a shrine (DEITY_GATE +
     SHRINE_DENY). Order matters: the gate rejects, it never disambiguates. See the
     note in main() for the two wrong statements the other order produced.
  5. Emit  QID|P14391|"N"  — add-only, skipping items that already have P14391.

Output: modern-quickstatements/shinmei_ids.txt
Also writes _site/shinmei_unmatched.txt — a REPORT of the names that resolve to no
item or to several. Report only; nothing there reaches Wikidata.

THE UNMATCHED TAIL IS IRREDUCIBLE BY NAME MANIPULATION — measured 2026-07-28, do not
re-attempt. queue.md carried "a fuzzy/alias pass could recover more" for the 129
no-match names. Tested directly: generating suffix variants (strip/append 神/命/尊/
大神/之命) over all 129 resolves just 3, and only ONE of the 3 is right —
穴戸神→穴戸 hits Q907382 長門国 (an ancient province) and 大土神→大土 hits Q11571306 犯土
(a calendrical term); only 須勢理毘売→Q8191715 is a real kami. 1-in-3 precision on a
property that is supposed to identify a specific deity is not a trade worth making,
so the relaxation was NOT adopted. The remaining 129 are obscure Kojiki names with no
Wikidata item at all, and the 19 ambiguous ones need a human to choose.

Read-only (kokugakuin + WDQS); writes only the .txt and the report. 429 from WDQS =>
bail. Throttled ~0.4s/page (polite to kokugakuin).
"""

import os
import re
import sys
import time
import html
import requests

from generate_genbu_ids import to_shinjitai   # kyūjitai -> shinjitai normalizer
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_contact import contact

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "shinmei_ids.txt")
REPORT = os.path.join(HERE, "_site", "shinmei_unmatched.txt")
INDEX = "https://kojiki.kokugakuin.ac.jp/shinmei/"
SPARQL = "https://query-main.wikidata.org/sparql"
UA = {"User-Agent": WIKIDATA_USER_AGENT}
SPARQL_HDR = dict(UA, **{"Accept": "application/sparql-results+json"})

SLUG_RE = re.compile(r'href="(https://kojiki\.kokugakuin\.ac\.jp/shinmei/([^"/]+)/)"')
SHORTLINK_RE = re.compile(r"\?p=(\d+)")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _sparql(query):
    for attempt in range(4):
        time.sleep(0.5)
        try:
            r = requests.post(SPARQL, data={"query": query, "format": "json"},
                              headers=SPARQL_HDR, timeout=120)
            if r.status_code == 429:
                raise SystemExit("429 from WDQS — bailing.")
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except SystemExit:
            raise
        except Exception as e:
            print(f"  [WDQS retry {attempt+1}] {e}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("WDQS failed")


def deity_slugs():
    r = requests.get(INDEX, headers=UA, timeout=60)
    r.raise_for_status()
    seen, out = set(), []
    for url, slug in SLUG_RE.findall(r.text):
        if slug in ("feed",) or slug in seen:
            continue
        seen.add(slug)
        out.append(url)
    return out


def scrape(urls):
    """[(kanji_name, numeric_id)] from each deity page."""
    out = []
    for i, u in enumerate(urls, 1):
        time.sleep(0.4)
        try:
            r = requests.get(u, headers=UA, timeout=60)
            r.raise_for_status()
        except Exception as e:
            print(f"  [{i}/{len(urls)}] fetch failed {u}: {e}", flush=True)
            continue
        pid = SHORTLINK_RE.search(r.text)
        title = TITLE_RE.search(r.text)
        if not pid or not title:
            continue
        name = html.unescape(title.group(1)).split("–")[0].split(" - ")[0].strip()
        if name:
            out.append((name, pid.group(1)))
        if i % 50 == 0:
            print(f"  scraped {i}/{len(urls)}", flush=True)
    return out


# Class gate. Its sibling resolver generate_genbu_ids.py has always gated on
# P31/P279* Q845945; this one matched ANY item carrying the label, and that hole
# shipped two category errors into shinmei_ids.txt (audited 2026-07-28, before the
# freeze let them out): Q13987 九州 — the real island, not the Kojiki island-deity —
# and Q11129346 氣比神宮, a SHRINE holding a god-name-database id.
#
# The four allowed classes were chosen by measuring against the 80 already-emitted
# lines: this gate keeps 78 and drops exactly those two. Deity and human are the bulk
# (a god-name DB legitimately lists legendary people like 彦五瀬命, P31=ヒト); mythical
# character keeps ヨモツシコメ (oni), and mythological island keeps オノゴロ島. Gating on
# deity alone would have dropped 7, including four correct ones.
DEITY_GATE = ("{ ?i wdt:P31/wdt:P279* wd:Q178885 } "      # deity
              "UNION { ?i wdt:P31/wdt:P279* wd:Q5 } "      # human
              "UNION { ?i wdt:P31/wdt:P279* wd:Q4271324 } "   # mythical character
              "UNION { ?i wdt:P31/wdt:P279* wd:Q33513999 }")  # mythological island
# Even inside the gate, a SHRINE is never the referent of a god-name entry. 座摩神
# (Q10928586) is typed BOTH 神 and 神社/式内社, so the allow-gate alone admitted it.
SHRINE_DENY = "FILTER NOT EXISTS { ?i wdt:P31/wdt:P279* wd:Q845945 }"


def gate_pass(qids):
    """Subset of `qids` that are deity-like and not shrines.

    Applied AFTER uniqueness, never as part of the label lookup — see the note in
    main(). Fault-tolerant per chunk: a failed chunk keeps nothing, which errs toward
    emitting less.
    """
    keep, uniq = set(), sorted(qids)
    for i in range(0, len(uniq), 40):
        vals = " ".join("wd:%s" % q for q in uniq[i:i + 40])
        try:
            rows = _sparql("SELECT DISTINCT ?i WHERE { VALUES ?i { %s } %s %s }"
                           % (vals, DEITY_GATE, SHRINE_DENY))
        except Exception as e:
            print(f"  [gate chunk {i//40} skipped] {e}", flush=True)
            continue
        for b in rows:
            keep.add(b["i"]["value"].rsplit("/", 1)[1])
    return keep


def label_to_qids(names):
    """{ja name -> [QIDs]} matching an item's ja label OR ja alias (kami carry many
    name variants as aliases). UNGATED on purpose. Fault-tolerant per chunk."""
    out = {}
    uniq = sorted(set(names))
    for i in range(0, len(uniq), 50):
        chunk = uniq[i:i + 50]
        values = " ".join('"%s"@ja' % n.replace('\\', '\\\\').replace('"', '\\"') for n in chunk)
        try:
            rows = _sparql(
                "SELECT ?i ?lab WHERE { VALUES ?lab { %s } "
                "?i (rdfs:label|skos:altLabel) ?lab }" % values)
        except Exception as e:
            print(f"  [chunk {i//50} skipped] {e}", flush=True)
            continue
        for b in rows:
            out.setdefault(b["lab"]["value"], []).append(b["i"]["value"].rsplit("/", 1)[1])
    return out


def existing_p14391():
    rows = _sparql('SELECT ?i WHERE { ?i wdt:P14391 [] }')
    return {b["i"]["value"].rsplit("/", 1)[1] for b in rows}


def main():
    _utf8()
    urls = deity_slugs()
    print(f"{len(urls)} deity pages in the Shinmei index", flush=True)
    entries = scrape(urls)
    print(f"scraped {len(entries)} (name, id) pairs", flush=True)

    all_forms = set()
    for name, _ in entries:
        all_forms.add(name)
        all_forms.add(to_shinjitai(name))
    lab_qids = label_to_qids(all_forms)
    have = existing_p14391()

    lines, ambiguous, nomatch, already = [], 0, 0, 0
    unmatched, ambiguous_names = [], []
    candidates, gate_rejected = [], []
    for name, pid in entries:
        qids = set()
        for form in (name, to_shinjitai(name)):
            qids.update(lab_qids.get(form, []))
        if not qids:
            nomatch += 1
            unmatched.append((name, pid))
            continue
        if len(qids) > 1:
            ambiguous += 1
            ambiguous_names.append((name, pid, sorted(qids)))
            continue
        qid = next(iter(qids))
        if qid in have:
            already += 1
            continue
        candidates.append((qid, pid, name))

    # THE GATE REJECTS; IT NEVER DISAMBIGUATES. Applying it inside the label lookup
    # was tried on 2026-07-28 and made things worse: it narrowed two names that had
    # been safely skipped as ambiguous down to a single, WRONG item — 阿須波神 to
    # 座摩神 (a shrine that is also typed 神) and 天之狭霧神 to オオヤマツミ, who is
    # Ame-no-Sagiri's parent, not Ame-no-Sagiri. It preferred the richly-typed item
    # over the correct one, converting "skip, a human must choose" into a confident
    # error. So ambiguity is settled FIRST, on the ungated candidate set, and the gate
    # only ever removes a survivor. It costs ~6 correct alias matches that gate
    # disambiguation would have found; per CLAUDE.md, data loss beats a visible wrong
    # statement.
    ok = gate_pass({q for q, _p, _n in candidates})
    for qid, pid, name in candidates:
        if qid not in ok:
            gate_rejected.append((name, pid, qid))
            continue
        lines.append(f'{qid}|P14391|"{pid}"')

    # de-dup (a QID matching two names would be a data problem; keep first)
    seen, uniq = set(), []
    for ln in lines:
        q = ln.split("|", 1)[0]
        if q in seen:
            continue
        seen.add(q)
        uniq.append(ln)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(uniq) + "\n")
    print(f"emit {len(uniq)} P14391 | ambiguous(skip) {ambiguous} | no-match {nomatch} | "
          f"already {already} | gate-rejected {len(gate_rejected)} -> {OUT}")
    for ln in uniq[:8]:
        print("  ", ln)

    # Diagnostic dump, not a queue: the no-match tail is the only place further
    # coverage can come from, and it is impossible to judge which matching rule
    # would be SAFE to add without seeing the actual names that miss. Report-only —
    # nothing here is emitted to Wikidata.
    with open(REPORT, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Shinmei DB entries with no single Wikidata item, %d no-match + "
                "%d ambiguous.\n" % (nomatch, ambiguous))
        f.write("# Regenerated by generate_shinmei_ids.py. Report only.\n\n")
        f.write("## no label/alias match (%d)\n" % nomatch)
        for name, pid in unmatched:
            f.write(f"{name}\t{pid}\n")
        f.write("\n## ambiguous — name matches several items (%d)\n" % ambiguous)
        for name, pid, qs in ambiguous_names:
            f.write(f"{name}\t{pid}\t{' '.join(qs)}\n")
        # The gate's rejections are listed, not just counted: a wrongly-rejected
        # entry is invisible otherwise, and this is the section to read first if
        # coverage ever drops unexpectedly.
        f.write("\n## unique match REJECTED by the deity/non-shrine gate (%d)\n"
                % len(gate_rejected))
        for name, pid, qid in gate_rejected:
            f.write(f"{name}\t{pid}\t{qid}\n")
    print(f"  wrote the unmatched tail -> {REPORT}")


if __name__ == "__main__":
    main()
