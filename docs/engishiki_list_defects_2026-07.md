# Three defects in the Engishiki list data — found 2026-07-10

Background: `docs/engishiki_lists_primer.md`. These are the loose threads left by
`orphan_shikinaisha_2026-07.md`, run down one at a time. Nothing here has been edited on Wikidata.

## 1. Two entries the list names TWICE — and script 1 would have made it worse

The register lists each shrine once. Two list items name an entry at **two different ordinals**:

| entry | list | ordinals |
|---|---|---|
| [Q135040786](https://www.wikidata.org/wiki/Q135040786) 坐韓国伊大弖神社 | Izumo Province | **28 and 29** |
| [Q11361262](https://www.wikidata.org/wiki/Q11361262) 下立松原神社 | Awa Province | **3 and 5** |

This is the same piped-link import damage that hit the shrine items, surviving on the *list* side —
so the list, which is supposed to be the source of truth, is itself wrong in these two places.
Which ordinal is right cannot be read off the list.

**Script 1 was emitting one head line per ordinal.** Two lines, same item, same list, different
`series ordinal`. QuickStatements matches a statement by its *value*, so both would have found the
same statement and hung two rival ordinals on it — and both carried the neighbours of whichever
position `neighbours()` recorded last, so the ordinal-3 line wore ordinal-5's neighbours.

Fixed: `ambiguous_entries()` excludes them, `generate_list_membership_rebuild.py` emits nothing for
them and prints them, and six lines left the batch (5,643 → 5,637). Six tests pin it.

**The damage already exists on Wikidata, from the original import, not from us.** `Q11361262`
carries two `part of` statements to the Awa list, ordinals 3 and 5, *each* with two `follows` and
two `followed by` values. Our lines carry references; these have none. The batch has never run —
`conflict_gate` has been closed — which is the only reason we did not add to it.

*Recommendation: leave the live statements alone (a value-matched removal is exactly the wrong tool
here) and fix the two list items by hand, since the list is what is wrong. Two items.*

## 2. Thirteen named entries with no Kokugakuin id — and four of them never could have one

2,700 of the 2,713 named entries carry a Kokugakuin 式内社 database id. The 13 that do not:

**Four are not shrines at all — they are palace deities**, named by *List of Shikinaisha in the
Imperial Palace*: `Q11391709` 八神殿 (Hasshinden), `Q10928586` 座摩神, `Q135019513` 御門巫祭神 八座,
`Q135019813` 生島巫祭神 二座. The register's opening section lists the 宮中神, kami enshrined in the
palace itself — "eight seats", "two seats". The Kokugakuin database indexes *shrines*, so these have
no entry to point at. **Their missing id is correct, not a gap.**

**Nine are ordinary provincial entries** whose id was simply never matched: `Q116694076` 諸口神社
(Izu), `Q135039158` 大鳥北浜神社 (Izumi), `Q135040298` 野蚊神社 (Kaga), `Q135040786` 坐韓国伊大弖神社
and `Q135040970` 天若日子神社 and `Q135041051` 韓國伊太弖奉神社 (Izumo), `Q135041503` 同佐肆布都神社
(Iki), `Q135041552` 和多都美神社 (Tsushima), `Q135229657` 阿波遅神社 (Harima). All but one are ours,
created 2025-06.

*Recommendation: nothing to do. Script 1 already declines to claim a database reference for an entry
with no id — that path is tested. The four palace kami should never get one.*

## 3. `Q11474068` — the hot spring that really is a Shikinaisha

**Superseded 2026-07-10. The first version of this section recommended stripping three statements
off this item. That recommendation was wrong, and acting on it would have destroyed correct data.**

[Q11474068](https://www.wikidata.org/wiki/Q11474068) is **岩井温泉, Iwai Onsen**, a hot spring in
Iwami, Tottori — `instance of` **onsen**, **sulphur spring**, **Shikinaisha** and **Shinto shrine**.
It looked like a category error: our own bot added the Shikinaisha class on 2025-06-26, the jawiki
article is about the spa, and there is a register shrine at that spa (御湯神社, `Q135195567`).

It is not an error. Look at the Inaba list around it:

| ordinal | entry | what it is |
|---:|---|---|
| 6 | `Q21654507` 二上山 | a **mountain** — `mountain` + `Shikinaisha` + `Shinto shrine` + `Kokuhei-sha` |
| 7 | `Q11474068` 岩井温泉 | a **hot spring** — `onsen` + `sulphur spring` + `Shikinaisha` + `Shinto shrine` |
| 8 | `Q135040724` 日野神社 | an ordinary shrine |

Where the register's shrine is identified with a natural feature, the feature carries the shrine's
classes. The mountain at entry 6 does exactly what the spa at entry 7 does. And 御湯神社 is not the
same thing: it is a **Ronsha**, a disputed candidate, sitting at ordinal 1.

The onsen's own statement already says it is part of the Inaba list at **ordinal 7**, following
二上山 and followed by 日野神社 — precisely the slot the list leaves empty when it jumps from 6 to 8.

### The actual defect: one missing ordinal

The **list's** `has part` statement pointing at the onsen carries no `series ordinal`. That single
omission caused everything above: `list_members()` reads an ordinal-less has-part as a class count,
so the onsen was never a "named part", so it surfaced in the orphan report, so it looked like a
mis-tagged spa.

It is the **only** has-part statement across all 69 lists that lacks an ordinal without being a
class count — 196 of the other 197 carry a quantity qualifier and name a class
(`Shikinaisha` / `Taisha` / `Shōsha`).

**Fixed as an add**, queued in `miscellaneous_edits.txt`:

    Q11420254|P527|Q11474068|P1545|"7"

Nothing is removed. Once it lands, the onsen becomes a named part and script 1 treats it like any
other entry.
