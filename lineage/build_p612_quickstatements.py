#!/usr/bin/env python3
"""
build_p612_quickstatements.py
=============================
Turn `lineage/agent_results.tsv` — the full-article Opus read of all 444 shrines
(345 別表神社 + 99 神宮125社) — into QuickStatements for the mother-house model:

    <shrine>|P612|<target>|P1013|Q195793|S854|"<jawiki article url>"

ONE P612 with the P1013=Q195793 (Bunrei) criterion qualifier in the SAME
statement, never bare — the invariant in docs/wikidata_shrine_festival_model.md.
Lines are APPENDED to `modern-quickstatements/beppyo_p612.txt`, the atomic file
the daily drip already drains; existing lines there are never duplicated.

Class handling (Emma, 2026-08-04, on the two open calls):

  AUTOCHTHONOUS -> Q135508874. A positive finding: the article describes an
    in-situ founding with no parent shrine. These are the roots of the graph.

  TRANSFER -> the named source. **Including sources that are not shrines** —
    a palace, a place, a tomb (皇大神宮←笠縫邑, 白峯神宮←白峯陵, 石上神宮←宮中).
    Emma chose "emit P612 to the place item": the edge is real and recording it
    beats losing it, even though P612's model expects a shrine.

  NETWORK -> the network head, INCLUDING where the article names only a deity
    or a cult (函館八幡宮 "八幡神" -> 宇佐神宮, 笠間稲荷 勧請元不詳 -> 伏見稲荷大社).
    Emma chose the inferred head over emitting nothing. DEITY_HEAD below is that
    inference, and it is the one place in this script where a value is not read
    off the article.

  UNKNOWN -> no statement. Six articles give no origin at all.

Targets are resolved to QIDs through **ja.wikipedia**, never Wikidata: one
batched `prop=pageprops` call per 50 titles gives `wikibase_item` for free
(CLAUDE.md — Wikidata is a destination, not a lookup source).

Gates: the SUBJECT must have its own Wikidata item (`lineage/subject_qids.json`
— 21 of the 444 are jawiki redirects with no item of their own, and emitting for
them would write onto whichever shrine the redirect lands on); and the target
must resolve to a QID, must not be the subject itself, and must not be
Q135508874 unless the class is AUTOCHTHONOUS.

--supersede replaces the earlier keyword pass's line for a subject this pass
disagrees with. Emma 2026-08-04 on that earlier pass: it judged from keyword-
extracted sentences, not full articles, so where the two differ the full read
wins. Without it those items would land TWO contradictory P612 values — one
naming a parent, one saying autochthonous. This only ever edits the queue file,
never Wikidata: beppyo_p612.txt was first written 2026-08-03 and the freeze has
forced wikidata-daily-fire false since 2026-07-28, so no line in it has run.
Check that before using the flag on a file with a different history.

Usage: python lineage/build_p612_quickstatements.py [--dry-run] [--supersede]
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from shinto_miraheze.user_agent import USER_AGENT  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

RESULTS = os.path.join(SCRIPT_DIR, 'agent_results.tsv')
SUBJECTS = os.path.join(SCRIPT_DIR, 'subject_qids.json')
QS_OUT = os.path.join(ROOT, 'modern-quickstatements', 'beppyo_p612.txt')
LOG = os.path.join(SCRIPT_DIR, '_p612_resolution.log')

BUNREI = 'Q195793'            # criterion used: Bunrei
AUTOCHTHONOUS = 'Q135508874'  # Autocthonous shrine
API = 'https://ja.wikipedia.org/w/api.php'
THROTTLE = 0.3                # read-only jawiki calls, batched 50 titles each
DAB = set()                   # titles refused as disambiguation pages, for callers

# The network-head inference, used ONLY for NETWORK rows whose article names a
# deity or a cult rather than a shrine. Longest key wins, so 八幡大神 is matched
# before 八幡 would be. Keys are matched against the recorded source text.
DEITY_HEAD = {
    '八幡': '宇佐神宮',
    '稲荷': '伏見稲荷大社',
    '菅原道真': '北野天満宮',
    '天神信仰': '北野天満宮',
    '天満宮': '北野天満宮',
    '熊野': '熊野本宮大社',
    '諏訪': '諏訪大社',
    '氷川': '氷川神社 (さいたま市)',
    '東照': '日光東照宮',
    '山王権現': '日吉大社',
    '日吉神社': '日吉大社',
    '浅間大神': '富士山本宮浅間大社',
    '住吉神': '住吉大社',
    '武甕槌神': '鹿島神宮',
    '天照大神': '皇大神宮',
    '天照大御神': '皇大神宮',
    '大己貴命': '出雲大社',
    '粟嶋神': '淡嶋神社',
    '橋姫明神': '橋姫神社',
}


def load_results():
    with open(RESULTS, encoding='utf-8') as fh:
        next(fh, None)
        for line in fh:
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 2 and parts[0]:
                yield parts[0], parts[1], (parts[2] if len(parts) > 2 else '')


def candidates(source):
    """Article-title candidates for a recorded source string, best first.

    The source is prose the agent copied out of the article — "石清水八幡宮（平浜
    別宮）", "櫛田神社 (松阪市)", "宇佐八幡宮（宇佐神宮）", "熊野三山（紀伊国熊
    野権現）". The half-width parenthetical is often part of the real jawiki title
    (disambiguators), the full-width one almost never is, and the text inside
    either is sometimes the better target than the text outside it.
    """
    out = []

    def add(s):
        s = s.strip(' 　・/／、。')
        if s and s not in out:
            out.append(s)

    src = re.sub(r'※.*$', '', source).strip()
    # Cutting the ※note can leave an unbalanced （ — "笠縫邑（宮中から遷され…"
    # — which then defeats every parenthetical rule below.
    if src.count('（') > src.count('）'):
        src = src[:src.rindex('（')].strip()
    add(src)
    add(re.sub(r'（[^（）]*）', '', src))                      # drop 全角 gloss
    for inner in re.findall(r'（([^（）]*)）', src):            # try the gloss too
        for piece in re.split(r'[・、,／/]', inner):
            add(piece)
    for piece in re.split(r'[／/、]', re.sub(r'（[^（）]*）', '', src)):
        add(piece)
    # A shrine or place name embedded in prose: "比沼麻奈為神社などが論社",
    # "丹波国天の真名井", "大和笠縫邑". The agents recorded the source as a
    # sentence fragment more often than as a bare title.
    for m in re.findall(
            r'[一-龥々ぁ-んァ-ヶー]+?(?:神社|神宮|大社|八幡宮|天満宮|大神宮|権現|'
            r'真名井|笠縫邑|後宮|陵)', src):
        add(m)
        add(re.sub(r'^(?:大和|山城|京都の|紀伊国|丹波国|讃岐国|筑前国)', '', m))
    # A trailing half-width disambiguator belongs to the title; also try without.
    for c in list(out):
        add(re.sub(r'\s*\([^()]*\)$', '', c))
    return [c for c in out if len(c) >= 2 and not c.isdigit()]


def resolve_titles(titles):
    """title -> QID via ja.wikipedia pageprops, 50 titles per request.

    Disambiguation pages are refused. "京都の諏訪神社" resolves to the generic
    諏訪神社 article, which lists every Suwa shrine in Japan — as a P612 value
    that is worse than no value.
    """
    found = {}
    titles = list(titles)
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        params = {
            'action': 'query', 'format': 'json', 'formatversion': '2',
            'prop': 'pageprops', 'redirects': '1',
            'titles': '|'.join(batch),
        }
        req = urllib.request.Request(
            API + '?' + urllib.parse.urlencode(params),
            headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        norm = {}
        for key in ('normalized', 'redirects'):
            for entry in data.get('query', {}).get(key, []) or []:
                norm[entry['from']] = entry['to']
        pages = {}
        for page in data.get('query', {}).get('pages', []) or []:
            props = page.get('pageprops') or {}
            qid = props.get('wikibase_item')
            if qid and 'disambiguation' in props:
                DAB.add(page['title'])
            elif qid:
                pages[page['title']] = qid
        for asked in batch:
            seen, cur = set(), asked
            while cur in norm and cur not in seen:
                seen.add(cur)
                cur = norm[cur]
            if cur in pages:
                found[asked] = pages[cur]
        print(f'  resolved {len(found)}/{min(i + 50, len(titles))}')
        time.sleep(THROTTLE)
    return found


def head_for(source):
    """The network head for a NETWORK row whose source names no shrine."""
    for key in sorted(DEITY_HEAD, key=len, reverse=True):
        if key in source:
            return DEITY_HEAD[key]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--supersede', action='store_true',
                    help='drop the earlier pass\'s line where this pass disagrees')
    args = ap.parse_args()

    # Each shrine's OWN item. 25 of the 444 titles are jawiki redirects and
    # the old root _title2qid.json gave them the target article's QID, which
    # put statements on another shrine's item — see build_subject_map.py.
    title2qid = {t: q for t, q in
                 json.load(open(SUBJECTS, encoding='utf-8'))['map'].items() if q}
    rows = list(load_results())

    # Every candidate title we might need, resolved in one batched pass.
    wanted = set()
    for _, cls, source in rows:
        if cls == 'TRANSFER':
            wanted.update(candidates(source))
        elif cls == 'NETWORK':
            wanted.update(candidates(source))
            head = head_for(source)
            if head:
                wanted.add(head)
    print(f'resolving {len(wanted)} candidate titles via ja.wikipedia')
    resolved = resolve_titles(sorted(wanted))

    file_lines = []
    if os.path.exists(QS_OUT):
        with open(QS_OUT, encoding='utf-8') as fh:
            file_lines = [l.rstrip('\n') for l in fh]
    existing = {l.strip() for l in file_lines if l.strip()}
    already = {l.split('|')[0] for l in existing if '|P612|' in l}

    intended, lines, log, skipped = {}, [], [], {}
    for title, cls, source in rows:
        subject = title2qid.get(title)
        url = 'https://ja.wikipedia.org/wiki/' + urllib.parse.quote(title.replace(' ', '_'))
        if not subject:
            skipped['subject has no Wikidata item'] = skipped.get(
                'subject has no Wikidata item', 0) + 1
            log.append(f'-\t{cls}\t{title}\tno subject QID')
            continue
        if cls == 'UNKNOWN':
            skipped['UNKNOWN'] = skipped.get('UNKNOWN', 0) + 1
            log.append(f'{subject}\t{cls}\t-\t{title}: no origin in the article')
            continue

        if cls == 'AUTOCHTHONOUS':
            target, via = AUTOCHTHONOUS, 'in-situ founding'
        else:
            target, via = None, ''
            for cand in candidates(source):
                if cand in resolved:
                    target, via = resolved[cand], cand
                    break
                # jawiki's bare title may be a dab page while the real article
                # carries a disambiguator our own map already holds
                # (朝熊神社 -> 朝熊神社 (伊勢市)).
                same = [t for t in title2qid
                        if t == cand or t.startswith(cand + ' (')]
                if len(same) == 1:
                    target, via = title2qid[same[0]], same[0]
                    break
            if target is None and cls == 'NETWORK':
                head = head_for(source)
                if head and head in resolved:
                    target, via = resolved[head], f'inferred head: {head}'
            if target is None:
                skipped['unresolved target'] = skipped.get('unresolved target', 0) + 1
                log.append(f'{subject}\t{cls}\t-\t{title}: cannot resolve "{source}"')
                continue
            if target == subject:
                skipped['self-reference'] = skipped.get('self-reference', 0) + 1
                log.append(f'{subject}\t{cls}\t-\t{title}: target is the subject itself')
                continue
            if target == AUTOCHTHONOUS:
                skipped['autochthonous in non-root class'] = skipped.get(
                    'autochthonous in non-root class', 0) + 1
                log.append(f'{subject}\t{cls}\t-\t{title}: target is the root marker')
                continue

        line = f'{subject}|P612|{target}|P1013|{BUNREI}|S854|"{url}"'
        log.append(f'{subject}\t{cls}\t{target}\t{title} ← {via}')
        intended[subject] = (line, target, title)

    # This pass owns the P612 lines for its 444 subjects: any line for one of
    # them that is not exactly what this run intends is stale — the earlier
    # keyword pass reading the article differently, an earlier run of this script
    # before the disambiguation gate existed (佐嘉神社 -> the 松原神社 dab page), or
    # a line whose S854 cites a redirect title because the subject map used to
    # hand redirects another shrine's QID.
    subjects = {q for q in (title2qid.get(t) for t, _, _ in rows) if q}
    # Keyed by the S854 article URL as well as by subject: a line can cite one of
    # our 444 articles while sitting on the WRONG item, which is exactly what the
    # redirect bug produced (馬場都々古別神社's line landed on 都々古別神社's item).
    by_url = {l[0].split('|S854|')[1]: l[0] for l in intended.values()}
    superseded = [
        l for l in file_lines
        if '|P612|' in l and l.strip() and (
            (l.split('|')[0] in subjects
             and l.strip() != (intended.get(l.split('|')[0]) or ('', None, None))[0])
            or ('|S854|' in l and l.split('|S854|')[1] in by_url
                and l.strip() != by_url[l.split('|S854|')[1]]))
    ]

    for subject, (line, target, title) in intended.items():
        if line in existing:
            skipped['already in the atomic file'] = skipped.get(
                'already in the atomic file', 0) + 1
            continue
        if subject in already and not (args.supersede and any(
                l.split('|')[0] == subject for l in superseded)):
            skipped['subject already has a different P612 line'] = skipped.get(
                'subject already has a different P612 line', 0) + 1
            continue
        lines.append(line)
        already.add(subject)

    print(f'\n{len(lines)} new QuickStatements lines')
    for reason, n in sorted(skipped.items(), key=lambda kv: -kv[1]):
        print(f'  skipped, {reason}: {n}')
    print(f'{len(superseded)} earlier-pass lines disagree with the full read'
          + (' — dropping them' if args.supersede else ' — left in place'))

    if args.dry_run:
        for line in lines[:10]:
            print('  ' + line)
        return
    if args.supersede and superseded:
        drop = set(superseded)
        with open(QS_OUT, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('\n'.join(l for l in file_lines if l not in drop) + '\n')
    with open(QS_OUT, 'a', encoding='utf-8', newline='\n') as fh:
        if lines:
            fh.write('\n'.join(lines) + '\n')
    with open(LOG, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(log) + '\n')
    print(f'appended to {os.path.relpath(QS_OUT, ROOT)}; log in {os.path.relpath(LOG, ROOT)}')


if __name__ == '__main__':
    main()
