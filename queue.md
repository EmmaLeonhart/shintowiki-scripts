# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## ⭐ FRONT OF QUEUE — do these first, in order (Emma 2026-07-06)

1. [ ] **READ THE HANDOFF DOCUMENT** `docs/deleted_items_recreation_handoff_2026-07-06.md`
   before touching the deleted-item work. It captures the full recreation pipeline built on
   branch `claude/work-queue-processing-ps5j2l` (not merged to main). A session started on `main`
   prematurely; this handoff is the bridge so it doesn't duplicate or clobber the branch work.

2. [ ] **MAIN PRIORITY — classify the remaining 79 unclassified recreation candidates (P31).**
   `enrich_p31.py` now types 134/213 from the entity name; **79 are left null for human review**
   (Izumo-taisha 教会 churches, 霊場 sacred-site lists, geographic 海/湯, rank/系 systems, person
   names without clan markers). Push the count down further ONLY where a name signal is
   definitional — add rules like the shrine/temple/kofun ones, verifying every new type QID live
   on Wikidata. NEVER guess (a host-page-category pass already mislabeled a kami as a dab page —
   see the handoff §5). Leave the genuinely-ambiguous for Emma. Then continue "a bit more data"
   enrichment (P17=Japan for shrines/festivals/temples, P131 place) per the handoff §6. Recreation
   itself stays human-gated (Emma go/no-go + min-claim-set — see Blockers at queue end).

---

## Multilingual label generalization (BFS-driven)

Goal: name every important Shinto entity in all ~60 covered languages. All the
transliteration categories (kami / Buddhist deities+Sanskrit engine / provinces /
people / texts / Shikinaisha lists / court-ranks-CJK / misc-terms) are SHIPPED and
wired into the 11-step `!regenerateQuickStatements.bat` — see DEVLOG 2026-07-04.

DELIVERY to Wikidata (verified 2026-07-04): `modern-quickstatements/select_label_proposals.py`
globs `shinto-label-generator/quickstatements/*.txt` — ALL category files included,
not just `<lang>.txt` — into `label_proposals_drip.txt`, drip-fed **20/day** by the
daily submission (routed to direct-daily-edits since the QS path is retired). The
drip opens FULLY on `RAMP_DATE` = 2027-05-23 (a deliberate ~1-year community-review
window). So the labels reach Wikidata; the tail just drains slowly until the ramp.

Translation tier — investigated & closed for the local work-loop (2026-07-05):

- **Descriptive concepts: DONE.** `generate_concept_translations.py`'s hand-authored
  dict is fully drained (11/11 concepts, 57 labels, in the drip). It only translates
  what a human authors into the dict — no auto-discovery — so it is NOT "ongoing";
  it no-ops until someone adds entries. The confidently-Shinto concepts are exhausted.
- **Shinto property names: DONE.** The only two genuinely Shinto-specific descriptive
  properties — P13723 shrine ranking, P14005 court rank — are translated
  (`generate_property_translations.py`, in the drip). Every other entry in
  `bfs/property_label_report.md` is a GENERIC community-maintained Wikidata property
  (worshipped by, official religion, next-higher-rank, literal translation, …) —
  core infrastructure, out of this project's remit; do NOT mass-propose translations.
- **Concept-classes / 90-item text residue (`bfs/text_labels_residue.md`):** these are
  translation-not-transliteration of mostly non-Japanese / foreign-encyclopedia /
  infra titles — i.e. bulk LLM-grunge, which per the top-of-file policy belongs to the
  claude.ai remote routine (`remote_queue.json`), NOT the local work-loop. Not
  actionable here without guessing.

So the translation tier is COMPLETE: the transliteration matrix is shipped +
drip-delivered, and every confidently-actionable translation is done. What's left is
remote-routine drift and the 2027 delivery ramp.

**DONE — QuickStatements provenance comments** (2026-07-05; promoted from todo.md).
Annotate each generated label line with the source it derives from, as a `# <source>`
comment line (drip selector + submitter skip `#`, so it never reaches Wikidata; same
pattern generate_indonesian_proposals.py already uses). FOUNDATION SHIPPED: `write_qs`
now emits a provenance comment for 4-tuple `(qid, lang, label, source)` rows
(backward-compatible; tested). Sources: phonetic ← `romaji "…"`, CJK ← `ja kanji "…"`,
ko-hanja ← `ja kanji "…" (hanja)`, Sanskrit-named ← `Sanskrit "…"`.

