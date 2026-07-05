# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, delete it. Finished work lives in `git log` and `DEVLOG.md`. It fills up and you barrel through it during a session; clearing the queue = doing the items, not relocating them. Standing policy/notes do NOT live here — they go in `CLAUDE.md`.

Bulk LLM-grunge work (duplicated_content reorg, need_translation translation, fandom template fixup) lives in `remote_queue.json` and is worked by the claude.ai remote routine — not duplicated here.

---

## Standardization — deferred tails (need new transliterators; not CI-gated)

- **th** (33/135 labels): needs a real Thai transliterator (pre-posed vowel
  signs); build only as its own deliberate task.
- **pa/km/lo/dz/new/mad/shn** (≤16 labels each): no script converter, 0-2
  observed labels — revisit only if a converter arrives or Sonnet does them.
- **cdo**: zero observed labels, mixed-script wiki — parked with evidence.

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

**Remaining (NOT this session — recreation itself is out of scope, per Emma):**
- [ ] Per-target research to give each item enough content to not be auto-deleted again
  (Wikidata churn is the risk). The count (304, only ~36 with recovered QIDs) is small
  enough to research individually. Enrich `CREATE` blocks with whatever authoritative
  data can be found (claims, better sitelinks, descriptions) beyond the current
  labels+provenance.
- [ ] Decide the minimum viable claim set per target-type (person / shrine / facility /
  concept) that survives Wikidata deletion review.
- [ ] Only after review: feed vetted blocks through the QuickStatements pipeline
  (human-gated; still respect the WD-editing rules in CLAUDE.md).

## Next-session analysis pass — DONE (2026-07-05)

Written per-item "resolved / partial / not started + what's left" over all 8 backlog
problems shipped to `docs/backlog_resolution_status_2026-07-05.md`. Highest-value
remaining build thread flagged there: **#5 phase (c) tail** (later gazetteer suffixes +
misses). #8 per-target research is larger but content/Emma-gated.

---

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

- [ ] **NEEDS-DECISION (Emma) — recreate any of the ~122 self-deleted items?** author-request
  + self-initiated batch were Immanuelle's own deletions; recreating undoes her call. Flagged
  on `[[Open questions]]`. The ~180 truly-empty (`content was:""`) + RfD-no-evidence stay out.
- [ ] **NEEDS-INVESTIGATION (next loop) — vet the fandom crossref output** and feed the strong
  candidates (matched fandom page, langlinks recovered, no live wikidata link yet) through #8's
  human-gated generator. Run `--deep` for QID validation on the subset lacking a `dd=`.

## Stop removing history from miraheze (Emma 2026-07-05 — no longer necessary)

- [ ] **If miraheze history removal is still running, stop it.** The `history_offload` op
  (in every orchestrator's OPS, gated by `ENABLE_HISTORY_OFFLOAD=1` + `ENABLE_REVDEL=1`,
  destructive delete+recreate only on category ns 14 as of 2026-05-11) mirrors history to
  fandom+XML then delete+recreates the miraheze page to purge visible history. Emma: this
  isn't necessary anymore. INVESTIGATE whether any scheduled trigger / workflow-dispatch is
  still passing `enable_history_offload=true` (+ `enable_revdel`); if so, stop passing it (or
  disable the destructive stage). The fandom mirror it produced is actually load-bearing for
  the deleted-item recovery above — but the *miraheze* history purge is the part to stop.

Pinned tail (keep last, always):
- [ ] Ensure the three autonomous-loop crons (work-loop :03, auto-flush :15, status-report :42) are running; start them if this session hasn't.
- [ ] Run the status-report action once more independently as an end-of-session summary.

---

## END-OF-QUEUE (Emma-placed 2026-07-05 — investigate only when reached, not before)

- [ ] **Fandom `Template:Ill` keeps getting wrongly deleted — the "no miraheze equivalent"
  delete pipeline isn't covering redirects.** The fandom bot ("Their Eminence") deletes
  `https://shinto.fandom.com/wiki/Template:Ill` on a recurring schedule with summary
  "Bot: no Shinto equivalent time triggered pipeline" (observed 2026-06-30 08:29 and
  2026-07-05 08:07 — recurs every few days). It should NOT be deleted. Emma: this indicates
  our "delete fandom pages with no miraheze equivalent" op **isn't covering redirects** — the
  miraheze equivalent of `Template:Ill` is very likely a REDIRECT that the equivalence check
  doesn't count as "having an equivalent", so the op wrongly flags it as orphaned and deletes
  it.
  - **IMMEDIATE MITIGATION (Emma 2026-07-05 — critical, do this first to void the problem):**
    make `Template:Ill` a **git-synced page on BOTH wikis** (add it to the git-synced set so it
    is force-present on miraheze AND fandom). With a synced miraheze `Template:Ill` present, the
    "no miraheze equivalent" check passes and the recurring fandom deletion stops; the sync also
    restores it if deleted. Do this as the immediate fix.
  - **ROOT-CAUSE FOLLOW-UP:** make the no-equivalent check follow/count redirect targets on the
    miraheze side before deleting (likely in the fandom delete-orphans / fandom-cleanup pipeline).
