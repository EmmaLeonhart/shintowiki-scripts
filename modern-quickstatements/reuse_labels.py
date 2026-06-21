"""
reuse_labels.py — Stage 2 rule logic: reuse an English label from another
shrine that shares the identical Japanese name.

Pure, offline-testable. The SPARQL that gathers the candidate readings lives in
generate_identical_name_en_labels.py; this module only decides, given the
candidate en labels (and their frequencies) for one target shrine, which label
to assign and whether to add an alias.

Rules (queue.md A2, from Emma's prose):
  - The dominant reading (strictly highest count among same-ja-name shrines that
    have an en label) becomes the label. Ties -> pick one at random.
  - Add an alias ONLY when there is exactly one OTHER distinct reading (exactly 2
    distinct readings total). With 3+ distinct readings, add no alias (too messy).
  - The random tie-break is deterministic per QID, so a shrine's chosen label is
    stable across daily runs and never churns on Wikidata.
"""

import random
from typing import Dict, Optional, Tuple


def choose_label(candidates: Dict[str, int], qid: str) -> Optional[Tuple[str, Optional[str]]]:
    """Pick (label, alias) for a target shrine from candidate en readings.

    ``candidates`` maps each distinct en label seen on a same-ja-name shrine to
    the number of shrines bearing it. Returns ``(label, alias_or_None)``, or
    ``None`` when there are no candidates (nothing to reuse — defer to Stage 3).
    """
    if not candidates:
        return None

    n = len(candidates)
    max_count = max(candidates.values())
    tied_max = sorted(label for label, c in candidates.items() if c == max_count)

    if len(tied_max) == 1:
        label = tied_max[0]
    else:
        # Deterministic per-QID random pick among the tied-dominant readings.
        label = random.Random(qid).choice(tied_max)

    # Alias only when exactly one OTHER distinct reading exists (n == 2).
    if n == 2:
        alias = next(lbl for lbl in candidates if lbl != label)
    else:
        alias = None

    return (label, alias)
