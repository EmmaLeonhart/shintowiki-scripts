#!/usr/bin/env python3
"""Timed gate for the Nengo + torchhd item creations.

Emma 2026-07-16:
    "We create this stuff a month from now"
    "Just to be clear, this is a real task that I'm actually trying to get the
     shinto wiki scripts to run a month from now. This isn't something that Emma
     is going to do a month from now. This is something that you add to the shinto
     wiki scripts that runs a month from now, like a scheduled edit thing that runs
     a month from now."

So: her QS lives in vsa_libraries.txt, registered in ATOMIC_FILES, and this gate
keeps it shut until 2026-08-16 — a month out. After that the drip creates the two
items on its own schedule. No one has to remember.

TWO FIXES to her QS as dictated, both worth naming:

1. A MISSING `CREATE`. Her text had a bare "1." between the Nengo and torchhd
   blocks — the numbered-list artifact of exactly the speech-to-text truncation
   she flagged ("If there are instances where it appears like the bullet points
   just kinda end on my end, usually that indicates formatting fuckup"). Without
   a second CREATE, every torchhd statement would have been applied to the NENGO
   item: torchhd's label would have overwritten Nengo's, and Nengo would have
   ended up depending on PyTorch. Added.

2. torchhd had no P31 and no P277. Given the same treatment as Nengo —
   P31=Q188860 (software library), P277=Q28865 (Python) — since the description
   she wrote says "open-source Python library".

Everything else is verbatim hers. Properties verified live:
  P31 instance of · P277 programmed in · P856 official website
  P1324 source code repository URL · P1547 depends on software · P2283 uses
And neither item exists yet (checked 2026-07-16), so CREATE is correct.

Fails CLOSED: any error -> gate shut. The global conflict_gate still applies.
"""
import datetime

# Emma said this 2026-07-16, "a month from now" -> 2026-08-16.
#
# PUSHED OUT ANOTHER MONTH, 2026-08-16, by Emma: "Stop it until a month from now."
#
# Why she was asked: this gate was hours from opening (the workflow fires 09:37 UTC)
# and create-items.yml does NOT consult wikidata-daily-fire, so the enwiki-mention
# freeze of 2026-08-06 does not cover item creation at all. Her freeze says no
# Wikidata editing while "Immanuelle" is named on the AI noticeboard, and this
# path would have created two items straight through it.
#
# NOTE THE HOLE IS STILL OPEN. Moving this date stops THIS batch only. Any future
# gated batch registered in create_items.py GATES has the same bypass, because the
# workflow has no freeze check of its own. Emma chose the narrow fix when asked;
# widening it to a wikidata-daily-fire guard on create-items.yml is a separate call.
START_DATE = datetime.date(2026, 9, 16)


def is_open(today=None):
    """(open?, reason) — may the VSA-library creations run yet?"""
    today = today or datetime.date.today()
    if today < START_DATE:
        return False, (f"waiting until {START_DATE} (Emma's 'a month from now'; "
                       f"{(START_DATE - today).days}d left)")
    return True, f"open: past {START_DATE}"


if __name__ == "__main__":
    ok, why = is_open()
    print(f"vsa_libraries {'OPEN' if ok else 'CLOSED'}: {why}")
