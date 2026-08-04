#!/usr/bin/env python3
"""
build_report.py
===============
Assemble `lineage/report.html` — the investigation page for the 444-shrine full
read: what the method actually was, every row it produced, and every place the
data does not fit Wikidata's model.

Pure local assembly from files already in the repo:
    agent_results.tsv     the classification, one row per shrine
    subject_qids.json     each shrine's OWN item (or null) + how it was found
    _collisions.json      the 19 shared-QID groups, investigated
    _source_coverage.tsv  does the named source have an item
    _p612_resolution.log  what each row became, or why it became nothing
and the staged QuickStatements in modern-quickstatements/beppyo_p612.txt.

The page is self-contained: data is inlined as JSON, no external requests.

Usage: python lineage/build_report.py
"""
import io
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OUT = os.path.join(SCRIPT_DIR, 'report.html')
CREATES = os.path.join(ROOT, 'modern-quickstatements', 'ise_jingu_creates.txt')

# Emma 2026-08-04 asked for one lineage report instead of three pages, so the
# hand-written analysis from `no_origin_6.html` lives here now. It is prose, not
# derivable from any file — a re-read of each shrine across its own article,
# en.wikipedia, the kami's article and the related shrine, recording what looks
# like an origin and is not. Deleting it would lose the only reason not to
# "helpfully" infer these six later.
NO_ORIGIN_NOTES = {
    '月讀宮': {
        'says': '「由緒は定かではないが、…延暦23年（804年）の大神宮儀式帳に「月讀宮一院、'
                '正殿四区」で…と記されており」— attestation, not origin.',
        'checked': 'No enwiki. ツクヨミ\'s article lists where the deity is enshrined but '
                   'gives no enshrinement narrative for any of them.',
        'not': '月夜見宮\'s origin (高河原, an agricultural kami in place) belongs to THAT '
               'shrine. A different shrine with a similar name — do not transplant it.',
    },
    '風宮': {
        'says': '「風宮の由緒は定かではないが、997年（長徳3年）の『長徳検録』に外宮所管の…'
                '風社と記されたとの…引用が最古である。」',
        'checked': 'No enwiki. シナツヒコ\'s article gives no first-enshrinement site.',
        'not': 'Its promotion from 末社-rank 風社 to 別宮 in 1293 after the Mongol invasions '
               'is a rank change on the same site — continuity, not an origin, and not '
               'enough for autochthonous either.',
    },
    '風日祈宮': {
        'says': '「風日祈宮の由緒は定かではないが、804年（延暦23年）の『皇太神宮儀式帳』の'
                '「風神社」が初出である。」',
        'checked': 'No enwiki. Same kami as 風宮, same dead end. 皇大神宮\'s article mentions '
                   'it only as a location.',
        'not': 'Same as 風宮 — the 1293 promotion is not an origin. And シナツヒコ = 天御柱命 '
               'at 龍田大社 is a deity identification, not a transfer from Tatsuta.',
    },
    '度津神社': {
        'says': '「往古の羽茂川洪水により社殿、古文書から別当寺にいたるまでことごとく流失した'
                'ため、創建の由緒は不詳である。」— the records were physically destroyed by a flood.',
        'checked': 'enwiki "Watatsu Shrine" adds only a founding attributed to Emperor '
                   'Chūai and says the history is uncertain.',
        'not': 'Do NOT give it a 五十猛命 / 伊太祁曽神社 lineage. The article disputes that the '
               'kami is 五十猛命 at all: the identification is Edo-period (橘三喜, 1678), '
               '吉田東伍 called it 「附会を免れず」, and the 佐渡志 records '
               '「又海童神ヲ祭ルトモ云ヘリ」— a competing sea-deity reading. イソタケル\'s own '
               'article never mentions this shrine, 佐渡, or any 勧請.',
    },
    '石園座多久虫玉神社': {
        'says': '「創建年代は不明であるが、第三代安寧天皇の時代の都である片塩浮穴宮跡の'
                '伝承地に鎮座している。」',
        'checked': 'No enwiki. No ja article exists for the kami at all — 建玉依比古命, '
                   '鴨玉依比古命, 玉依彦, 多久豆玉命 are all redlinks. 長尾神社 only repeats '
                   'the same dragon legend.',
        'not': 'Two things that look like origins and are not: the 上賀茂神社摂社土師尾社 / '
               '日吉大社摂社樹下若宮 line is a deity-identity equation (「…のこととされる」) with '
               'no direction; and standing on 安寧天皇\'s 片塩浮穴宮跡 is a fact about the SITE, '
               'not about where the kami came from. The 大神神社-head / 竜王社-body / '
               '長尾神社-tail dragon story is a landscape myth about three shrines\' relative '
               'positions.',
    },
}

