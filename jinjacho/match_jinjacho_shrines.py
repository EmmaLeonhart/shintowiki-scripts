"""
Resolve crawled 神社庁 shrine records -> Wikidata QIDs.

Input  : jinjacho/crawled_shrines.csv        (crawl_jinjacho_shrines.py)
Output : jinjacho/crawled_shrines_matched.csv — SAME columns as the hand-built
         jinjacho/shrines_and_websites.csv (shrine, shrineLabel, website), so
         generate_jinjacho_p973.py reads both with one extra path.

Deliberately a SEPARATE script from the crawl: a fetch failure and a bad entity
match are different failures, and re-running the resolution must not re-hit the
prefectural sites.

PRECISION POLICY (the same one genbu/shinmei use, and it matters more here)
--------------------------------------------------------------------------
Shrine names are heavily repeated — a single prefecture holds dozens of 八幡神社
and 神明神社. So a name alone can never identify an item. A row is emitted only when:

  1. the crawled name matches the ja label OR ja alias of a Shinto-shrine item
     (P31/P279* Q845945), in its raw form or its shinjitai normalisation, AND
  2. exactly ONE such item is located in the MUNICIPALITY the crawled address names
     (the item's P131* ancestors include something whose ja label is that 市/区/町/村).

WHY THE MUNICIPALITY AND NOT THE PREFECTURE. The first version gated on prefecture
and was wrong about 2 of its first 5 matches: a 天満神社 crawled in 大垣市 was matched
to 天満神社 (高山市), and a 白髭神社 in 大垣市墨俣町 to 白鬚神社 in 各務原市. Both are
real, distinct shrines that merely share a name, and each was the ONLY item of that
name in Gifu — so "unique within the prefecture" happily attached the URL to the wrong
shrine. A prefecture holds hundreds of municipalities and the same names recur in
each; the address the page already gives us is the discriminator, so use it.

Everything else — no match, no candidate in that municipality, two candidates in it,
or an address we cannot parse a municipality out of — is dropped and counted. Missing
a shrine costs nothing; attaching a Gifu URL to the wrong 八幡神社 is a wrong statement
on Wikidata, which is the expensive direction.

Nothing here writes to Wikidata. The output CSV feeds the QuickStatements
generator, which is the only path (CLAUDE.md "Wikidata editing").

Usage
-----
    python match_jinjacho_shrines.py            # report, write the CSV
    python match_jinjacho_shrines.py --dry-run  # report only
"""

import os
import re
import csv
import sys
import argparse
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "modern-quickstatements"))

from generate_genbu_ids import (            # noqa: E402
    shrine_label_qids, to_shinjitai, _sparql,
)

IN_CSV = os.path.join(HERE, "crawled_shrines.csv")
OUT_CSV = os.path.join(HERE, "crawled_shrines_matched.csv")
ENTITY = "http://www.wikidata.org/entity/%s"

# 大垣市 / 高山市 / 各務原市 / 安八郡安八町 / 東秩父村 / さいたま市大宮区 ...
#
# REWRITTEN 2026-08-03 after the Mie yield (17 matched from 300 crawled) was
# traced here rather than to the data. The previous version used three loose
# regexes and silently mis-parsed a whole class of ordinary addresses. Measured
# failures, all real rows in crawled_shrines.csv:
#
#   四日市市三滝町1-1       -> '四日市'  a non-greedy token stops at the FIRST 市, and
#                                      Yokkaichi's name ends in one. Same for
#                                      廿日市市, 野々市市, 市原市.
#   鈴鹿市国府町 1609       -> ''       `^.{2,4}?[都道府県]` is not anchored to a real
#   豊川市国府町的場19      -> ''       prefecture, so it ate '鈴鹿市国府' — any address
#   藤井寺市道明寺1-16-40   -> ''       through a 国府町 / 道明寺 loses its city.
#   霧島市国分郡田1730      -> ''       `^.{1,5}?郡` ate '霧島市国分郡' — 国分 is part of
#                                      the place name, not a district prefix.
#
# Every one of these failed CLOSED (no municipality -> row dropped), so they cost
# coverage rather than producing wrong statements. The rewrite keeps that
# property: anything unparsed still returns ''.
#
# The token rule itself is UNCHANGED — first 市/区/町/村 token — because the
# alternatives do not work and were tried:
#
#   "extend across a doubled mark" turns 近江八幡市市井町 into 近江八幡市市 (the
#   next unit is 市井町, a locality that starts with 市) and 日野町村井 into 日野町村.
#   "a 市 anywhere outranks 町/村" turns 寄居町今市 into 寄居町今市 and 七宗町神渕高市場
#   into 七宗町神渕高市 — 町 municipalities whose sub-locality contains 市.
#
# 四日市市三滝町 and 近江八幡市市井町 are the same shape (X市 + 市Y町) and cannot be
# told apart without knowing which strings are municipality names. So the handful
# of municipalities whose own name ends in a mark are listed explicitly below.
# The list is NOT exhaustive, and that is safe: an unlisted one truncates exactly
# as before and its row is dropped, never mismatched.
# A spurious entry here fails CLOSED, which is why the list is safe to grow by
# hand: if a string is not really a municipality, no item's P131 ancestor carries
# that label, so the row matches nothing instead of matching wrongly.
_MUNI_OVERRIDES = (
    "四日市市",       # 三重 — 市 inside the name
    "廿日市市",       # 広島
    "野々市市",       # 石川
    "武蔵村山市",     # 東京 — 村 inside the name
    "東村山市",       # 東京
    "十日町市",       # 新潟 — 町 inside the name
    "大町市",         # 長野
    "大村市",         # 長崎
    "田村市",         # 福島
    "大町町",         # 佐賀 杵島郡
)
_PREFECTURES = (
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
)
# A district prefix is only a district if a 町/村 follows it — 霧島市国分郡田 does
# not qualify, 安八郡安八町 does.
_GUN_PREFIX = re.compile(r"^([^\s0-9\-]{1,5}郡)(?=[^\s0-9\-]{1,8}?[町村])")


