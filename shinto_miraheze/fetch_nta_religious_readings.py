#!/usr/bin/env python3
"""
fetch_nta_religious_readings.py
===============================
Build a lookup of **legally registered readings** for Japan's temple and shrine
corporations, from the National Tax Agency corporate-number registry.

## Why this exists

The English-label residual — ~18,065 shrines and temples with no ``Len`` — is the
population the deterministic stages could not name, and they could not name it for
exactly one reason: **the item carries no kana**. The reading is what is missing, not
the romanization rule. Measured 2026-09-18 over the 400 staged ``en_label/`` work-files:

  * 23 of 400 have a Japanese Wikipedia article, whose lead gives the reading as
    furigana — ``栄養寺（えいようじ）``. Those 39 were answered by reading them.
  * Of 50 sampled from the rest, **39 carry no source of any kind** — no official
    website, no Commons category, no Kokugakuin id, no ja alias.
  * Web search returns readings that are the *search engine's* inference. Two were
    checked against their claimed sources and neither was in them: ``わせんじ`` for
    和泉寺 (the cited jawiki page does not exist) and ``なかはらじ`` for 中原寺
    (tesshow.jp lists that temple in kanji only, no reading anywhere on the page).
    A reading that cannot be traced to a source must not become a label — the
    work-files say so outright: *"Do not invent a reading you cannot source."*

The NTA registry is the source that survives that test. A 宗教法人's フリガナ is the
one it registered with the state, and this repo already treats it as authoritative:
**4,764 P1814 statements on 4,763 items cite houjin-bangou.nta.go.jp**, and Emma's
2026-08-24 ruling in ``docs/kana_name_mate_rulings.md`` is that an NTA-cited reading is
PRESERVED even when it looks like a typo, because the corporation registered it that way.

## What the registry does and does not give

Furigana is optional on registration, so coverage is partial. Measured on Yamanashi
(file 27959, 35,974 rows): **2,586 temple/shrine corporations, 433 with a furigana —
17%**. Nationally that is on the order of ten thousand readings, which is the same
order as the label backlog itself.

Two properties of the data that the matcher downstream has to respect:

  * **The reading is KATAKANA** — ``専徳寺 -> セントクジ``. P1814 wants modern hiragana
    and ``collect_name_in_kana.py`` REJECTS katakana outright, which is right: katakana
    is the signature of the ancient-Engishiki-reading error that the kana-qualifier
    cleanup exists to undo. A reading from here is converted, and its provenance is the
    NTA citation, not the script.
  * **The reading is sometimes the STEM ONLY** — ``淺間神社 -> センゲン``, with ジンジャ
    left off. So a reading is not simply the whole name's romanization and cannot be
    treated as one.

## Matching is by name AND municipality, never by name alone

``遠妙寺`` appears in 中央市 and again in 笛吹市. Temple names repeat heavily — that
repetition is the whole premise of ``generate_identical_name_en_labels.py`` — so a
name-only match would attach one corporation's registered reading to a different
building. The output is keyed ``(prefecture, municipality, name)`` and the matcher is
expected to require all three.

## Network behaviour

The bulk download is a session POST, not a plain link: fetch the index once to get a
cookie, then POST ``selDlFileNo`` + ``event=download`` to the same URL. Without the
cookie the server returns the HTML page with a 200 and an ``application/octet-stream``
that is really the page. Files are ~2-20MB zipped per prefecture, ~240MB for 全国;
this fetches per prefecture so a failure costs one prefecture, not the run.

The CSVs are NOT kept. They are ~240MB, they are republished monthly, and a stale copy
in the repo would be worse than no copy. Only the derived JSON is written.

Usage:
    python shinto_miraheze/fetch_nta_religious_readings.py --pref 19   # one prefecture
    python shinto_miraheze/fetch_nta_religious_readings.py             # all 47
    python shinto_miraheze/fetch_nta_religious_readings.py --stats     # read the output
"""
import argparse
import csv
import http.cookiejar
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)

from shinto_miraheze.ua_for import ua_for  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "nta_religious_readings.json")
BASE = "https://www.houjin-bangou.nta.go.jp/download/zenken/"
THROTTLE = 5.0          # a government bulk endpoint; one file every five seconds.

# CSV column positions, from the registry's own resource definition and verified
# against file 27959 on 2026-09-18. The file has 30 columns and no header row.
C_HOUJIN, C_NAME, C_PREF, C_CITY, C_FURIGANA = 1, 6, 9, 10, 28

# A corporation that is a place of worship. The suffix test is what the registry gives
# us -- there is no "religious corporation" flag in the CSV -- so the corporate-form
# words are excluded first, because 株式会社 ends in 社 and would otherwise swamp the
# set (9,125 "religious-looking" rows in Yamanashi against a real 2,586).
_CORP = re.compile("会社|有限|合同|合資|組合|財団|社団|学校|医療|協会|連合")
_WORSHIP = re.compile(r"(寺|神社|神宮|八幡宮|大社|院|庵|坊|稲荷)$")


