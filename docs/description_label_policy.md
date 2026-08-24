# Descriptions and labels — Emma's four-step path (2026-08-21)

Authoritative for **every language**. Written down 2026-08-24 because it had been living only
in a chat message and in one script's docstring, while the answer on `[[Open questions]]`
still described the mechanism it supersedes. Emma, on that page: *"the pairs thing was
actually somewhat made obsolete by the content I added to open questions."*

## Her words

> If this is about descriptions well honestly the thing about descriptions is that they are
> all kinda bullshit. Just a grammatically right fill in the blanks statement in each language.
> With the extremely important caveat that we always remove descriptions from items without a
> label in that language, due to descriptions doing it
>
> here is the path
>
> 1. If item has no label and a description, remove the description
> 2. If item has no label or description, add a label
> 3. If item has a label and no description, add a programmatically generated fill in the
>    blanks description (ideally shinto shrine in location)
> 4. If the description is rejected, then try again with an iteration on the algorithm
>
> Applies the same across all languages.
>
> The problem with it is that many items can have the same label and empty descriptions, and
> many items can hae the same description and an empty label, but once the two of them are
> both filled then it rejects edits to one to avoid duplication
>
> Since labels are overwhelmingly more important than descriptions, it follows that any
> description on an item without a label is actively harmful

And, four minutes later, on whose data this is: *"MY work was aimed at fixing the ones added
by another person."*

## Why step 1 is step 1

Wikidata's uniqueness constraint is on the **(label, description) pair** in a language;
either field alone may repeat freely. A description on a label-less item stakes the half of
the pair that matters least. When the label finally arrives the completed pair can collide,
and it is the **label** edit that gets rejected. **A description with no label costs a label.**

So removal is not tidying. It clears an obstruction to the only field anyone reads.

## How this lands against the code that already existed

`modern-quickstatements/generate_description_fixes.py` has handled the same population since
Emma's 2026-07-07 spec, by a different remedy: set the standardised description **and** add
the label as one unit, 100/day, into `description_label_pairs.txt`.

**The two are not in conflict, and this is the reconciliation to keep.** The pairs pipeline
resolves an orphan description by *supplying the missing label* — which is exactly what step 1
is protecting. Step-1 removal is for the **residue**: items whose label the generator cannot
produce, so the description would sit there blocking nothing but a label that never comes.

That distinction is why a blanket removals file was the wrong shape. One was built on
2026-08-21 (`orphan_description_removals.txt`, 9,615 lines) without checking for the existing
pipeline; **3,511 items appeared in both files**, one setting a description and the other
clearing it, dripping in random order. It was unregistered and deleted, and
`modern-quickstatements/tests/test_orphan_description_removals.py` pins that it stays
unregistered. `audit_orphan_descriptions.py` survives as the **measurement**.

## Where it actually stands — measured 2026-08-24

`orphan_descriptions_audit.json`, descriptions on items with no label in that language:

| lang | orphan descriptions | labels the pairs file currently supplies |
|---|---|---|
| id | 5,024 | 5 |
| uk | 4,591 | 2,682 |
| nl | 168 | 163 |
| everything else | ~467 combined | small |
| **total** | **10,250** | — |

Two things follow, and neither is a guess:

- **id is not a data problem, it is the skipped-branch bug.** Emma's own 2025 bot pass had
  standardised every Indonesian description to `kuil Shinto di Prefektur {pref}, Jepang`, so
  `new == desc` held for all 5,024 and the generator `continue`d past them — dropping the
  label with the description. Fixed 2026-08-21 (`96e3cb6b`): that case now emits a
  **label-only** line through the same uniqueness check.
- **The fix is not visible yet.** `description_label_pairs.txt` still dates from 2026-08-02.
  It regenerates only on a **Sunday** step inside `generate-quickstatements.yml`, and that
  workflow was broken 08-19 → 08-22. The counts above are read from the stale file, so treat
  the id column as "before", not as evidence the fix failed.

The uk residue — roughly 1,900 items with an orphan description and no label coming from the
pairs pipeline — is the population step 1 is actually for. Size it against the **regenerated**
file, not this one.

## Step 4 is not implemented and should not be faked

"If the description is rejected, try again with an iteration on the algorithm" needs the
rejection to be observable. QuickStatements failures are not currently read back per line, so
there is nothing to iterate on. Do not invent a retry that cannot see a rejection.

⛔ Nothing here is deliverable before the Wikidata lockout lifts on **2026-09-18**
(`shinto_miraheze/wikidata_editing_lockout.state`). Staging is workable; delivering is not.
