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

## 3. `Q11474068` — the Shikinaisha that is a hot spring

[Q11474068](https://www.wikidata.org/wiki/Q11474068) is **岩井温泉, Iwai Onsen**, a hot spring in
Iwami, Tottori. Its description says so: 鳥取県岩美町にある温泉. It is `instance of`: **onsen**,
**sulphur spring**, **Shikinaisha**, and **Shinto shrine**. It also claims to be part of the Inaba
Province list, which does not name it.

Our own bot added the Shikinaisha class on 2025-06-26. The jawiki article 岩井温泉 is about the spa,
and there is a register shrine at it (御湯神社); the import attached the shrine's class to the spa.

*Recommendation: drop `instance of: Shikinaisha`, `instance of: Shinto shrine`, and the Inaba list
membership from the onsen. All three are our own errors and none of them is disputable — a hot
spring is not a shrine. That is three removals, so it needs the enumerated-removal treatment
`miscellaneous_edits.py` already has for addresses, not a computed removal. Not done: nothing was
edited this tick.*