**IMPORTANT — how comments actually reach the .txt (corrected 2026-07-05):** the
CATEGORY generators (kami, buddhist, human, misc_terms, shrine_rank, courtrank_buddhist,
province, text, shikinaisha, *_translations) are NOT run by CI — `label-generator-
regenerate.yml` only runs fetch_shrines_tokiponize / korean / chinese / indonesian /
multilang. So category-file comments apply only on Emma's local `!regenerateQuickStatements.bat`
rebuild (verified end-to-end 2026-07-05: a local `generate_misc_terms` run produced 960
well-formed `# <source>` lines, one per label, integrity tests green — then reverted so
category files stay a consistent set for the next full rebuild). The CI-run subset
(korean/chinese/multilang) DOES apply on CI once wired.

WIRED — ALL 8 CATEGORY generators done (2026-07-05): kami, human, misc_terms,
shrine_rank, courtrank_buddhist, buddhist, **province**, **text** (text's
`labels_for_item` now returns `(lang, label, source)` triples; its test helper +
a provenance assertion updated). These apply on Emma's next local
`!regenerateQuickStatements.bat`.

ROLLOUT COMPLETE — every transliteration generator now emits provenance. CI-run
(korean, indonesian, chinese, tokiponize already did; **multilang** wired 2026-07-05 →
applies next CI regen) + all 8 category generators (apply on the local `.bat` rebuild).
Not covered, by design: `shikinaisha_lists` (frame-built descriptive list-titles, not a
transliteration of one source label — could add a province/parent source later if wanted)
and the hand-authored `courtrank_/concept_/property_translations` (translations, no source
label → N/A). Each wired file ~doubles in line count on regen — the intended "annotate
output lines".
(Sanskrit-engine polish DONE: Greek double-nasal νντ→ντ; Arabic/Perso-Arabic/Hebrew
word-initial vowel carriers — Indra → ar إندرا / fa ایندرا / he אינדרא.)

---

## Backlog board barrel-through (2026-07-05 session)

Working the 8 `BACKLOG_ITEMS` (`site/generate_pages.py`). #1 + #2 DONE this session;
#3/#4/#6/#7 are shipped-automation whose residual is inherent human review / remote-
routine (not build tasks); #8 has its own continuation section below; the analysis pass
its own section further down. Nothing buildable left in the board itself.

## Backlog #8 — recreate deleted Wikidata items (CONTINUATION for a future session)

Generator SHIPPED this session: `recreate-deleted-wikidata/generate_recreate_quickstatements.py`
(isolated dir; NOT auto-submitted; 7 unit tests; CI-wired). It walks
`[[Category:Pages with deleted QID in ill template]]` (144 pages → **304 distinct
deleted ill targets**) and writes info-rich `CREATE` blocks to
`recreate-deleted-wikidata/recreate_quickstatements.txt` + a human-review `review.md`.
Corrected the original design: the deleted QIDs are the ill **targets** (sub-topics),
NOT the pages (which already have their own items) — so NO `P11250|"shinto:…"`. Old
QIDs are carried as `#` provenance comments (36 recovered — 31 from `dd=`, +5 from the
QID-was-written-into-the-label-slot data-loss bug, now detected & recovered). Enrichment:
jawiki-article existence gates the sitelink (notability anchor); ja-already-linked-to-a-
live-item flags probable duplicates (2 found). Only **7/304** currently have a safe
jawiki sitelink → the rest need content before they'd survive re-deletion.

**Remaining:**
- [ ] Per-target research to give each item enough content to not be auto-deleted again
  (autonomous RAG — like the fandom crossref already done). Enrich `CREATE` blocks with
  authoritative data (claims, better sitelinks, descriptions) beyond labels+provenance.
- The min-claim-set-per-type decision + recreation go/no-go + human-gated QS submission are
  **NEEDS-DECISION (Emma)** → see "Blockers awaiting Emma" at the queue end.

## Next-session analysis pass — DONE (2026-07-05)

Written per-item "resolved / partial / not started + what's left" over all 8 backlog
problems shipped to `docs/backlog_resolution_status_2026-07-05.md`. Highest-value
remaining build thread flagged there: **#5 phase (c) tail** (later gazetteer suffixes +
misses). #8 per-target research is larger but content/Emma-gated.

