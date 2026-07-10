# Three defects in the Engishiki list data — found 2026-07-10

Background: `docs/engishiki_lists_primer.md`. These are the loose threads left by
`orphan_shikinaisha_2026-07.md`, run down one at a time. Nothing here has been edited on Wikidata.

## 1. Two entries the list names TWICE — diagnosed against the source articles

The register lists each shrine once. Two list items name an entry at **two different ordinals**:

| entry | list | ordinals |
|---|---|---|
| [Q135040786](https://www.wikidata.org/wiki/Q135040786) 同社坐韓国伊大弖神社 | Izumo Province | **28 and 29** |
| [Q11361262](https://www.wikidata.org/wiki/Q11361262) 下立松原神社 | Awa Province | **3 and 5** |

**Script 1 was emitting one head line per ordinal** — two lines, same item, same list, different
`series ordinal`. QuickStatements matches a statement by its *value*, so both would have found the
same statement and hung two rival ordinals on it; both also carried the neighbours of whichever
position `neighbours()` recorded last, so the ordinal-3 line wore ordinal-5's neighbours. Guarded by
`ambiguous_entries()`, and nothing is emitted for them.

Reading the jawiki source articles says which ordinal is right in each case. They are **two
different defects**, not one.

### Izumo: one item doing two entries' work — **report only** (Emma, 2026-07-10)

`Template:出雲国意宇郡の式内社一覧` runs: 須多神社 (26), 揖夜神社 (27), **同社坐韓国伊大弖神社** (28),
**筑陽神社** (29), 同社坐波夜都武自和気神社 (30) … 佐久多神社 (38), **同社坐韓国伊太弖神社** (39),
志保美神社 (40). The 同社坐 entries are 境内社 — shrines standing *inside* another shrine's grounds —
and 意宇郡 has **two** of them with near-identical names: 伊**大**弖 at 揖夜神社 (28) and 伊**太**弖 at
佐久多神社 (39).

Wikidata has one item for both. `Q135040786` is labelled 坐韓国伊大弖神社 — the 大 spelling, entry 28
— but **its own `part of` statement describes entry 39**: ordinal 39, following 佐久多神社, followed by
志保美神社. Meanwhile the list places it at 28 *and* at 29, and **ordinal 39 is an empty hole.**

So three things are wrong at once: a spurious statement at 29 (which is 筑陽神社, already there), a
hole at 39, and one item meaning two entries. Resolving it needs a **new item**, which is not a
QuickStatement.

**Emma 2026-07-10: report only, leave it.**

*Consequence, recorded rather than hidden:* `contested_entries()` withholds every entry sharing an
ordinal, so `Q135040787` 筑陽神社 — a perfectly correct entry — receives no ordinal, no neighbours
and no references from script 1 for as long as ordinal 29 stays contested. That is the price of the
guard, and it is the right price: the alternative is guessing.

### Awa: a piped link stole entry 3

`安房国の式内社一覧` runs: 安房坐神社 (1), 后神天比理乃咩命神社 (2), **天神社** (3), 莫越山神社 (4),
**下立松原神社** (5), 高家神社 (6). Entry 3's identified shrine is written as a **piped link** —
`[[下立松原神社#白浜町の下立松原神社|下立松原神社]]` — and the import followed the link instead of the
bold entry name. This is precisely the damage Emma described: *"a shrine that was part of another
shrine ended up getting piped in."*

The Kokugakuin ids prove it. Awa runs 181733 (2), then **181736** at 3, 181735 at 4, **181736**
again at 5, 181737 at 6. **181734 is missing entirely** — and it is held by
[Q137041912](https://www.wikidata.org/wiki/Q137041912) **天神社**, a complete entry item
(`Shikinaisha`, Kokugakuin id 181734) which carries **no list membership at all**. Its slot was taken.

*Fix, in two halves:*

* **The add, queued** in `miscellaneous_edits.txt`: `Q11450714|P527|Q137041912|P1545|"3"`.
* **The removal, by hand**: delete the list's `has part` → `Q11361262` statement carrying ordinal 3.
  It cannot be a QuickStatement — two statements share the value `Q11361262`, so a value-matched
  removal is as likely to take the correct one at ordinal 5.

### A second guard, because the add lands before the removal

Once `天神社` is added, ordinal 3 holds two entries until the hand fix happens. `contested_entries()`
now withholds every entry sharing an ordinal with a different entry — a position holding two entries
is not a position. It withholds `Q135040787` 筑陽神社 too, which *is* correct, because the list read
alone cannot say so. Three entries are currently unplaceable and the batch is 5,635 lines. Eleven
tests pin both guards.

**The damage already exists on Wikidata, from the original import, not from us.** `Q11361262` carries
two `part of` statements to the Awa list, ordinals 3 and 5, *each* with two `follows` and two
`followed by` values. Our lines carry references; these have none. The batch has never run —
`conflict_gate` has been closed — which is the only reason we did not add to it.

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