def is_worship(name):
    return bool(name) and not _CORP.search(name) and bool(_WORSHIP.search(name))


def _opener():
    # ua_for(url) picks the agent from the DESTINATION -- the two personas must never be
    # built by hand (tests/test_no_hardcoded_user_agents.py). This host is neither wiki,
    # so it takes whatever ua_for gives a third-party host.
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", ua_for(BASE)), ("Referer", BASE)]
    op.open(BASE, timeout=90).read()          # the cookie is the point of this call
    return op


def file_numbers(op):
    """{prefecture_name: selDlFileNo} for the Unicode CSV of each prefecture.

    The page is three stacked sections — CSV/Shift_JIS, CSV/Unicode, XML/Unicode — and
    each prefecture appears once in each, as `<dt>山梨県</dt>` followed by a
    `doDownload(N)`. So a prefecture has three ids in document order and the SECOND is
    the Unicode CSV (山梨県: 27958 Shift_JIS, 27959 Unicode, 27960 XML, checked
    2026-09-18 by downloading 27959 and getting `19_yamanashi_all_20260831.csv`).

    Discovered rather than hardcoded: the ids change when the registry republishes
    monthly. A first version read `<tr>` rows and paired names to ids positionally,
    which silently mapped 北海道 to 青森県's file — every prefecture was off by one
    region and the run returned 0 readings with no error.
    """
    html = op.open(BASE, timeout=90).read().decode("utf-8", "replace")
    pairs = re.findall(r"<dt[^>]*>\s*([一-鿿]{2,4}[都道府県])\s*</dt>"
                       r".*?doDownload\((\d+)\)", html, re.S)
    seen = {}
    for name, fid in pairs:
        seen.setdefault(name, []).append(fid)
    return {name: ids[1] for name, ids in seen.items() if len(ids) >= 2}


def fetch_prefecture(op, file_no):
    """[(name, pref, city, furigana, houjin_bangou)] for the worship corporations.

    The 13-digit corporate number is carried because the CITATION is what protects the
    value downstream. Emma's rule (docs/kana_name_mate_rulings.md, 2026-08-24) is that a
    reading cited to houjin-bangou.nta.go.jp is PRESERVED even when it looks like a typo,
    and an uncited one is corrected — so a reading emitted without its reference would be
    "fixed" by the next pass. generate_lost_shrine_creates.py records exactly that near
    miss on 近殿神社's ちかどのじんしゃ. The number is what makes the reference URL point
    at this corporation rather than at the registry's front door.
    """
    body = urllib.parse.urlencode({"selDlFileNo": file_no, "event": "download"}).encode()
    data = op.open(urllib.request.Request(BASE, data=body), timeout=600).read()
    if not data.startswith(b"PK"):
        raise RuntimeError("file %s came back as %r, not a zip -- session lost"
                           % (file_no, data[:16]))
    z = zipfile.ZipFile(io.BytesIO(data))
    text = z.read(z.namelist()[0]).decode("utf-8", "replace")
    out = []
    for r in csv.reader(io.StringIO(text)):
        if len(r) <= C_FURIGANA:
            continue
        name, furi = r[C_NAME], r[C_FURIGANA].strip()
        if furi and is_worship(name):
            out.append((name, r[C_PREF], r[C_CITY], furi, r[C_HOUJIN]))
    return out


def reference_url(houjin_bangou):
    """The registry page for one corporation — the citation that protects the reading."""
    return ("https://www.houjin-bangou.nta.go.jp/henkorireki-johoto.html?selHouzinNo=%s"
            % houjin_bangou)


def load():
    if not os.path.exists(OUT):
        return {}
    with io.open(OUT, encoding="utf-8") as fh:
        return json.load(fh)


def key(pref, city, name):
    return "%s|%s|%s" % (pref, city, name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pref", help="one prefecture name, e.g. 山梨県")
    ap.add_argument("--stats", action="store_true", help="read the output, fetch nothing")
    args = ap.parse_args()
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    if args.stats:
        d = load()
        print("%s readings in %s" % (len(d), OUT))
        for k in list(d)[:10]:
            print("   %-40s %s  %s" % (k, d[k]["kana"], d[k]["houjin"]))
        return 0

    op = _opener()
    files = file_numbers(op)
    if args.pref:
        files = {k: v for k, v in files.items() if k == args.pref}
        if not files:
            print("no such prefecture on the page")
            return 1

    readings = load()
    for i, (pref, fid) in enumerate(sorted(files.items()), 1):
        try:
            rows = fetch_prefecture(op, fid)
        except Exception as exc:          # one prefecture, not the run
            print("%-8s FAILED %s" % (pref, exc))
            continue
        for name, p, city, furi, houjin in rows:
            readings[key(p, city, name)] = {"kana": furi, "houjin": houjin}
        print("%2d/%d %-8s %5d readings" % (i, len(files), pref, len(rows)))
        time.sleep(THROTTLE)

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(readings, fh, ensure_ascii=False, indent=0, sort_keys=True)
    print("\n%d readings -> %s" % (len(readings), OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