Emma's taxonomy (sorting rule): **empty stubs = real things → recreate**; **deletion-requested
= usually duplicates → relink to the existing live item, not recreate**; **deleted-but-still-
used-on-wiki = the complicated middle** (our 304 are all used). Build the dataset in THIS order
(all LOCAL/read-only until the final human-gated submission; respect the Wikidata QS-only +
freeze rules — recreation itself stays human-gated):

## Context dump + agentic RAG on deleted Immanuelle-created Wikidata items — PROCESSED (2026-07-05)

Context dump reviewed. Full analysis: `docs/deleted_immanuelle_items_analysis_2026-07-05.md`.
Facts: `context dump/deleted.txt` is an XTools export of **455 deleted Immanuelle-created
Q-items** (list only — QID + timestamp + byte-size + admin-gated undelete link; NO content);
`chat dump.md` is the interrupted-session transcript (backlog #1/#2/#8, no deleted-item
content). **35** of the deleted QIDs overlap backlog #8's recovered ill-target set — those
are already covered by #8 (content sourced from shinto-wiki ills, not the deleted items).

RAG DONE (corrected — my earlier "blocked" call was wrong): the deletion LOGS are public.
`rag_deleted_logs.py` recovered **273 clean English labels** from `content was:"X"` log
comments (kami, shrines, Izumo-taisha branch churches, people). Buckets: 322 empty-item /
96 author-request / 26 self-initiated batch / 7 RfD. ~122 were Emma's OWN deletions
(author-request + batch) → leave unless she says.

RECOVERY via FANDOM (Emma's steer — don't rely on labels alone; the QID is saved discreetly in
`dd=` for some ills and is in the fandom page HISTORY for the rest; fandom is NOT
Cloudflare-blocked). `crossref_deleted_labels.py` (rebuilt against shinto.fandom.com, verified
live from dev) finds the fandom `{{ill|<label>|…}}` for each recovered label and pulls the
per-language langlinks (recreation content — they survive the `qid=DELETED_QID` overwrite),
the current ill qid (`dd=` recoveries), the host page, and (`--deep`) the ORIGINAL qid from
history (proven: `Niwa-tsume no Mikoto` → `Q135579706`, matches the RAG). Pure logic unit-tested
(8 cases, green). Report: `shinto_wiki_crossref.md/.json`. Also wired into
`recreate-deleted-crossref.yml` (weekly refresh).

Full `--deep` fandom run done: 272 labels → **215 matched, 213 with per-language langlinks,
203 with the original QID recovered from history AND validated against the RAG** (+ host-page
categories + jawiki sitelink + context per item). Report: `shinto_wiki_crossref.md/.json`.
The ~122 self-deleted (author-request + batch) are **moot — confirmed NOT on the wikis**
(0/122 labeled, 0/15 sampled QIDs referenced on fandom); dropped from scope. Recreation
surface = the ~213 fandom-matched, langlink-bearing items (203 QID-anchored).

Vetting/enrichment of the ~213 candidates — SUBSTANTIALLY DONE (2026-07-06 session). Built
the enrich pipeline (`enrich_country.py` P17=Japan, `enrich_p31.py` extended, `enrich_relations.py`
familytree+infobox, `dedup_humans.py`). State (2026-07-06 latest): **188/213 typed** (P31; 3 are
P279 subclasses — wa mirror / imitation mirror / calendar maker), 85 with P17=Japan, 38 humans
(14 with cited family relations incl. the full Kamibe `{{familytree}}` lineage + Abe genealogy;
4 dedup-flagged), median 59 labels each, descriptions on all typed. Also flagged: **7 duplicates**
of live items (balneology→Q789523, Ne no Kuni→Q7555425, herbal baths→Q16496694, Kōshin-dō→Q124683618,
Futagoyama Park dab→Q110799681, Kansei 12→Q6875 [year 1800], Bunka 1→Q6894 [year 1804] — relink,
don't recreate) and **1 non-item EXCLUDED** (recreation_candidate=false: Kamado Town 2510-1, a
street address). Full per-bucket
readiness: `recreate-deleted-wikidata/items/_recreation_readiness.md`. Remaining AUTONOMOUS work:
- [ ] The **~13 still-untyped real items** (Shimabara Sea, court offices 御匙/御鑰, Kyoto's Three
  Kumano, Ōtsuki Hotel, Color Index, Inner Palace, Nakatomi Sakado clan, Kibi no Anaumi,
  Kimi-no-Mori, Shōkyō, Benten Chigo, rope attachment projections, Hozumi-Suzuki Clan Genealogy;
  + verify JR Ise Sangu Line & rhyolitic welded tuff which likely duplicate an existing line/rock
  item). NOTE (corrected 2026-07-06): these are **ill-TARGETS** (sub-topics inside `{{ill}}`), so
  they are redlinks on BOTH wikis — that is EXPECTED, not a fandom/miraheze discrepancy. Their host
  pages exist on both (verified 27/27 miraheze=fandom=YES) and the langlink content is already in
  the item JSONs. There is nothing page-wise to pull/fix; recreating them is purely the human-gated
  Wikidata-item task. Remaining autonomous step: assign each a P31 (a few need per-item research).
