# Description enrichment pipeline — collision groups & the translation chain

> # ⭐ SUPERSEDED IN PART — Emma's ruling, 2026-08-21. Read this block first.
>
> **Descriptions are minor, programmatic, and disposable.** Her words:
> *"the thing about descriptions is that they are all kinda bullshit. Just a grammatically right
> fill in the blanks statement in each language."* And: *"descriptions are kinda bullshit and can
> just be treated as minor things to be programmatically generated and if one does not work then
> try another programmatically generated one."*
>
> **What this retires:** the collision-group design below, insofar as it routes descriptions
> through per-item CLOUD research to write "informative, distinguishing" text. That is the path
> that produced the 63 description work-files, and on 2026-08-21 Emma looked at them and said
> *"is just a random ronsha and nothing is wrong with it"* / *"Are we just discussing indonesian
> descriptions? Nothing serious?"*. **Do not spend per-item research on a description.** The
> uniqueness mechanics documented below are still correct and still load-bearing; it is the
> *response* to a collision that changes — iterate the generator, do not research the item.
>
> ## THE ALGORITHM — per item, per language, in this order
>
> | # | condition (in this language) | action |
> |---|---|---|
> | **1** | **no label, HAS a description** | **REMOVE the description** |
> | **2** | no label, no description | ADD a label |
> | **3** | HAS a label, no description | ADD a programmatically generated fill-in-the-blanks description — ideally `Shinto shrine in <location>` |
> | **4** | the description is REJECTED | try again with an **iteration on the algorithm** — a different generated form, never hand research |
>
> **Applies identically across all languages.**
>
> ## Why step 1 is the "extremely important caveat", in her words
>
> *"The problem with it is that many items can have the same label and empty descriptions, and many
> items can have the same description and an empty label, but once the two of them are both filled
> then it rejects edits to one to avoid duplication. Since labels are overwhelmingly more important
> than descriptions, it follows that any description on an item without a label is actively
> harmful."*
>
> The constraint is on the **(label, description) pair**. Either field alone may repeat freely. So a
> description sitting on an item that has **no label** is not neutral — it is a **claim staked on
> one half of a pair**, and it is the half that matters least. When the label finally arrives, the
> completed pair can collide with an existing item and the *label* edit is what gets rejected.
>
> **A description with no label costs a label. That is the entire argument, and it is why removal
> comes first rather than last.**
>
> Order matters for the same reason: 1 clears the obstruction, 2 supplies the thing that actually
> matters, 3 only then decorates, and 4 keeps 3 cheap.


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
