#!/usr/bin/env python3
"""
generate_honzon_quickstatements.py
===================================
Import 本尊 (principal image / main object of veneration) from the jawiki
{{日本の寺院}} temple infobox onto Wikidata as P825 (dedicated to) — the temple
sibling of generate_saijin_quickstatements.py, from
`docs/jawiki_infobox_import_review_2026-07.md`.

HIGH-PRECISION design — no name-matching, no guessing:
  * only deities that are WIKILINKED in the 祭神 field are imported;
  * each link target resolves to its Wikidata item via jawiki's own
    pageprops (wikibase_item), following redirects — jawiki's editorial
    linking is the identification, we never match by string;
  * unlinked plain-text deity names are counted and skipped;
  * (shrine, deity) pairs already on Wikidata are skipped (SPARQL set).

A parenthetical FORM in the field — 「[[阿弥陀如来]]（[[秘仏]]）」 — is not a
second honzon. Emma, 2026-09-13: *"hibitsu and buddharupa are qualifiers"*,
*"qualifiers on the other thing"*. It is emitted as a P3831 qualifier on the deity
it follows, inline when that statement is being created and as a qualifier-only
enrichment line when it already exists. See IMAGE_FORM_ROOTS.

Output: honzon_p825.txt — atomic cited lines
    <shrine>|P825|<deity>|S143|Q177837|S4656|"<jawiki url>"
    <shrine>|P825|<deity>|P3831|<form>|S143|Q177837|S4656|"<jawiki url>"
    <shrine>|P825|<deity>|P3831|<form>                     (enrichment, no value created)

Usage:
    python generate_honzon_quickstatements.py             # full run
    python generate_honzon_quickstatements.py --limit 200 # sample
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import argparse
import collections
import io
import os
import re

import sys
import time
import urllib.parse

import requests

from infobox_fields import field_pattern

# Plain module import, matching the other adopters — test_wdqs_transport.py checks
# for exactly this line as the evidence a file has not grown its own client back.
import wdqs_transport

HERE = os.path.dirname(os.path.abspath(__file__))
JA_API = "https://ja.wikipedia.org/w/api.php"
# The class check below asks Wikidata, not jawiki, so _get takes an endpoint.
WD_API = "https://www.wikidata.org/w/api.php"
# The SPARQL endpoint and its Accept header moved into wdqs_transport with the
# transport itself. UA stays: the ja.wikipedia and Wikidata API calls still use it.
UA = WIKIDATA_USER_AGENT
TEMPLATE = "Template:日本の寺院"
OUTPUT = os.path.join(HERE, "honzon_p825.txt")

# Same ordered-alternation defect as 祭神: `[^\n|]` halted at the pipe inside the
# first piped wikilink, dropping every later 本尊. See infobox_fields.py.
# ⛔ A honzon is a DEITY. Refuse any resolved target whose Wikidata class says it
# is a heritage designation instead.
#
# Emma, 2026-09-12, first on Q1188622: "a completely invalid thing and we should
# never add it and should universally remove it from all items it is present on."
# Then, when the same error turned up twice more, on whether to keep naming QIDs:
# "Block the whole class instead."
#
# P825 is "dedicated to". Q1188622 is 重要文化財 and Q1139795 is 国宝 — both
# designations the Agency for Cultural Affairs awards to an object, and both
# P31 = Q30634609 heritage designation. "Dedicated to National Treasure" asserts
# nothing.
#
# They get in because this generator takes EVERY wikilink in the 本尊 field, and
# temple infoboxes write the designation beside the deity:
#     |本尊 = [[阿弥陀如来]]（[[重要文化財]]）
#
# MEASURED before choosing the class, over all 118 distinct values this generator
# emits: Q30634609 contains exactly ONE of them, Q1139795, at 23 lines. Nothing
# legitimate is in it. The neighbouring classes were checked and deliberately NOT
# blocked, because each holds real honzon —
#   Q23847174 religious concept : 曼荼羅, 仏舎利, and Bodhisattva itself
#   Q80071     symbol           : 曼荼羅
#   Q838948    work of art      : Q1410999 大曼荼羅, Nichiren's own Gohonzon
#   Q3658341   literary character: 地蔵菩薩, 文殊菩薩, 普賢菩薩 …
#
# ⚠ 秘仏 hibutsu is NOT one of these and is not refused — it is MOVED. See
# IMAGE_FORM_ROOTS below.
# The root of the class, reached by P279 ONLY. Two wrong versions came first:
#   * P31 = Q30634609 alone caught 2 of the 4 — Q858308 (日本の文化財) and
#     Q2901860 (有形文化財) carry no P31 at all.
#   * (P31|P279)/P279* to Q2065736 cultural property caught all four AND 42
#     legitimate statements, because "instance of a cultural property" is true of
#     every listed building: Holy Sepulchre (31), its church, Santa Maria sopra
#     Minerva, Portiuncula, the Warsaw Ghetto.
# Subclass-only, rooted at the Japanese designation family, draws it exactly:
#     Q1139795 国宝 -P279-> Q1188622 -P279-> Q2901860 -P279-> Q858308
#
# ⭐ It does NOT reach 秘仏 (Q11595955 -P279-> Q1000809 Buddharupa -P279-> statue),
# 仏像, or Q101659 dolmen — a monument type that subclasses cultural property
# without being a designation. The chain draws the line; a session does not. The
# first two are handled by IMAGE_FORM_ROOTS below, which is a different remedy,
# not a second blocklist.
INVALID_HONZON_ROOTS = {
    "Q858308",     # Cultural Property of Japan 日本の文化財, and every subclass
}

# ⭐ NOT invalid — MISPLACED. Emma, 2026-09-13: *"hibitsu and buddharupa are
# qualifiers"*, and then *"qualifiers on the other thing"*. A temple infobox writes
#
#     |本尊 = [[阿弥陀如来]]（[[秘仏]]）
#
# and the parenthetical is not a second honzon, it is the FORM the honzon takes.
# So it belongs on the deity's own P825 statement as a qualifier, not beside it as
# a value — the same parse damage as 重要文化財 above, with a different remedy:
# that one is meaningless and goes, this one is true and moves.
#
# Rooted at 仏像 Buddharupa and walked by P279, exactly like the designation root.
# Checked against all 115 distinct values in the file, 2026-09-13: it reaches four,
# and every one is a form rather than a deity — 秘仏 hibutsu (53 lines), 仏像 itself
# (7), 涅槃仏 Reclining Buddha (1), 磨崖仏 magaibutsu (1). No buddha or bodhisattva
# is under it: 阿弥陀 and 藥師 are P31 Q7055, 観音 is P31 Q178149, and P31 is not
# walked here for the reason recorded above.
IMAGE_FORM_ROOTS = {
    "Q1000809",    # 仏像 Buddharupa — a statue, and every subclass of one
}

# "object has role" — the role or generic identity of the value of a statement,
# which is what 秘仏 is to the 阿弥陀 it qualifies. Same property the festival
# model uses for the Reisai role on P837 (docs/wikidata_shrine_festival_model.md).
FORM_QUALIFIER = "P3831"

MAX_CLASS_DEPTH = 6


def refused_classes(qids, roots=None):
    """{qid} whose P279 ancestry reaches one of `roots` (default: the invalid ones).

    Walks upward in batches rather than asking SPARQL, so this script keeps its
    one dependency (the two MediaWiki APIs) and costs a handful of requests.
    """
    # `P279*` includes zero steps, so a target that IS a root counts. The first
    # version only looked at parents and let Q858308 itself through — caught by
    # the nine-case check, not by reading.
    roots = INVALID_HONZON_ROOTS if roots is None else roots
    blocked = {q for q in qids if q in roots}
    seen = set()
    frontier = {q for q in qids if q}
    origin = {q: {q} for q in frontier}          # ancestor -> which targets it came from
    for _ in range(MAX_CLASS_DEPTH):
        frontier = {q for q in frontier if q not in seen}
        if not frontier:
            break
        seen |= frontier
        parents = {}
        batch = sorted(frontier)
        for i in range(0, len(batch), 50):
            d = _get({"action": "wbgetentities", "props": "claims",
                      "ids": "|".join(batch[i:i + 50])}, api=WD_API)
            for qid, ent in (d.get("entities") or {}).items():
                claims = ent.get("claims") or {}
                # P279 ONLY. Adding P31 means "the value is an instance of a
                # cultural property", which is true of every listed building —
                # it swept up Holy Sepulchre, its church, and the Warsaw Ghetto.
                for prop in ("P279",):
                    for c in claims.get(prop, []):
                        v = c["mainsnak"].get("datavalue", {}).get("value", {})
                        if isinstance(v, dict) and v.get("id"):
                            parents.setdefault(qid, set()).add(v["id"])
            time.sleep(0.3)
        nxt = set()
        for qid, ps in parents.items():
            src = origin.get(qid, set())
            for parent in ps:
                if parent in roots:
                    blocked |= src
                else:
                    origin.setdefault(parent, set()).update(src)
                    nxt.add(parent)
        frontier = nxt
    return blocked


_FIELD_RE = re.compile(field_pattern("本尊"))
_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def _get(params, api=None):
    """One ja.wikipedia (or Wikidata) API call, retried three times.

    `requests` rather than a raw urlopen, matching the other adopters: this file's
    SPARQL now goes through `wdqs_transport`, and `test_wdqs_transport.py` reads a
    hand-rolled urlopen anywhere in an adopter as evidence it regrew its own WDQS
    client. Behaviour is unchanged — same params, same UA, same three attempts.
    """
    params = dict(params)
    params["format"] = "json"
    for attempt in range(3):
        try:
            r = requests.get(api or JA_API, params=params,
                             headers={"User-Agent": UA}, timeout=60)
            if r.status_code == 429:
                raise SystemExit("429 from the MediaWiki API — bailing.")
            r.raise_for_status()
            return r.json()
        except SystemExit:
            raise
        except Exception:
            if attempt == 2:
                raise
            time.sleep(4)


def temple_titles():
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "embeddedin", "eititle": TEMPLATE,
             "einamespace": 0, "eilimit": "max"}
        if cont:
            p["eicontinue"] = cont
        d = _get(p)
        titles += [e["title"] for e in d.get("query", {}).get("embeddedin", [])]
        cont = d.get("continue", {}).get("eicontinue")
        if not cont:
            break
        time.sleep(0.3)
    return titles


def fetch_batch(titles):
    d = _get({"action": "query", "prop": "revisions|pageprops", "rvprop": "content",
              "rvslots": "main", "ppprop": "wikibase_item",
              "titles": "|".join(titles), "redirects": 1})
    out = []
    for p in d.get("query", {}).get("pages", {}).values():
        if "missing" in p:
            continue
        qid = p.get("pageprops", {}).get("wikibase_item")
        revs = p.get("revisions", [])
        text = revs[0]["slots"]["main"]["*"] if revs else ""
        out.append((p["title"], qid, text))
    return out


def resolve_links(titles):
    """{jawiki title -> wikidata QID} for deity link targets (redirects followed)."""
    out = {}
    titles = sorted(titles)
    for i in range(0, len(titles), 50):
        d = _get({"action": "query", "prop": "pageprops", "ppprop": "wikibase_item",
                  "titles": "|".join(titles[i:i + 50]), "redirects": 1})
        qy = d.get("query", {})
        remap = {}
        for r in qy.get("normalized", []) + qy.get("redirects", []):
            remap[r["from"]] = r["to"]
        final = {}
        for t in titles[i:i + 50]:
            ft = t
            seen = set()
            while ft in remap and ft not in seen:
                seen.add(ft)
                ft = remap[ft]
            final[t] = ft
        by_title = {p["title"]: p.get("pageprops", {}).get("wikibase_item")
                    for p in qy.get("pages", {}).values() if "missing" not in p}
        for t, ft in final.items():
            if by_title.get(ft):
                out[t] = by_title[ft]
        time.sleep(0.3)
    return out


def _pairs(rows):
    return {(b["s"]["value"].rsplit("/", 1)[-1], b["d"]["value"].rsplit("/", 1)[-1])
            for b in rows}


def existing_pairs():
    """Every (temple, honzon) P825 pair. COUNT ONLY — not the skip set.

    ⚠ The `if r.status == 429` check this used to carry, after a SUCCESSFUL
    urlopen, was dead code: urllib raises `HTTPError` on a 429 and never returns a
    response to test. The transport bails on it properly.
    """
    return _pairs(wdqs_transport.query(
        "SELECT ?s ?d WHERE { ?s wdt:P31 wd:Q5393308 ; wdt:P825 ?d . }"))


def referenced_pairs():
    """(temple, honzon) pairs whose P825 statement ALREADY carries a reference.

    ⛔ THIS IS THE SKIP SET, not `existing_pairs()`. The shrine half of the same
    property was fixed on 2026-09-15 for exactly this: skipping every pair that
    merely exists means a statement that landed bare can never be given the
    reference, because this generator is the only thing that knows which
    ja.wikipedia article named the deity.

    Temple P825 is in far better shape than the shrine half — 6,173 of 6,380
    referenced, because we built nearly all of it ourselves from 本尊 with the
    citation attached. So this closes a ratchet rather than recovering a
    population: the 207 bare ones become reachable, and future runs stop locking
    in their own.

    Re-emitting does not duplicate: QuickStatements matches the existing
    (item, property, value) and attaches the reference to that statement. A form
    qualifier seen later in the same field is then inlined on that line instead of
    needing the separate qualifier-only shape, which is the same edit either way.
    """
    return _pairs(wdqs_transport.query("""
      SELECT ?s ?d WHERE {
        ?s wdt:P31 wd:Q5393308 ; p:P825 ?st .
        ?st ps:P825 ?d .
        ?st prov:wasDerivedFrom ?ref .
      }
    """))


def emit_for_temple(lines, counts, qid, url, links, resolved, refused, forms, referenced):
    """Append this temple's QuickStatements to `lines`, tallying into `counts`.

    `lines` holds [head, source-tail] pairs so a qualifier can still be inserted
    between the value and its references — house style is value|qualifier|source,
    as in reisai.txt.

    ⭐ The field is read IN ORDER, and that is the whole of the rule. A temple
    infobox writes 「[[阿弥陀如来]]（[[秘仏]]）」, so a form qualifies the deity most
    recently seen in the same field. Emma, 2026-09-13: *"hibitsu and buddharupa
    are qualifiers"*, *"qualifiers on the other thing"*.

    Three cases for a form, and the second is the one that carries most of the
    value here:

    * the deity's statement is being created now → the qualifier goes inline;
    * the deity's statement already exists → a qualifier-only enrichment line,
      which is the case for every temple whose honzon has already landed;
    * no deity precedes it → nothing to attach to, so it is dropped and counted
      rather than guessed at.
    """
    pending = None                 # (deity qid, index into `lines`, or None if extant)
    for t in links:
        d = resolved.get(t)
        if not d:
            continue
        if d in refused:
            counts["invalid"] += 1
            continue
        if d in forms:
            if pending is None:
                counts["orphan_form"] += 1
                continue
            deity, idx = pending
            if idx is None:
                # Emma, 2026-09-11, on generators that create but never enrich:
                # *"the updating of the existing ones to add more to them is kind
                # of a very critical part that makes it so that this work is
                # productive."*
                lines.append([f"{qid}|P825|{deity}|{FORM_QUALIFIER}|{d}", ""])
            else:
                lines[idx][0] += f"|{FORM_QUALIFIER}|{d}"
            counts["qualified"] += 1
            continue
        if (qid, d) in referenced:
            # Already cited, so there is nothing to add — but it EXISTS, so a form
            # seen later in the same field still has a statement to qualify, via
            # the qualifier-only branch above.
            counts["dup"] += 1
            pending = (d, None)
            continue
        lines.append([f"{qid}|P825|{d}", f'|S143|Q177837|S4656|"{url}"'])
        pending = (d, len(lines) - 1)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    have = existing_pairs()
    referenced = referenced_pairs()
    print(f"{len(have)} existing (temple, honzon) P825 pairs on Wikidata; "
          f"{len(referenced)} referenced, "
          f"{len(have - referenced)} bare and reachable for enrichment")
    titles = temple_titles()
    if args.limit:
        titles = titles[:args.limit]
    print(f"{len(titles)} jawiki temple articles")

    # pass 1: parse fields, collect linked deity targets
    shrine_deities = {}     # (shrine_title, shrine_qid) -> [deity jawiki titles]
    unlinked = no_field = no_qid = 0
    for i in range(0, len(titles), 50):
        for title, qid, text in fetch_batch(titles[i:i + 50]):
            m = _FIELD_RE.search(text or "")
            if not m or not m.group(1).strip():
                no_field += 1
                continue
            if not qid:
                no_qid += 1
                continue
            links = [t.strip() for t in _LINK_RE.findall(m.group(1))
                     if t.strip() and not t.startswith(("File:", "ファイル:", "Category:"))]
            plain = _LINK_RE.sub("", m.group(1))
            if re.search(r"[一-龠ぁ-んァ-ヶ]{2,}", plain):
                unlinked += 1   # field also has unlinked names — those are skipped
            if links:
                shrine_deities[(title, qid)] = links
        time.sleep(0.3)
    print(f"{len(shrine_deities)} temples with linked honzon "
          f"(no-field={no_field}, no-QID={no_qid}, fields-with-unlinked-names={unlinked})")

    # pass 2: resolve deity link targets to QIDs
    all_targets = {t for links in shrine_deities.values() for t in links}
    resolved = resolve_links(all_targets)
    print(f"{len(resolved)}/{len(all_targets)} deity link targets resolve to Wikidata items")

    refused = refused_classes(set(resolved.values()))
    print(f"{len(refused)} resolved target(s) refused as a heritage designation")
    forms = refused_classes(set(resolved.values()), roots=IMAGE_FORM_ROOTS)
    print(f"{len(forms)} resolved target(s) are an image FORM -> {FORM_QUALIFIER} qualifier")

    # Each new statement is held as [head, source] so a qualifier can still be
    # inserted between them. House style is value|qualifier|source (see reisai.txt),
    # and while direct_daily_edits sorts trailing P/S pairs either way round,
    # matching the shape everything else in this directory uses is worth the list.
    lines, counts = [], collections.Counter()
    for (title, qid), links in sorted(shrine_deities.items()):
        url = "https://ja.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        emit_for_temple(lines, counts, qid, url, dict.fromkeys(links),
                        resolved, refused, forms, referenced)
    lines = sorted({head + tail for head, tail in lines})
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print(f"{len(lines)} P825 lines -> {OUTPUT} "
          f"(already-present pairs skipped: {counts['dup']}, "
          f"invalid honzon refused: {counts['invalid']}, "
          f"form qualifiers attached: {counts['qualified']}, "
          f"forms with no deity to attach to: {counts['orphan_form']})")


if __name__ == "__main__":
    main()
