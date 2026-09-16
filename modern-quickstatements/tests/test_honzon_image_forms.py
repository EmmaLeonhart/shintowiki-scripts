"""秘仏 and 仏像 are QUALIFIERS on the deity statement, not values beside it.

Emma, 2026-09-13, shown that `Q11595955` 秘仏 hibutsu was the sixth most-emitted
value in `honzon_p825.txt` (53 of 834 lines): ***"hibitsu and buddharupa are
qualifiers"***, then ***"qualifiers on the other thing"***.

They arrive by the same parse damage as 重要文化財 — the generator takes every
wikilink out of the jawiki 本尊 field, and a temple infobox writes

    |本尊 = [[阿弥陀如来]]（[[秘仏]]）

— but they need the opposite remedy. "Dedicated to Important Cultural Property"
asserts nothing and is deleted; "this Amitābha is a concealed image" is true and
is relocated onto the Amitābha statement as `P3831` (object has role).

**The rule is positional**, and that is what most of this file pins: the field is
read in order, so a form qualifies the deity most recently seen in it. Getting
that wrong in either direction is silent — attach to the wrong deity and the claim
is false; attach to none and 62 lines of real information are dropped.

Measured 2026-09-13 over all 115 distinct values in the file: the Buddharupa root
reaches exactly four, and every one is a form rather than a deity — 秘仏 (53
lines), 仏像 itself (7), 涅槃仏 Reclining Buddha (1), 磨崖仏 magaibutsu (1). No
buddha or bodhisattva is under it. That measurement is why the root is a class
rather than a list, and `test_the_root_holds_no_deity` keeps it honest.
"""

import collections
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

DEITY = "Q236242"          # 阿弥陀如来 Amitābha
DEITY2 = "Q854773"         # 薬師如来 Bhaiṣajyaguru
HIBUTSU = "Q11595955"      # 秘仏 — a form
BUDDHARUPA = "Q1000809"    # 仏像 — a form
DESIGNATION = "Q1188622"   # 重要文化財 — invalid, deleted not moved

# Every member of IMAGE_FORM_ROOTS that the file actually contained, measured
# 2026-09-13 against all 115 distinct values. The class walk needs the network;
# this list does not, so the data check below can run offline. If the root ever
# widens, this widens with it.
KNOWN_FORMS = (
    "Q11595955",   # 秘仏 hibutsu        53 lines
    "Q1000809",    # 仏像 Buddharupa      7
    "Q2921452",    # 涅槃仏 Reclining Buddha  1
    "Q11239248",   # 磨崖仏 magaibutsu    1
)
URL = 'https://ja.wikipedia.org/wiki/X'