# The sixth. It was in this set until the re-read found its answer somewhere the
# first pass had no reason to look, which is the whole argument for the re-read.
RECOVERED = {
    'title': '小俣神社', 'qid': 'Q17225978', 'target': 'Q11633343', 'target_label': '豊受大神宮',
    'found': 'The shrine\'s own article says nothing — its 歴史 section only dates it '
             '(pre-804) and describes the district. The answer is in the KAMI\'s article: '
             '『御鎮座本紀』 records it as enshrining ウカノミタマ稲女神, who came to Ise '
             'accompanying トヨウケ大神.',
    'not': 'Not 丹波. 豊受大神宮\'s article has Toyouke summoned from 丹波国 by oracle; chaining '
           'that would give 小俣神社 a Tanba origin, but no single source says that about this '
           'shrine — two inferences stacked. The staged value stops at the deity-home that is '
           'actually stated.',
}


def tsv(path, ncols):
    rows = []
    with open(path, encoding='utf-8') as fh:
        next(fh, None)
        for line in fh:
            p = line.rstrip('\n').split('\t')
            if p and p[0]:
                rows.append((p + [''] * ncols)[:ncols])
    return rows


def read_creates():
    """The CREATE batch for the 21 itemless shrines, parsed back out of the file
    it will actually be run from — so the page cannot drift from the batch."""
    out, cur = [], None
    for raw in open(CREATES, encoding='utf-8'):
        line = raw.strip()
        if line.startswith('# ') and ' — ' in line:
            cur = {'title': line[2:].split(' — ')[0].strip(),
                   'en': line.split(' — ', 1)[1].strip(), 'kana': '', 'p612': ''}
            out.append(cur)
        elif cur and line.startswith('LAST|P1814|"'):
            cur['kana'] = line.split('"')[1]
        elif cur and line.startswith('LAST|P612|'):
            cur['p612'] = line.split('|')[2]
    redirects = {r['title']: r['redirect'] for r in
                 json.load(open(os.path.join(SCRIPT_DIR, '_ise21.json'), encoding='utf-8'))}
    for c in out:
        c['redirect'] = redirects.get(c['title'], '')
    return out


