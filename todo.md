# Todo

Long-horizon backlog — genuine, not-yet-done tasks ONLY. Active session work is in [queue.md](queue.md); finished work + history in [DEVLOG.md](DEVLOG.md); how the pipelines/orchestrators work lives in [CLAUDE.md](CLAUDE.md) and `docs/` (e.g. `docs/remote_queue_pipeline.md`). Reference/narrative and completed/dropped items do NOT belong here.

## Label-generator horizons (merged 2026-07-04 from the subtree's deleted todo.md)

> Long-term goal: every Shinto shrine, temple, deity, and related entity on
> Wikidata labeled in all supported languages (reference: Q687168 with every
> language column filled). Formal expansion roadmap:
> [`docs/mass-label-expansion-plan.md`](docs/mass-label-expansion-plan.md);
> the active BFS-driven work is in `queue.md`.


## Repo / script tasks

- **Full program audit:** [`docs/program_audit_2026-06.md`](docs/program_audit_2026-06.md) (2026-06-05) — the single read-through of the whole machine: CI invocation graph, orchestrators+ops, legacy CI scripts, the Wikidata QS path, the sync/cloud-queue loop, known kludges, in-flight migrations, keep/fix/retire verdicts.


## Wiki content tasks

> ⚠ Most of this section was closed on 2026-09-17 (see the bottom of this file). [`docs/wiki_content_scripting_plans_2026-05.md`](docs/wiki_content_scripting_plans_2026-05.md) still holds the per-item designs, but its recommended build order names four things that are now won't-do — read it as history, not as a plan.

- [ ] **Translate category names in `[[Category:Japanese language category names]]`** → canonical English titles. Deterministic resolvers all SHIPPED (`generate_category_translation_moves.py`, wired monthly before `move_categories`): dated-maintenance transform + Wikidata-anchored resolver + phase-(c) place gazetteer (`の神社`→"Shinto shrines in X", `の寺院`/`の建築物`/`の歴史`/`の重要文化財`; jawiki→enwiki place + P31 gate; `の旧県社`/bare-`郡` verified as having no enwiki category convention → residual, 2026-07-06). **Everything the deterministic resolvers can't confidently name now routes to agentic RAG** (queue #5, 2026-07-06): `build_category_translation_queue.py` writes a work-file per residual category → the cloud remote routine researches the English name → `collect_category_translations.py` folds answers into `category_moves.csv`. So no "guessing-risk" gazetteer to hand-build and no dead human-only queue — the residual drains via RAG. Nothing left to build here.



## What was closed on 2026-09-17, and by whose word

Emma ruled on four give-up questions. Three closed things out; the fourth is recorded because the
question itself was wrong.

**Gave up on the uncovered 59 languages.** The 54 covered are the final set. The gate-failing ones
(`nan`/`hak`/`yue`/`wuu`/`ka`) fail for reasons a romanization table does not fix, and this file
already said there was no hand-build left to do.

**Closed as won't-do**, with their CI detection left running: the low-confidence ILL residue, the
7 double-category-QID dab pages, the multiple-`{{wikidata link}}` residual, the 26 interlanguage
pages with no Wikidata item, and the 9 large kokuzō articles. The ops that FIND these still run
every cleanup loop and still populate their review categories. What is gone is the promise that
anyone reviews the output.

**The wiki side is formally abandoned — and the machinery stays up.** Emma: *"we are formally
abandoning it but our abandonment means the machinery is still here and still indefinitely tries to
run."* So the syncs, the probes and the wiki-bound queue categories are **not** removed and **not**
disabled; they keep trying indefinitely and will simply start working again if Cloudflare ever stops
challenging the runners. What changed is that none of it is pending work any more, and it is not a
blocker to report. `FANDOM_SUNSET_DATE` needs no decision now — abandonment resolves it.

⛔ **The temple labels were NOT dropped, and asking was the error.** I put "13,288 temples, 45 years
at 1.1/day" as a give-up candidate. Emma: *"Of course not is this even a task ... I think this is
just an automated thing."* She is right and CLAUDE.md already says so: the drainer is designed to run
unattended indefinitely, so its rate is not a deadline and a horizon computed from it is not a
finding. **Do not re-open this, and do not compute a completion date for anything the drip owns.**