- [ ] **Analyze the `User:Immanuelle/` draft pages** (Emma 2026-07-06): the ills carry
  `13=User:Immanuelle/<name>` draft targets. Enumerate those draft pages on shinto.miraheze.org,
  read them, and try to deal with them (they may hold intended content for the deleted items /
  be promotable / be stale). Feeds the recreation dataset.
- [ ] Optional per-item data for the ready set: **P131** (admin territory, from host-page place)
  and coordinates — authoritative only.
Recreation itself + the min-claim-set + verifying the dedup-flagged are **NEEDS-DECISION (Emma)**
→ see "Blockers awaiting Emma" below.

Pinned tail (keep last, always):
- [ ] Run the status-report action once more independently as an end-of-session summary.

---

## Blockers — parked at queue end (awaiting Emma; mirrored to [[Open questions]] 2026-07-05)

These are the not-done items that need Emma's decision/action or are deferred by her explicit
instruction. The work-loop skips them (they're parked, not top-actionable). Autonomous work
items (vet the 213 candidates; per-target enrichment RAG) stay in their sections above.

- [ ] **NEEDS-DECISION (Emma) — recreate the deleted items? + min claim set per type.** The
  fandom crossref recovered ~213 deleted Immanuelle items (203 QID-anchored) with per-language
  content (`recreate-deleted-wikidata/shinto_wiki_crossref.md`). The ~122 self-deleted are moot
  (not on the wikis). Decision needed: (a) do you want the recoverable set recreated on Wikidata
  at all; (b) the minimum viable claim set per target-type (person / shrine / facility / concept)
  that survives Wikidata deletion review. Actual creation is human-gated + off-limits autonomously
  (CLAUDE.md WD rules); nothing goes to Wikidata without your go-ahead.

- [ ] **OUT-OF-SCOPE / deferred by Emma — `Template:Ill` wrongful-deletion fix** (investigate
  only when reached). The fandom bot deletes `shinto.fandom.com/wiki/Template:Ill` on a recurring
  schedule ("Bot: no Shinto equivalent time triggered pipeline"; observed 2026-06-30, 2026-07-05
  — recurs every few days). Root cause: the "delete fandom pages with no miraheze equivalent" op
  likely isn't counting a miraheze REDIRECT as an equivalent, so it wrongly orphans+deletes it.
  - **IMMEDIATE MITIGATION (Emma — critical, do first):** make `Template:Ill` a git-synced page
    on BOTH wikis (force-present on miraheze + fandom) so the equivalence check passes and the
    sync restores it if deleted.
  - **ROOT-CAUSE FOLLOW-UP:** make the no-equivalent check follow/count redirect targets on the
    miraheze side before deleting (fandom delete-orphans / fandom-cleanup pipeline).

- [ ] **OUT-OF-SCOPE / needs a build decision — long-tail language transliterators.** `th` Thai
  (33/135 labels) needs a real Thai transliterator (pre-posed vowel signs) — build only as its
  own deliberate task. `pa/km/lo/dz/new/mad/shn` (≤16 labels each): no script converter, 0-2
  observed labels. `cdo`: zero observed labels, mixed-script wiki. Parked with evidence; revisit
  only if Emma wants a transliterator built or a converter arrives.