def _utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_rows():
    if not os.path.exists(IN_CSV):
        return []
    with open(IN_CSV, encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh)
                if (r.get("shrine_name") or "").strip() and (r.get("url") or "").strip()]


_MUNI_RE = re.compile(r"([^\s0-9\-]{1,8}?[市区町村])")


def municipality(address):
    """'岐阜県大垣市墨俣町墨俣264番地' -> '大垣市'. '' when nothing parses."""
    a = (address or "").strip()
    a = re.sub(r"^〒?\s*\d{3}-?\d{4}\s*", "", a)
    for pref in _PREFECTURES:
        if a.startswith(pref):
            a = a[len(pref):]
            break
    a = _GUN_PREFIX.sub("", a, count=1)
    a = a.lstrip()
    for name in _MUNI_OVERRIDES:
        if a.startswith(name):
            return name
    m = _MUNI_RE.search(a)
    return m.group(1) if m else ""


def item_admin_labels(qids):
    """{item QID -> set of ja labels of its P131* ancestors}.

    One batched query instead of resolving municipality names separately: the
    ancestors' own labels are exactly what we need to compare the address against.
    """
    out, uniq = {}, sorted(qids)
    for i in range(0, len(uniq), 60):
        vals = " ".join("wd:%s" % q for q in uniq[i:i + 60])
        try:
            rows = _sparql(
                "SELECT ?item ?aLabel WHERE { VALUES ?item { %s } "
                "?item wdt:P131* ?a . "
                'SERVICE wikibase:label { bd:serviceParam wikibase:language "ja". } }'
                % vals)
        except Exception as e:
            print(f"  [admin chunk {i//60} skipped] {e}", flush=True)
            continue
        for b in rows:
            lab = b.get("aLabel", {}).get("value", "")
            if lab:
                out.setdefault(b["item"]["value"].rsplit("/", 1)[1], set()).add(lab)
    return out


def main():
    _utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; do not write the CSV")
    args = ap.parse_args()

    rows = load_rows()
    if not rows:
        print(f"no crawled rows at {IN_CSV} — run crawl_jinjacho_shrines.py first")
        return
    print(f"{len(rows)} crawled records "
          f"({len({r['prefecture'] for r in rows})} prefectures)", flush=True)

    # 1 — every name, raw and shinjitai-normalised, in one batched label lookup.
    names = set()
    for r in rows:
        n = r["shrine_name"].strip()
        names.add(n)
        names.add(to_shinjitai(n))
    print(f"resolving {len(names)} distinct names against shrine labels+aliases...",
          flush=True)
    label_qids = shrine_label_qids(sorted(names))
    print(f"  {len(label_qids)} names matched at least one shrine item", flush=True)

    # 2 — every candidate's administrative ancestry, in one batched P131* lookup.
    all_qids = {q for qs in label_qids.values() for q in qs}
    print(f"locating {len(all_qids)} candidate items...", flush=True)
    item_admin = item_admin_labels(all_qids)

    # 3 — emit only single-candidate-in-that-municipality rows.
    out, stats, seen = [], collections.Counter(), set()
    for r in rows:
        name = r["shrine_name"].strip()
        muni = municipality(r.get("address", ""))
        if not muni:
            stats["no municipality in the crawled address"] += 1
            continue
        cands = set(label_qids.get(name, [])) | set(
            label_qids.get(to_shinjitai(name), []))
        if not cands:
            stats["no label match"] += 1
            continue
        in_muni = [q for q in cands if muni in item_admin.get(q, set())]
        if not in_muni:
            stats["matched by name, but none in that municipality"] += 1
            continue
        if len(in_muni) > 1:
            stats["ambiguous within municipality"] += 1
            continue
        qid = in_muni[0]
        key = (qid, r["url"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"shrine": ENTITY % qid, "shrineLabel": name,
                    "website": r["url"]})

    # 4 — COLLISION GUARD. A municipality can still hold two shrines of the same
    # name with only ONE of them on Wikidata, and step 3 would then hand that one
    # item both URLs. Seen immediately: 八幡神社 at 墨俣町墨俣1番地 and at 墨俣町二ツ木
    # 22番地 both resolved to Q11391073 (八幡神社 (大垣市墨俣町)). At most one can be
    # right and nothing in the data says which, so drop every row of any such group.
    by_qid = collections.Counter(row["shrine"] for row in out)
    collided = {q for q, n in by_qid.items() if n > 1}
    if collided:
        dropped = [row for row in out if row["shrine"] in collided]
        out = [row for row in out if row["shrine"] not in collided]
        stats["dropped — one item claimed by several crawled shrines"] = len(dropped)
        for row in dropped[:6]:
            print(f"  collision: {row['shrine'].rsplit('/', 1)[1]} "
                  f"({row['shrineLabel']}) <- {row['website'][:70]}")
    stats["matched"] = len(out)

    print("\nresolution:")
    for k, v in stats.most_common():
        print(f"  {v:6d}  {k}")

    if args.dry_run:
        print(f"\n[DRY] would write {len(out)} rows -> {OUT_CSV}")
        return
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["shrine", "shrineLabel", "website"])
        w.writeheader()
        w.writerows(out)
    print(f"\nwrote {len(out)} matched rows -> {OUT_CSV}")


if __name__ == "__main__":
    main()
