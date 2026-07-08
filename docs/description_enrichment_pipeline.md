# Description enrichment pipeline — collision groups & the translation chain

Emma's design, 2026-07-07 (recorded verbatim in intent; treat as authoritative
alongside `docs/wikidata_shrine_festival_model.md`).

## Why descriptions are hard: the uniqueness constraint

Label+description combinations must be UNIQUE on Wikidata. The description is
the deduplicator for non-unique labels (八幡神社 ×1006, 諏訪神社 ×1004 …), so
standardized/generic descriptions COLLIDE wherever two same-labeled items get
the same description.

**The rule: every proposal set must be checked for uniqueness — internally
(proposals against each other) and externally (against existing Wikidata
label+description pairs) — before emission.** Colliding proposals are never
emitted as-is; they become collision groups (below).

Also strategic: English labels drain FIRST (each English label auto-translates
into many languages downstream), so description edits must not dominate the
daily drip early — hence the description-adds cap (50/day until 2027-01-01).

## Collision groups

Collisions are roughly the same across languages (the same 八幡神社s collide
everywhere), so a collision group — the set of items sharing a proposed
label+description pair in some language — is treated as a UNIT across
languages. Groups get informative, distinguishing descriptions built from each
item's Wikidata context via CLOUD operations (the remote routine), gradually
replacing the generic forms. Slow by design, dependent on collisions.

## The staged translation chain (per collision group)

1. **Japanese has no descriptions → English first.** Build English descriptions
   from: the English labels of all group members + the things they link to +
   the original proposed description.
2. **Next pass (separately, significantly later): Japanese from English.**
   For groups with unique English descriptions but Japanese incomplete/absent:
   inputs = the proposed Japanese label + Japanese labels of all linked things
   + the English labels and context. Japanese ≈ a translation of the English.
3. **Unique Japanese but no English → English from Japanese.** Inputs = full
   linked Japanese + English labels of linked things. English ≈ a translation
   of the Japanese.
4. **Later languages, each from its source:**
   * Mandarin Chinese ← translated from Japanese;
   * all other Chinese variants ← from Mandarin;
   * Korean ← from English;
   * every other language ← from English.

## Deity-name disambiguation test (2026-07-08) — measured, mostly NOT viable

Emma's hypothesis test: could P825 deity names in descriptions ("Shinto shrine
dedicated to Hachiman in …") disambiguate collision groups cheaply? English
measurement: 1,279 (label, prefecture) collision groups / 14,616 shrines.
Deity sets fully disambiguate **52 groups (4%)** today; the CEILING with full
P825 coverage is **14%** (73 of the 507 all-deitied groups) — same-named
shrines overwhelmingly enshrine the same deity, exactly as Emma suspected.
Verdict: use the deity form opportunistically for the groups it does resolve,
and as one context signal in the cloud stages, but it cannot replace the
pipeline. Corollary non-blocking: only 1 colliding item had a deity without an
English label. Side finding: 6,841 colliding shrines have NO P825 at all —
independent support for the jawiki 祭神 import
(`docs/jawiki_infobox_import_review_2026-07.md`).

## Current implementation state (2026-07-07)

* `ja` and `en` are NOT in the covered-language registry — no generator makes
  Japanese or English descriptions today; they arrive only via this pipeline.
* `generate_description_adds.py` implements the uniqueness rule: internal
  collision grouping + external check against existing same-class
  label+description pairs; unique-safe proposals → `description_adds.txt`
  (capped 50/day until 2027-01-01), colliders →
  `description_collision_groups.json` (the seed for the cloud stages above).
* `generate_description_fixes.py` (the desc-then-label pairs) predates the
  rule — retrofit queued.
* The cloud stages are NOT built yet; the collision-groups file is their
  designed input, to flow through the remote-queue work-file pattern
  (`docs/remote_queue_pipeline.md`).
