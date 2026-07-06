# shintowiki-scripts — Work Queue

**This file is a queue, not a state snapshot.** When an item is done, **DELETE it** — do not
annotate it "DONE" in place. Finished work lives in `DEVLOG.md` + `git log`; standing policy in
`CLAUDE.md`; pipeline/status detail in `docs/`. If a section has no `[ ]` checkbox, it does not
belong here.

Bulk LLM-grunge (duplicated_content reorg, need_translation, fandom fixup) lives in
`remote_queue.json` (claude.ai remote routine) — not duplicated here.

> **De-staled 2026-07-05 (Emma):** the queue had accumulated completed-work narrative
> (multilingual-label rollout, backlog board, provenance comments, the analysis pass — all
> shipped, see DEVLOG 2026-07-04..07-06) left in place instead of deleted, and had mis-filed
> easy autonomous work under "Blockers — parked/awaiting Emma." Those are removed / un-parked
> below. "Back of the queue" means **easy, do last** — NOT parked or deferred.

---

## 1. Context-dump audit — DO FIRST (potentially work-losing)

`context dump/` is committed (a deliberate safety net — losing it before we've mined it would be
real lost work). The goal is to delete it, but only after confirming nothing significant was
missed. Contents: `deleted.txt` (XTools export of 455 deleted Immanuelle Q-items — list only),
`chat dump.md` + two `*.html` session dumps (+ their `*_files/`). Prior analysis said the
actionable content is already extracted into the recreation pipeline (213 fandom-matched items;
the ~122 self-deleted are moot) — `docs/deleted_immanuelle_items_analysis_2026-07-05.md`.

- [ ] Re-audit every `context dump/` file against the shipped pipeline + docs. Confirm each
  actionable item is captured somewhere durable. If a genuine item was missed, queue it FIRST.
  Once clear, `git rm -r "context dump/"` and commit.

## 2. Recreate deleted Wikidata items — continue (Emma is running the CREATEs)

Dataset + generators live in `recreate-deleted-wikidata/`; readiness in
`items/_recreation_readiness.md`; handoff `docs/deleted_items_recreation_handoff_2026-07-06.md`.
Emma is actively creating the items via QuickStatements (human-gated) with a minimal claim set
(labels + P31/P279 + P17 + description); relinking the ills to the new QIDs as they land is the
autonomous follow-up. **Repair is disposable — do the dumb direct thing (text swaps), don't build
durable pipelines for it.**

- [ ] **Finish P31 typing of the 24 still-untyped candidates** (186/210 typed). Type only where a
  name signal is definitional; verify every new type QID live on Wikidata; NEVER guess. Leave
  genuinely-ambiguous ones for Emma. Named untyped tail: Shimabara Sea, court offices 御匙/御鑰,
  Kyoto's Three Kumano, Ōtsuki Hotel, Color Index, Inner Palace, Nakatomi Sakado clan, Kibi no
  Anaumi, Kimi-no-Mori, Shōkyō, Benten Chigo, rope attachment projections, Hozumi-Suzuki Clan
  Genealogy (+ verify JR Ise Sangū Line & rhyolitic welded tuff for existing-item duplicates).
- [ ] **Edit the ills on the 144 git-synced pages** (`[[Category:Pages with deleted QID in ill
  template]]`, pulled into `git_synced/`). Per `{{ill|…|qid=DELETED_QID}}`: sub-topics that are
  really **sections** → `[[Page#Section]]` (verify the section exists); real entities → relink to
  the created/live QID; duplicates → relink to the live QID. Un-sync each resolved page (remove
  `[[Category:Git synced pages]]` → next sync drops the on-wiki tag + local copy).
- [ ] **Optional per-item enrichment for the ready set:** P131 (admin territory from host-page
  place) + coordinates — authoritative only.
- [ ] **Analyze the `User:Immanuelle/` draft targets** (low). Precise extraction only:
  `13=User:Immanuelle/…` INSIDE `{{ill|…|qid=DELETED_QID}}` (a plain scan returns 2212 noise hits).
  Lower value now that recreation runs off minimal QuickStatements, not draft content.

## 3. `Template:Ill` wrongful-deletion fix (easy — was mis-parked)

The fandom bot recurrently deletes `shinto.fandom.com/wiki/Template:Ill` ("no Shinto equivalent"),
because the no-equivalent check doesn't count a miraheze **redirect** as an equivalent.

- [ ] **Mitigation (do this — it's easy):** make `Template:Ill` a git-synced page on BOTH wikis so
  the equivalence check passes and the sync restores it if deleted.
- [ ] **Root cause:** make the fandom delete-orphans / cleanup check follow/count miraheze redirect
  targets before deleting.

## 4. Long-tail language transliterators (build task)

- [ ] **Thai (`th`)** transliterator — real converter handling pre-posed vowel signs (33/135 labels
  currently). `pa/km/lo/dz/new/mad/shn` (≤16 labels each) and `cdo` have no script converter and
  near-zero observed labels — only pursue if a converter arrives. `python
  shinto-label-generator/language_registry.py` prints uncovered languages by label count.

## 5. Merged-QID redirect resolution op (LOW — keep at the very end; least time-dependent)

A Wikidata **merge** turns the old item into a *redirect* to the survivor (NOT deleted/"missing"),
so nothing canonicalizes it — `deleted_qids_in_ill` / `wikidata_lookup` only act on `"missing"`
entities and leave a `"redirects"` entity untouched. The stale QID still resolves but never updates.

- [ ] **Build an orchestrator op that rewrites merged QIDs on the wiki.** For each
  `{{ill|…|qid=Q…}}` (and consider `{{wikidata link}}`), query `wbgetentities`; if the entity is a
  redirect, rewrite the QID to the redirect **target** (follow the chain). Light op (text
  transform, orchestrator saves); throttle + 429-bail; cache QID→target per run. This is *durable*
  maintenance (merges happen forever), unlike the disposable recreation repair.

## Pinned tail (keep last, always)

- [ ] Ensure the 3 work-loop crons are running (work-loop :03, auto-flush :15, status-report :42).
- [ ] Run the status-report action once more independently as an end-of-session summary.