def main():
    results = tsv(os.path.join(SCRIPT_DIR, 'agent_results.tsv'), 4)
    coverage = {r[0]: r for r in tsv(os.path.join(SCRIPT_DIR, '_source_coverage.tsv'), 7)}
    subjects = json.load(open(os.path.join(SCRIPT_DIR, 'subject_qids.json'), encoding='utf-8'))
    collisions = json.load(open(os.path.join(SCRIPT_DIR, '_collisions.json'), encoding='utf-8'))

    emitted = {}
    qs = os.path.join(ROOT, 'modern-quickstatements', 'beppyo_p612.txt')
    for line in open(qs, encoding='utf-8'):
        p = line.strip().split('|')
        if len(p) > 2 and p[1] == 'P612':
            emitted[p[0]] = p[2]

    reasons = {}
    for line in open(os.path.join(SCRIPT_DIR, '_p612_resolution.log'), encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if len(p) >= 4 and p[2] == '-':
            title = p[3].split(':')[0].strip()
            reasons[title] = p[3].split(':', 1)[1].strip() if ':' in p[3] else p[3]

    ise = {f[:-4] for f in os.listdir(os.path.join(ROOT, '_agent_input', 'jingu125'))
           if f.endswith('.txt')}

    rows = []
    for title, cls, source, quote in results:
        qid = subjects['map'].get(title)
        cov = coverage.get(title)
        rows.append({
            't': title, 'c': cls, 's': source, 'q': quote,
            'set': 'Ise' if title in ise else 'Beppyo',
            'qid': qid, 'how': subjects['how'].get(title, ''),
            'target': emitted.get(qid) if qid else None,
            'verdict': cov[3] if cov else ('' if cls in ('AUTOCHTHONOUS', 'UNKNOWN') else ''),
            'why': reasons.get(title, ''),
        })

    no_origin = [dict(NO_ORIGIN_NOTES[r['t']], title=r['t'], qid=r['qid'], quote=r['q'])
                 for r in rows if r['t'] in NO_ORIGIN_NOTES]

    data = {
        'rows': rows,
        'collisions': collisions,
        'creates': read_creates(),
        'noOrigin': no_origin,
        'recovered': RECOVERED,
        'generated': '2026-08-04',
        'counts': {
            'total': len(rows),
            'emitted': len(emitted),
            'noItem': sum(1 for r in rows if not r['qid']),
            'redirects': sum(1 for r in rows if 'redirect' in (r['how'] or '')),
        },
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

    html = TEMPLATE.replace('/*__DATA__*/', payload)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(html)
    print(f'{len(rows)} rows, {len(emitted)} statements -> '
          f'{os.path.relpath(OUT, ROOT)} ({os.path.getsize(OUT) // 1024} KB)')


TEMPLATE = r"""<title>Shrine lineage: the full read, audited</title>
<style>
:root{
  --paper:#f4f6f5; --raised:#ffffff; --ink:#161d1b; --muted:#5c6b67;
  --line:#d8e0dd; --indigo:#27496d; --indigo-soft:#e6ecf3;
  --ok:#2f6f4e; --warn:#8a6a1f; --bad:#9b3b2f;
  --ok-bg:#e6f0ea; --warn-bg:#f6efdd; --bad-bg:#f6e6e2;
  --mincho:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"Noto Serif JP","Songti SC",serif;
  --display:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --ui:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root{
  --paper:#101614; --raised:#182220; --ink:#e6ece9; --muted:#93a49f;
  --line:#2a3835; --indigo:#8fb4dd; --indigo-soft:#1b2a38;
  --ok:#79c79c; --warn:#d9b45e; --bad:#e08e7d;
  --ok-bg:#16281f; --warn-bg:#2a2313; --bad-bg:#2e1c18;
}}
:root[data-theme="dark"]{
  --paper:#101614; --raised:#182220; --ink:#e6ece9; --muted:#93a49f;
  --line:#2a3835; --indigo:#8fb4dd; --indigo-soft:#1b2a38;
  --ok:#79c79c; --warn:#d9b45e; --bad:#e08e7d;
  --ok-bg:#16281f; --warn-bg:#2a2313; --bad-bg:#2e1c18;
}
:root[data-theme="light"]{
  --paper:#f4f6f5; --raised:#ffffff; --ink:#161d1b; --muted:#5c6b67;
  --line:#d8e0dd; --indigo:#27496d; --indigo-soft:#e6ecf3;
  --ok:#2f6f4e; --warn:#8a6a1f; --bad:#9b3b2f;
  --ok-bg:#e6f0ea; --warn-bg:#f6efdd; --bad-bg:#f6e6e2;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--ui);
  font-size:15px;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px 96px;display:flex;
  flex-direction:column;gap:44px}
header{padding:56px 0 0;display:flex;flex-direction:column;gap:14px}
.eyebrow{font-size:11px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--muted);font-weight:600}
h1{font-family:var(--display);font-size:clamp(30px,4.4vw,46px);line-height:1.12;
  margin:0;font-weight:600;text-wrap:balance;letter-spacing:-.01em}
.lede{font-size:17px;color:var(--muted);max-width:64ch;margin:0}
h2{font-family:var(--display);font-size:25px;margin:0 0 4px;font-weight:600;
  text-wrap:balance}
h3{font-size:14px;margin:0;font-weight:650;letter-spacing:.01em}
p{margin:0;max-width:70ch}
section{display:flex;flex-direction:column;gap:16px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.tile{background:var(--raised);border:1px solid var(--line);border-radius:3px;
  padding:14px 16px;display:flex;flex-direction:column;gap:2px}
.tile b{font-family:var(--display);font-size:30px;font-weight:600;
  font-variant-numeric:tabular-nums;line-height:1.1}
.tile span{font-size:12px;color:var(--muted)}
.tile.flag b{color:var(--bad)}
.steps{display:flex;flex-direction:column;gap:0;border-top:1px solid var(--line)}
.step{display:grid;grid-template-columns:112px 1fr;gap:20px;padding:14px 0;
  border-bottom:1px solid var(--line);align-items:start}
.step .k{font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--indigo);font-weight:650;padding-top:3px}
.step .v{display:flex;flex-direction:column;gap:6px}
.step p{font-size:14px}
code,.mono{font-family:var(--mono);font-size:12.5px;font-variant-numeric:tabular-nums}
code{background:var(--indigo-soft);padding:1px 5px;border-radius:2px;
  color:var(--ink);white-space:nowrap}
.jp{font-family:var(--mincho);font-size:15px}
.note{border-left:2px solid var(--indigo);padding:2px 0 2px 16px;color:var(--muted);
  font-size:14px;max-width:70ch}
.group{background:var(--raised);border:1px solid var(--line);border-radius:3px;
  overflow:hidden}
.group>.head{display:flex;justify-content:space-between;align-items:baseline;
  gap:12px;padding:10px 14px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.member{display:grid;grid-template-columns:minmax(150px,1.1fr) 1fr auto;gap:14px;
  padding:10px 14px;border-bottom:1px solid var(--line);align-items:center}
.member:last-child{border-bottom:0}
.member .why{font-size:12.5px;color:var(--muted)}
.pill{display:inline-block;font-size:10.5px;letter-spacing:.08em;font-weight:650;
  text-transform:uppercase;padding:2px 7px;border-radius:2px;white-space:nowrap}
.p-article{background:var(--ok-bg);color:var(--ok)}
.p-redirect{background:var(--warn-bg);color:var(--warn)}
.p-none{background:var(--bad-bg);color:var(--bad)}
.p-own{background:var(--indigo-soft);color:var(--indigo)}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;
  position:sticky;top:0;background:var(--paper);padding:12px 0;z-index:2;
  border-bottom:1px solid var(--line)}
input[type=search]{flex:1;min-width:190px;font:inherit;font-size:14px;padding:7px 11px;
  border:1px solid var(--line);border-radius:2px;background:var(--raised);color:var(--ink)}
button{font:inherit;font-size:12.5px;padding:6px 11px;border:1px solid var(--line);
  background:var(--raised);color:var(--muted);border-radius:2px;cursor:pointer}
button[aria-pressed=true]{background:var(--indigo);border-color:var(--indigo);color:var(--paper)}
button:focus-visible,input:focus-visible{outline:2px solid var(--indigo);outline-offset:2px}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:3px;background:var(--raised)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th{text-align:left;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);font-weight:650;padding:9px 12px;border-bottom:1px solid var(--line);
  position:sticky;top:0;background:var(--raised)}
td{padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
tr.flagged td{background:var(--bad-bg)}
td.q{color:var(--muted);font-size:12.5px;max-width:46ch}
.count{font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
a{color:var(--indigo)}
footer{color:var(--muted);font-size:12.5px;border-top:1px solid var(--line);padding-top:18px}
@media (max-width:720px){
  .step{grid-template-columns:1fr;gap:4px}
  .member{grid-template-columns:1fr;gap:6px}
}
</style>

<div class="wrap">
<header>
  <div class="eyebrow">444 shrines · 別表神社 + 神宮125社 · 2026-08-04</div>
  <h1>Where every shrine's kami came from — and where the data model breaks</h1>
  <p class="lede">Every article was read in full by an agent, not searched for keywords.
  This page is the audit trail: the method, all 444 rows with the sentence each
  verdict rests on, and the places a Wikipedia article turned out not to be a
  Wikidata item.</p>
</header>

<section>
  <div class="tiles" id="tiles"></div>
</section>

<section>
  <h2>What was actually done</h2>
  <div class="steps">
    <div class="step"><div class="k">Membership</div><div class="v">
      <p>Both sets come from a ja.wikipedia <b>category</b>, direct members only, ns=0 —
      one paginated <code>list=categorymembers</code> call. Never a recursive walk, and
      never a Wikidata query.</p></div></div>
    <div class="step"><div class="k">Article text</div><div class="v">
      <p>Each article's <b>full plain text</b> was written to
      <code>_agent_input/&lt;set&gt;/&lt;title&gt;.txt</code>. Not the lead, not an infobox,
      not a keyword window — the whole article.</p></div></div>
    <div class="step"><div class="k">The read</div><div class="v">
      <p>38 Opus sub-agents, 11–12 articles each, instructed to <b>read every article in
      full and not to grep</b>. Each returns one line per file: the class, the source, and
      an <b>exact Japanese sentence</b> from the article. The quote is the evidence — a
      verdict with no sentence behind it is not accepted.</p>
      <p class="note">This is the whole reason for the pass. The earlier attempt judged
      from keyword-extracted sentences and called 129 of 344 unclear; read in full, 438 of
      444 give an origin. 分霊 and 勧請 are usually <i>not</i> the words the article uses.</p>
      </div></div>
    <div class="step"><div class="k">Classes</div><div class="v">
      <p><b>TRANSFER</b> — a specific named source. <b>NETWORK</b> — tied to a named
      network, head, or deity with no transfer stated. <b>AUTOCHTHONOUS</b> — the kami
      originated here; these are the roots of the graph. <b>UNKNOWN</b> — no origin at all.</p>
      </div></div>
    <div class="step"><div class="k">Subject</div><div class="v">
      <p>Each shrine's <b>own</b> Wikidata item, resolved in order: the jawiki article's
      <code>wikibase_item</code>; else an item whose jawiki sitelink is exactly this title;
      else an item with exactly this ja label; else none. Redirects are
      <b>not</b> followed — see below.</p></div></div>
    <div class="step"><div class="k">Target</div><div class="v">
      <p>The recorded source is prose, so it is reduced to title candidates and looked up
      on ja.wikipedia. Disambiguation pages are refused; so is a target equal to the
      subject. Statements are
      <code>P612 + P1013=Q195793 + S854</code>, one per subject.</p></div></div>
  </div>
</section>

<section>
  <h2>An article is not a data item</h2>
  <p>The first subject map asked ja.wikipedia for each title's item <b>with redirects
  followed</b>. That hands a redirect the QID of the article it lands on — so 25 shrines
  were pointed at a neighbour's item and 19 items were claimed by two or three shrines at
  once. On Wikipedia a redirect is navigation; on Wikidata the shrine behind it is still
  its own subject. Four of them already had an item nobody would have found by sitelink.</p>
  <div id="collisions" style="display:flex;flex-direction:column;gap:12px"></div>
</section>

<section>
  <h2>The 21 with no item at all</h2>
  <p>Every one is a real 神社 of the 神宮125社 with its own name, its own kami and its own
  origin account — and on ja.wikipedia every one is a <b>redirect</b> into a neighbouring
  shrine's article. Two (<span class="jp">大河内神社</span>,
  <span class="jp">打懸神社</span>) are <b>section</b> redirects, which is the clearest sign
  they are separate subjects sharing one page for editorial convenience. No article means
  no sitelink, and a sitelink is how nearly everything here finds a QID.</p>
  <p class="note">This is not a lookup failure. Wikidata was also asked the two questions a
  sitelink cannot answer — is there an item whose jawiki sitelink is this redirect title,
  and is there an item whose ja label is exactly this name — and both came back empty for
  all 21. That same method is what found <code>Q114593121</code> and three items with no
  sitelink at all elsewhere in this set.</p>
  <p>They are now a CREATE batch, <code>modern-quickstatements/ise_jingu_creates.txt</code>,
  run through <code>create_items.py</code> behind a gate that stays shut until the Wikidata
  freeze lifts. Each gets the ja name, the English name, <code>P31 = Q845945</code>,
  <code>P361 = Q687168</code> (伊勢神宮 — what all 99 of these that already have an item
  carry), the hiragana reading, and the P612 this read produced. No descriptions.</p>
  <div class="tablewrap">
    <table>
      <thead><tr><th>Shrine</th><th>English name</th><th>Reading</th>
        <th>jawiki redirect goes to</th><th>P612</th></tr></thead>
      <tbody id="creates"></tbody>
    </table>
  </div>
</section>

<section>
  <h2>The six with no origin at all</h2>
  <p>Six of the 444 came back with no account of where their kami came from. They were
  re-read afterwards — the whole local article again, then en.wikipedia, then the
  <i>kami's</i> own article, then the related shrine the article names. <b>One turned out to
  have an answer</b> in a place the first pass had no reason to look; the other five are
  genuine, and four of them say so in the source's own words.</p>
  <p class="note">A blank here is not like a blank elsewhere: these are shrines whose lineage
  <i>cannot</i> be inferred from a neighbour without inventing it. So each row below also
  records what looks like an origin and is not — that column is the point of the section.
  The five are staged as <code>P612 = Q24238356</code> (unknown value), which says "it has a
  mother house and we do not know it" rather than leaving the property absent.</p>
  <div id="recovered" class="group"></div>
  <div id="noorigin" style="display:flex;flex-direction:column;gap:12px"></div>
</section>

<section>
  <h2>All 444 rows</h2>
  <p>Every classification with the sentence it rests on. <b>Flagged</b> shows only rows
  that produced no statement — no item of their own, an unresolvable source, or no origin
  in the article.</p>
  <div class="controls">
    <input type="search" id="q" placeholder="Search shrine, source, or quote…"
      aria-label="Search rows">
    <button data-f="all" aria-pressed="true">All</button>
    <button data-f="flagged" aria-pressed="false">Flagged</button>
    <button data-f="TRANSFER" aria-pressed="false">Transfer</button>
    <button data-f="NETWORK" aria-pressed="false">Network</button>
    <button data-f="AUTOCHTHONOUS" aria-pressed="false">Autochthonous</button>
    <button data-f="Ise" aria-pressed="false">Ise only</button>
    <span class="count" id="count"></span>
  </div>
  <div class="tablewrap">
    <table>
      <thead><tr><th>Shrine</th><th>Class</th><th>Source named</th>
        <th>Item</th><th>Evidence</th></tr></thead>
      <tbody id="tbody"></tbody>
    </table>
  </div>
</section>

<footer>Generated by <code>lineage/build_report.py</code> from
<code>agent_results.tsv</code>, <code>subject_qids.json</code>,
<code>_collisions.json</code> and the staged QuickStatements. Nothing here has been
written to Wikidata — the freeze holds until 2026-08-10.</footer>
</div>

<script>
const DATA = /*__DATA__*/;
const esc = s => (s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

const c = DATA.counts;
const tiles = [
  [c.total, 'articles read in full'],
  [c.emitted, 'statements staged'],
  [DATA.rows.filter(r=>r.c==='AUTOCHTHONOUS').length, 'autochthonous roots'],
  [DATA.rows.filter(r=>r.c==='TRANSFER'||r.c==='NETWORK').length, 'with a named lineage'],
  [c.redirects, 'titles that are redirects', true],
  [c.noItem, 'shrines with no item', true],
];
document.getElementById('tiles').innerHTML = tiles.map(([n,l,flag]) =>
  `<div class="tile${flag?' flag':''}"><b>${n}</b><span>${l}</span></div>`).join('');

document.getElementById('collisions').innerHTML = DATA.collisions.map(g => {
  const members = g.members.map(m => {
    const own = m.own_item_by_sitelink || (m.items_by_exact_ja_label[0]||{}).qid;
    let kind, why;
    if (m.page_kind === 'article') {
      kind = '<span class="pill p-article">article</span>';
      why = 'owns this item';
    } else {
      kind = '<span class="pill p-redirect">redirect</span>';
      why = 'redirects to <span class="jp">' + esc(m.redirect_target) + '</span>' +
            (m.redirect_section ? ' <b>#' + esc(m.redirect_section) + '</b>' : '');
    }
    const item = own
      ? `<span class="pill p-own">${esc(own)}</span>`
      : (m.page_kind === 'article' ? `<span class="mono">${esc(m.mapped_qid)}</span>`
                                   : '<span class="pill p-none">no item</span>');
    return `<div class="member"><div><span class="jp">${esc(m.title)}</span> ${kind}</div>
      <div class="why">${why}</div><div>${item}</div></div>`;
  }).join('');
  return `<div class="group"><div class="head">
    <h3><span class="mono">${esc(g.shared_qid)}</span> was claimed by ${g.members.length} shrines</h3>
    </div>${members}</div>`;
}).join('');

document.getElementById('creates').innerHTML = DATA.creates.map(c => {
  const sec = c.redirect.includes('#');
  return `<tr>
    <td><a class="jp" href="https://ja.wikipedia.org/wiki/${encodeURIComponent(c.title)}"
      >${esc(c.title)}</a></td>
    <td>${esc(c.en)}</td>
    <td class="jp">${esc(c.kana)}</td>
    <td class="jp">${esc(c.redirect)}${sec?' <span class="pill p-redirect">section</span>':''}</td>
    <td><a class="mono" href="https://www.wikidata.org/wiki/${esc(c.p612)}">${esc(c.p612)}</a></td>
  </tr>`;
}).join('');

const r0 = DATA.recovered;
document.getElementById('recovered').innerHTML = `
  <div class="head"><h3><span class="jp">${esc(r0.title)}</span> — recovered</h3>
    <span class="mono">${esc(r0.qid)} → ${esc(r0.target)} <span class="jp">${esc(r0.target_label)}</span></span></div>
  <div class="member" style="grid-template-columns:1fr"><div>
    <p style="font-size:14px">${esc(r0.found)}</p>
    <p class="why" style="margin-top:8px">${esc(r0.not)}</p></div></div>`;

document.getElementById('noorigin').innerHTML = DATA.noOrigin.map(n => `
  <div class="group">
    <div class="head"><h3><span class="jp">${esc(n.title)}</span></h3>
      <span class="mono">${esc(n.qid)} → Q24238356 unknown</span></div>
    <div class="member" style="grid-template-columns:1fr"><div>
      <p class="jp" style="font-size:14px">${esc(n.says)}</p>
      <p class="why" style="margin-top:8px"><b>Also checked.</b> ${esc(n.checked)}</p>
      <p class="why" style="margin-top:6px;color:var(--bad)"><b>Must not be inferred.</b>
        ${esc(n.not)}</p></div></div>
  </div>`).join('');

const tbody = document.getElementById('tbody');
let filter = 'all', query = '';
const isFlagged = r => !r.qid || !r.target;

function render(){
  const rows = DATA.rows.filter(r => {
    if (filter === 'flagged' && !isFlagged(r)) return false;
    if (filter === 'Ise' && r.set !== 'Ise') return false;
    if (['TRANSFER','NETWORK','AUTOCHTHONOUS'].includes(filter) && r.c !== filter) return false;
    if (query && !(r.t+r.s+r.q).toLowerCase().includes(query)) return false;
    return true;
  });
  document.getElementById('count').textContent = rows.length + ' of ' + DATA.rows.length;
  tbody.innerHTML = rows.map(r => {
    const item = r.qid
      ? `<span class="mono">${esc(r.qid)}</span>` + (r.target ? '' :
          `<br><span class="why" style="font-size:11.5px;color:var(--bad)">${esc(r.why||'no statement')}</span>`)
      : `<span class="pill p-none">no item</span><br><span class="why" style="font-size:11.5px">${esc(r.how)}</span>`;
    return `<tr class="${isFlagged(r)?'flagged':''}">
      <td><span class="jp">${esc(r.t)}</span><br><span class="why" style="font-size:11px;color:var(--muted)">${r.set}</span></td>
      <td>${esc(r.c)}</td>
      <td class="jp" style="font-size:13.5px">${esc(r.s)||'—'}</td>
      <td>${item}</td>
      <td class="q jp">${esc(r.q)||'—'}</td></tr>`;
  }).join('');
}

document.querySelectorAll('.controls button').forEach(b => b.addEventListener('click', () => {
  filter = b.dataset.f;
  document.querySelectorAll('.controls button').forEach(o =>
    o.setAttribute('aria-pressed', String(o === b)));
  render();
}));
document.getElementById('q').addEventListener('input', e => {
  query = e.target.value.toLowerCase(); render();
});
render();
</script>
"""


if __name__ == '__main__':
    main()