def _mod():
    if MQ not in sys.path:
        sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        "_gen_honzon_forms", os.path.join(MQ, "generate_honzon_quickstatements.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _emit(links, referenced=()):
    """Run one temple's field through the generator. `links` are jawiki titles;
    they resolve to themselves here so the test reads as the field does.

    `referenced` is the skip set, and it is the pairs whose P825 statement ALREADY
    CARRIES A REFERENCE — not merely the pairs that exist. See
    test_honzon_is_referenced.py; a bare statement is deliberately re-emitted so
    the citation can reach it.
    """
    mod = _mod()
    lines, counts = [], collections.Counter()
    mod.emit_for_temple(
        lines, counts, "Q1", URL, links,
        resolved={t: t for t in links},
        refused={DESIGNATION},
        forms={HIBUTSU, BUDDHARUPA},
        referenced=set(referenced))
    return sorted(h + t for h, t in lines), counts


def test_a_form_after_a_new_deity_becomes_an_inline_qualifier():
    lines, counts = _emit([DEITY, HIBUTSU])
    assert lines == [f'Q1|P825|{DEITY}|P3831|{HIBUTSU}|S143|Q177837|S4656|"{URL}"']
    assert counts["qualified"] == 1
    # One statement, not two. The whole point is that the form stops being a value.
    assert len(lines) == 1


def test_the_qualifier_sits_between_the_value_and_its_sources():
    """House style, and the shape reisai.txt already uses. direct_daily_edits
    sorts trailing P/S pairs either way round, so this is about the file being
    readable and consistent rather than about it executing."""
    lines, _ = _emit([DEITY, HIBUTSU])
    body = lines[0]
    assert body.index("|P3831|") < body.index("|S143|")


def test_a_form_after_a_CITED_deity_becomes_a_qualifier_only_line():
    """The case that carries most of the value: the honzon has already landed AND
    is cited, so there is no new statement to hang the form on inline. Without
    this the qualifier would simply never be emitted for any temple already
    imported — which, temple P825 being 96.8% referenced, is nearly all of them."""
    lines, counts = _emit([DEITY, HIBUTSU], referenced=[("Q1", DEITY)])
    assert lines == [f'Q1|P825|{DEITY}|P3831|{HIBUTSU}']
    assert counts["qualified"] == 1 and counts["dup"] == 1


def test_a_form_attaches_to_the_deity_it_follows_not_the_first_one():
    """「[[阿弥陀如来]] [[薬師如来]]（[[秘仏]]）」 — the form describes 薬師, the link
    before it. Attaching to the first deity in the field would assert something
    the article does not say."""
    lines, _ = _emit([DEITY, DEITY2, HIBUTSU])
    assert f'Q1|P825|{DEITY}|S143|Q177837|S4656|"{URL}"' in lines
    assert f'Q1|P825|{DEITY2}|P3831|{HIBUTSU}|S143|Q177837|S4656|"{URL}"' in lines
    assert len(lines) == 2


def test_a_form_with_no_deity_before_it_is_dropped_and_counted():
    """Nothing to qualify. Guessing at the temple's other statements would be
    inventing the claim; a count makes the population visible if it ever matters."""
    lines, counts = _emit([HIBUTSU, BUDDHARUPA])
    assert lines == []
    assert counts["orphan_form"] == 2 and counts["qualified"] == 0


def test_a_designation_is_still_deleted_rather_than_moved():
    """The two remedies must not converge. 重要文化財 is meaningless in this
    position in either slot, so it is refused outright and never becomes a
    qualifier."""
    lines, counts = _emit([DEITY, DESIGNATION])
    assert lines == [f'Q1|P825|{DEITY}|S143|Q177837|S4656|"{URL}"']
    assert counts["invalid"] == 1 and counts["qualified"] == 0


def test_the_two_root_sets_stay_separate_and_use_the_role_property():
    mod = _mod()
    assert mod.IMAGE_FORM_ROOTS == {"Q1000809"}, (
        "the image-form root changed; re-measure it against every value in "
        "honzon_p825.txt before trusting it — a wider root takes real deities")
    assert not (mod.IMAGE_FORM_ROOTS & mod.INVALID_HONZON_ROOTS), (
        "a class cannot be both deleted and moved")
    assert mod.FORM_QUALIFIER == "P3831"


def test_the_root_holds_no_deity():
    """The check that made the class safe to use, kept as an assertion rather than
    a memory. These are the six largest values in the file; every one is a buddha
    or bodhisattva and none may ever be treated as a form."""
    mod = _mod()
    deities = {"Q236242", "Q11644537", "Q124684411", "Q854773", "Q193849", "Q337624"}
    assert not (deities & mod.IMAGE_FORM_ROOTS)
    assert not (deities & mod.INVALID_HONZON_ROOTS)


def test_no_batch_still_emits_a_form_as_a_value():
    """The file is regenerated by CI, so this goes green on the next run rather
    than now. It is the check that the ruling actually reached the data."""
    import glob
    import re
    offenders = []
    for path in glob.glob(os.path.join(MQ, "*.txt")):
        for i, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
            line = line.strip()
            if not line or line.startswith("-"):
                continue
            if re.match(rf"^Q\d+\|P825\|(?:{'|'.join(KNOWN_FORMS)})(?:\||$)", line):
                offenders.append(f"{os.path.basename(path)}:{i}")
    assert not offenders, (
        "these give an image form as the P825 VALUE rather than as a P3831 "
        f"qualifier on the deity: {offenders[:5]}")
