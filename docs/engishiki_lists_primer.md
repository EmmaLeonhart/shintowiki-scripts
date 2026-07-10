# The Engishiki lists on Wikidata — what all of this actually is

Written 2026-07-10 because Emma said, fairly, *"a lot of these things are difficult because I don't
feel I have the necessary context to understand them."* Every question the bots have raised about
"list membership", "Ronsha", "orphans" and "duplicate part-of statements" is downstream of what
follows. Read this before reading any of those reports.

## The register

In 927 a register called the **Engishiki Jinmyōchō** (延喜式神名帳) listed about 2,800 shrines. It is
the ground truth for everything here.

On Wikidata, each province's portion is one **list item** — *List of Shikinaisha in Ōmi Province*,
and 68 others. A list item names its own entries with `has part` statements, each carrying a series
ordinal: entry 1, entry 2, entry 3.

Those entries are **records of what the register said**. They are not places you can visit. In
practice each one is an item, and nearly all of them (2,700 of 2,713) carry a Kokugakuin University
式内社 database id, because that database is the modern scholarly index of the register.

## The shrines standing today

Some modern shrines are confidently identified with a register entry. Those carry
`instance of: Shikinaisha` — a **confirmed** Shikinaisha.

For many entries, though, nobody knows which surviving shrine the register meant. Several shrines
each claim to be it. Those claimants are **Shikinai Ronsha** (式内論社), `instance of: Shikinai
Ronsha` — literally "disputed shrine". There are 2,323 of them.

**A Ronsha is a candidate, not a member.** Emma, 2026-07-09: *"Ronshas should not even have list
membership."* That single sentence resolves most of the work.

## What went wrong

Japanese Wikipedia's list articles used piped links. Where one shrine stood inside another shrine's
grounds, it got pulled into the list a second time. Emma, 2026-07-10:

> *"there was a large amount of pipe links in the list where there was a shrine that was part of
> another shrine, ended up getting piped in, resulting in massive duplications that have since been
> fixed."*

Fixed **in the list articles**. The individual shrine pages were never fixed, and Wikidata had
already imported from those. So today:

* the **list items are correct** — deduplicated, ordered, authoritative;
* **2,151 Ronsha claim membership of a list that never names them.**

## What the two scripts do

Neither script makes a judgement. The list decides, and the list is already right.

| | |
|---|---|
| `generate_list_membership_rebuild.py` (script 1, registered, drips) | For each of the 126 Ronsha a list **does** name, and every entry item: give its `part of` statement the ordinal, the previous and next entries, and two references. All derived from the list's own ordering, so the list stays the single source of truth. **Adds only.** |
| `generate_list_membership_removals.py` (script 2, unregistered, manual) | Take the `part of` statement away from the 2,151 the list does **not** name. **Removes only.** |

They are two scripts and not one because the daily batch runs its lines in random order, and because
**QuickStatements removes by value, not by statement id** — `-Q1|P361|Qlist` deletes *a* statement
pointing at that list. On an item holding both a good membership and junk aimed at the same list, it
could take the good one. Script 2 therefore never touches an item the list names.

## The residue — the only places anyone has to decide

Everything the bots have escalated lives here. None of it is urgent; all of it is recorded.

* **The 150 confirmed Shikinaisha no list names** (`orphan_shikinaisha_2026-07.md`). 84 are the same
  shrine twice: the list names the 927 entry, and a separate modern-shrine item also carries the
  confirmed class. 66 have no twin. *Emma: report only.*
* **22 duplicate `part of` statements** on named parts (`ronsha_list_membership_2026-07.md`). Three
  statements each saying the same true thing. QuickStatements cannot remove one identical twin and
  not the other, so no script can fix it. *Emma: report only.*
* **13 named entries with no Kokugakuin id**, and `Q11474068` — 岩井温泉, a **hot spring**, carrying
  the confirmed Shikinaisha class. Unexamined.
