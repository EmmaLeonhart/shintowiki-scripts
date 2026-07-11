# What is happening with Q135040786 (Izumo, 意宇郡) — the two 韓国伊太弖 shrines

Emma, Open questions 2026-07: *"I want you to write a relatively comprehensive report on
what the fuck might be happening with this thing."* This is that report. The browsable
version is `_site/izumo-karakuni.html`
(<https://emmaleonhart.github.io/shintowiki-scripts/izumo-karakuni.html>). Report only —
nothing here has been edited on Wikidata. Prior write-up: `engishiki_list_defects_2026-07.md §1`.

## One sentence

[`Q135040786`](https://www.wikidata.org/wiki/Q135040786) 坐韓国伊大弖神社 is a **single item
standing in for two different register entries** — 意宇郡 entry 28 (韓国伊**大**弖, a 境内社 in
揖夜神社's grounds) and entry 39 (韓国伊**太**弖, a 境内社 in 佐久多神社's grounds) — and both
the item and the list carry the damage, so untangling it needs a **new item**, which the
QuickStatements pipeline cannot mint.

## The two shrines the register actually distinguishes

意宇郡 has two 同社坐 (境内社 — shrines standing *inside* another shrine's precinct) whose names
differ by a single character:

| entry | register name | 大/太 | host shrine (境内 of) | Kokugakuin |
|---|---|---|---|---|
| **28** | 同社坐韓国伊**大**弖神社 | 大 | 揖夜神社 ([Q11498399](https://www.wikidata.org/wiki/Q11498399), entry 27) | — |
| **39** | 同社坐韓国伊**太**弖神社 | 太 | 佐久多神社 ([Q135040907](https://www.wikidata.org/wiki/Q135040907), entry 38) | — |

They are genuinely two shrines, in two different precincts, eleven entries apart. Wikidata has
**one** item for both — `Q135040786`, labelled with the 大 spelling (entry 28).

## What the item claims (live, three P361 statements)

`Q135040786` carries three `part of` statements at once:

| # | part of | ordinal | follows | followed by | reading |
|---|---|---:|---|---|---|
| 1 | list `Q11395853` | **28** | 揖夜神社 (27) | 筑陽神社 (29) | **correct for entry 28** |
| 2 | 揖夜神社 `Q11498399` | — | — | — | **correct** — the 境内社 host link for entry 28 |
| 3 | list `Q11395853` | **39** | 佐久多神社 (38) | 志保美神社 (40) | **describes entry 39** — a different shrine |

Statement 3's neighbours (follows 佐久多神社, followed by 志保美神社) are exactly entry 39's
position. So the *39 half* of this item is entry 39's membership, grafted onto entry 28's item.
The host-shrine link it is **missing** is a `part of` 佐久多神社 — because that half never got
its own item.

## What the list claims (live, has-part side of `Q11395853`)

The list mirrors the mess differently:

```
ord 27  →  揖夜神社           Q11498399
ord 28  →  坐韓国伊大弖神社    Q135040786   ✓ correct
ord 29  →  筑陽神社           Q135040787   ✓ correct
ord 29  →  坐韓国伊大弖神社    Q135040786   ✗ SPURIOUS — same item duplicated onto 29
ord 38  →  佐久多神社         Q135040907
ord 39  →  (nothing)                        ✗ EMPTY HOLE — entry 39 belongs here
ord 40  →  志保美神社         Q135040909
```

The item's two list statements say **28 and 39**; the list's two say **28 and 29**. They agree on
28 and disagree on the second: the item put its 伊太弖 half at 39 (right), the list put a copy of
the same item at 29 (wrong, colliding with 筑陽神社). The 39 slot the item points to does not exist
on the list side. This is the fingerprint of the piped-link / merge import damage Emma described —
two entries with near-identical names collapsed into one item, and the fix-up landed in two
different places on the two sides.

## A third, separate defect on the same list

`Q11395853`'s `has part` also lists three **class/rank items** with no ordinal —
`Q134917286` (Shikinaisha, the P31 class itself), `Q134917287`, `Q134917288` (rank values). These
are not shrines; they are properties of shrines that leaked into the membership list during import.
Noted here, not part of the 韓国伊太弖 tangle.

## Why it cannot be a QuickStatement

The right end state is:

1. **Create a new item** for 同社坐韓国伊太弖神社 (entry 39, 太 spelling), 境内社 of 佐久多神社.
2. Move statement 3 (list@39, follows 佐久多神社) off `Q135040786` onto the new item, and add its
   host link `part of` 佐久多神社.
3. On the list, replace the spurious ord-29 → `Q135040786` with ord-39 → new item; leave ord-29 →
   筑陽神社 alone.
4. `Q135040786` keeps only statement 1 (list@28) and statement 2 (host 揖夜神社).

Step 1 mints an entity; steps 2–3 are value-matched removes on statements that share a value
(`Q135040786` appears on the list twice), which QuickStatements cannot target precisely. So the
whole thing is **out of the pipeline** until a new item exists — exactly Emma's read.

## Consequence being paid right now

`contested_entries()` withholds every entry sharing an ordinal from list-membership script 1. Because
ordinal 29 is contested (筑陽神社 and the spurious `Q135040786` both sit there), **`Q135040787`
筑陽神社 — a perfectly correct entry — gets no ordinal, no neighbours and no references** for as long
as ord 29 stays contested. That is the price of not guessing, and it clears the moment the spurious
ord-29 statement is removed.

**Emma 2026-07-10: report only, leave it.**
