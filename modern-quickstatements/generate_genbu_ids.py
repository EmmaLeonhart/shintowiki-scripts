"""
Entity-resolution → P13930 (Genbu.net ID) from our OWN wiki citations.

genbu.net (a large personal Shinto-shrine/deity database) is already cited as a
reference in many shinto.miraheze.org articles. A human put each of those links on
the shrine's own page, so this is high-precision resolution with no fuzzy matching:

  1. Ask the wiki which mainspace pages link to genbu.net (exturlusage API) + the
     exact URL on each.
  2. Turn each URL into the P13930 id = the path after genbu.net/ minus ".htm"
     (formatter is https://www.genbu.net/$1.htm), e.g.
     http://www.genbu.net/data/izu/tamatukuri_title.htm -> "data/izu/tamatukuri_title".
  3. Map the page title -> its Wikidata QID via P11250 (shinto wiki article).
  4. Emit  QID|P13930|"id"  — add-only, skipping items that already have P13930.

Precision guard: if a page cites MORE THAN ONE distinct genbu.net URL, skip it
(ambiguous which is the page's own id). "Cited on the page" is treated as "the
page's id"; rare cross-references are the residual error, acceptable for an add-only
external id.

Output: modern-quickstatements/genbu_ids.txt
Read-only against the wiki + WDQS; writes only the .txt (the daily drip executes it).
429 from WDQS => bail (repo rule).
"""

import os
import re
import sys
import time
import urllib.parse
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(HERE, "genbu_ids.txt")
SPARQL = "https://query.wikidata.org/sparql"
# Source is the synced *.wiki files, not the live wiki API — shinto.miraheze.org is
# behind a Cloudflare 403; WDQS is unaffected. Covers the synced subset; swap in the
# exturlusage API for full-wiki coverage once the 403 clears.
UA = {"User-Agent": "ShintoWikiGenbu/1.0 (immanuelleleonhart@gmail.com)"}
SPARQL_HDR = dict(UA, **{"Accept": "application/sparql-results+json"})

GENBU_RE = re.compile(r"https?://(?:www\.)?genbu\.net/(.+?)\.htm", re.I)


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


def exturl_pages():
    """{mainspace page title -> set of genbu ids} from the synced *.wiki files."""
    pages = {}
    for dirpath, _dirs, files in os.walk(REPO_ROOT):
        if os.sep + ".git" in dirpath:
            continue
        for fn in files:
            if not fn.endswith(".wiki"):
                continue
            title = urllib.parse.unquote(fn[:-len(".wiki")])
            if ":" in title:           # skip namespaced pages (Category:, Template:, …)
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            for m in GENBU_RE.finditer(text):
                gid = m.group(1).strip("/")
                pages.setdefault(title, set()).add(gid)
    return pages


def p11250_map():
    """{shinto wiki article title -> Wikidata QID}. P11250 values are wiki-prefixed
    (e.g. "shinto:Heda Shrine"); keep only the shinto: ones and strip the prefix."""
    rows = _sparql('SELECT ?item ?t WHERE { ?item wdt:P11250 ?t }')
    out = {}
    for b in rows:
        val = b["t"]["value"]
        if val.startswith("shinto:"):
            out[val[len("shinto:"):]] = b["item"]["value"].rsplit("/", 1)[1]
    return out


def existing_p13930():
    rows = _sparql('SELECT ?item WHERE { ?item wdt:P13930 [] }')
    return {b["item"]["value"].rsplit("/", 1)[1] for b in rows}


def main():
    _utf8()
    pages = exturl_pages()
    print(f"{len(pages)} mainspace pages link to genbu.net", flush=True)
    title_qid = p11250_map()
    print(f"{len(title_qid)} P11250 title->QID mappings", flush=True)
    have = existing_p13930()
    print(f"{len(have)} items already have P13930", flush=True)

    lines, ambiguous, no_qid, already = [], 0, 0, 0
    for title, gids in sorted(pages.items()):
        if len(gids) != 1:
            ambiguous += 1
            continue
        qid = title_qid.get(title)
        if not qid:
            no_qid += 1
            continue
        if qid in have:
            already += 1
            continue
        gid = next(iter(gids))
        lines.append(f'{qid}|P13930|"{gid}"')

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"emit {len(lines)} P13930 statements | ambiguous(skip) {ambiguous} | "
          f"no-QID {no_qid} | already-have {already} -> {OUT}")
    for ln in lines[:8]:
        print("  ", ln)


if __name__ == "__main__":
    main()
