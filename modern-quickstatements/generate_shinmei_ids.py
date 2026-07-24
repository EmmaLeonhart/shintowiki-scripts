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
  3. Match kanji name -> our Wikidata item by EXACT ja label; emit only when exactly
     ONE item carries that ja label (skip ambiguous — high precision, some misses).
  4. Emit  QID|P14391|"N"  — add-only, skipping items that already have P14391.

Output: modern-quickstatements/shinmei_ids.txt
Read-only (kokugakuin + WDQS); writes only the .txt. 429 from WDQS => bail.
Throttled ~0.4s/page (polite to kokugakuin).
"""

import os
import re
import sys
import time
import html
import requests

from generate_genbu_ids import to_shinjitai   # kyūjitai -> shinjitai normalizer

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "shinmei_ids.txt")
INDEX = "https://kojiki.kokugakuin.ac.jp/shinmei/"
SPARQL = "https://query.wikidata.org/sparql"
UA = {"User-Agent": "ShintoWikiShinmei/1.0 (immanuelleleonhart@gmail.com)"}
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


def label_to_qids(names):
    """{ja name -> [QIDs]} matching an item's ja label OR ja alias (kami carry many
    name variants as aliases). Fault-tolerant per chunk."""
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
    for name, pid in entries:
        qids = set()
        for form in (name, to_shinjitai(name)):
            qids.update(lab_qids.get(form, []))
        if not qids:
            nomatch += 1
            continue
        if len(qids) > 1:
            ambiguous += 1
            continue
        qid = next(iter(qids))
        if qid in have:
            already += 1
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
          f"already {already} -> {OUT}")
    for ln in uniq[:8]:
        print("  ", ln)


if __name__ == "__main__":
    main()
