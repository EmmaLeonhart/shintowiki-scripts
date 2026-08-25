"""Read the numbered 論社 candidates off a Kokugakuin Digital Museum entry page.

Emma, 2026-08-25, on the P958 reading queue: *"grind it."* This is the reader that makes the
grinding possible. It does not decide anything — it reports what the page says.

**What a page states.** Each 式内社データベース entry lists its candidate shrines as numbered
slots, rendered as plain table rows:

    <th>+現社名など（１）</th><td>本宮神社境外末社日御崎神社</td>
    <th>+現社名など（２）</th><td>佐久多神社</td>

That number IS the `P958` section, and it is what `P1352` records on the link statement. It exists
nowhere else, which is why this has always been a reading job rather than a derivation.

**Why parsing this is reading and not guessing.** The dangerous version of "match a shrine to a
name" is a global search — that is how an earlier pass produced false positives against jawiki
titles. Here the candidate set is **closed and tiny**: 2–5 names belonging to one specific entry.
A match is against that entry's own stated candidates, nothing wider.

**Exact match only, and ties defer.** `resolve()` returns a section only when exactly one candidate
string equals the item's label after normalisation. Two candidates matching, or none, returns
`None` — the same direction `resolve_multi_p13677` already takes, because attaching a section
number to the wrong candidate is worse than attaching none.

**Saved, not merely cached.** `kokugakuin_pages/` holds one file per entry id and is **committed**
— Emma, 2026-08-25: *"you can save pages from that site."* So the site is fetched once per entry
ever, the parse can be re-run and audited offline against exactly the bytes a section was read
from, and the evidence for a `P958` value outlives the page. Requests are paced at `READ_INTERVAL`;
this is a small museum site, not Wikidata.

**No browser needed.** Emma, same day: *"so no need to browser stuff."* The candidate slots are in
the raw HTML — a plain `urlopen` gets them, with no JavaScript rendering and no Playwright. The
standing fallback-to-Playwright rule is for pages whose content is not in the source; this is not
one of them, and reaching for a browser here would be cost with no return.

Usage:
    python modern-quickstatements/kokugakuin_candidates.py 182811 181621
"""
import io
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
from shinto_miraheze.wd_pace import wd_pace, READ_INTERVAL

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "kokugakuin_pages")
DET = "https://jmapps.ne.jp/kokugakuin/det.html?data_id="

# 現社名など（１）… the slot number is full-width. （０）is not used; slots start at 1.
FULLWIDTH = "０１２３４５６７８９"
SLOT = re.compile(
    r"<th>\+?現社名など（([０-９]+)）</th>\s*<td>(.*?)</td>", re.S)


def _digits(fw):
    return "".join(str(FULLWIDTH.index(ch)) for ch in fw)


def normalise(name):
    """Compare shrine names without punctuation/width/spacing noise.

    Deliberately conservative: NFKC, drop whitespace and the bracketed disambiguators
    Wikidata labels carry (`両神社 (下田市)`), nothing else. No suffix stripping, no
    character substitution — those are the transformations that manufacture false matches.
    """
    if not name:
        return ""
    n = unicodedata.normalize("NFKC", name)
    n = re.sub(r"[（(][^）)]*[）)]", "", n)
    n = re.sub(r"\s+", "", n)
    return n.strip()


def fetch(kid, refresh=False):
    """Raw HTML for one entry page, cached on disk."""
    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    path = os.path.join(CACHE, "%s.html" % kid)
    if os.path.exists(path) and not refresh:
        return io.open(path, encoding="utf-8").read()
    req = urllib.request.Request(DET + str(kid),
                                 headers={"User-Agent": WIKIDATA_USER_AGENT})
    wd_pace(READ_INTERVAL)
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", "replace")
    io.open(path, "w", encoding="utf-8", newline="\n").write(body)
    return body


def candidates(kid, refresh=False):
    """{section: name} for one entry, e.g. {'1': '本宮神社境外末社日御崎神社', '2': '佐久多神社'}."""
    body = fetch(kid, refresh=refresh)
    out = {}
    for fw, raw in SLOT.findall(body):
        name = re.sub(r"<[^>]+>", "", raw).strip()
        if name:
            out[_digits(fw)] = name
    return out


def resolve(kid, label, refresh=False):
    """(section, why) — the section this label occupies on this entry, or None.

    Exact normalised equality against that entry's own candidates. Ambiguity defers.
    """
    cands = candidates(kid, refresh=refresh)
    if not cands:
        return None, "page lists no candidates"
    target = normalise(label)
    if not target:
        return None, "item has no usable label"
    hits = [s for s, n in cands.items() if normalise(n) == target]
    if len(hits) == 1:
        return hits[0], "exact match against %d candidate(s)" % len(cands)
    if len(hits) > 1:
        return None, "label matches %d slots (%s) — ambiguous" % (len(hits), ",".join(sorted(hits)))
    return None, "no exact match among %d candidate(s): %s" % (
        len(cands), " / ".join(cands[s] for s in sorted(cands)))


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    for kid in sys.argv[1:] or ["182811"]:
        cs = candidates(kid)
        print("%s — %d candidate(s)" % (kid, len(cs)))
        for s in sorted(cs, key=int):
            print("   (%s) %s" % (s, cs[s]))
