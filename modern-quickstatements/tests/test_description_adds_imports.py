"""`generate_description_adds.py` must import, and must use the inflection fix.

Two faults, found together on 2026-09-13 by reading the run log of a step that
had been reporting a warning nobody read.

**1. It was dead.** Commit 47b42aff (2026-09-11) made
`generate_description_fixes.py` label-only and deleted `pref_labels`, `pref_keys`
and `infer_templates` from it — correctly, because that script no longer composed
a description. It did not check the other importer, so this one died at import:

    ImportError: cannot import name 'pref_labels' from 'generate_description_fixes'

Nothing surfaced it. The step is `continue-on-error: true` with an `|| echo` that
attributed the failure to HTTP 429, so a deterministic import error was reported
as a rate limit for two weekly slots while `description_adds.txt` went on dripping
its 2026-08-25 content.

**2. It never had the inflection fix.** `infer_templates` matches the prefecture by
substring, and this call site passed the raw labels where the distinctive keys were
expected. Ukrainian labels the item «Префектура Наґано» and writes descriptions
«…у префектурі Наґано, Японія», so no label ever matched and every uk target fell
to the generic. `generate_description_fixes.py` was fixed on 2026-09-10; this
sibling was not, because the bug lives at the call site rather than in the shared
function.

An import test is worth having for its own sake here: this file is only executed
on Sundays, behind `continue-on-error`, so a breakage costs a week before anyone
could notice — and did.
"""

import importlib.util
import inspect
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
WORKFLOW = os.path.normpath(
    os.path.join(MQ, "..", ".github", "workflows", "generate-quickstatements.yml"))


def _load(name):
    if MQ not in sys.path:
        sys.path.insert(0, MQ)
    spec = importlib.util.spec_from_file_location(
        f"_t_{name}", os.path.join(MQ, f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_it_imports_at_all():
    """The whole of fault 1. Everything below depends on this passing."""
    mod = _load("generate_description_adds")
    assert callable(mod.main)


def test_the_template_helpers_live_in_this_module_now():
    """Not re-imported from the label-only sibling, which must not regrow them:
    composing a description is this script's job, per step 3 of
    docs/description_label_policy.md."""
    mod = _load("generate_description_adds")
    for name in ("pref_labels", "pref_keys", "infer_templates"):
        fn = getattr(mod, name, None)
        assert callable(fn), f"{name} is missing"
        assert fn.__module__.endswith("generate_description_adds"), (
            f"{name} is imported from elsewhere; it belongs to this script")

    fixes = _load("generate_description_fixes")
    for name in ("pref_labels", "pref_keys", "infer_templates"):
        assert not hasattr(fixes, name), (
            f"generate_description_fixes regrew {name} — it is label-only "
            "(47b42aff) and must not compose descriptions again")


def test_the_prefecture_keys_are_derived_before_inference():
    """Fault 2, asserted at the call site because that is where it lived."""
    src = inspect.getsource(_load("generate_description_adds").main)
    assert "pref_keys(pref_labels(lang))" in src, (
        "infer_templates is being handed raw prefecture labels again; it matches "
        "by substring, so every inflecting language falls back to the generic")
    assert not re.search(r"infer_templates\(\s*corpus,\s*prefs\s*\)", src), (
        "the pre-2026-09-10 call shape is back")


def test_pref_keys_survives_an_inflecting_language():
    """The behaviour, not just the call. Ukrainian is the case that exposed it:
    the generic word declines and the place-name does not, so the key must be the
    place-name alone."""
    mod = _load("generate_description_adds")
    keys = mod.pref_keys(["Префектура Наґано", "Префектура Осака", "Префектура Кіото"])
    assert "Наґано" in keys and keys["Наґано"] == "Префектура Наґано", keys
    # And the locative form the descriptions actually use is now matchable.
    desc = "синтоїстське святилище у префектурі Наґано, Японія"
    assert any(k in desc for k in keys), keys


def test_pref_keys_drops_an_elision_particle():
    """French labels the item "préfecture d'Okayama"; a frequency test alone
    leaves the "d" and the key becomes "d Okayama", which matches nothing and
    filled templates with "de d Okayama"."""
    mod = _load("generate_description_adds")
    keys = mod.pref_keys(["préfecture d'Okayama", "préfecture de Nagano",
                          "préfecture de Kyoto", "préfecture d'Osaka"])
    assert "Okayama" in keys, keys
    assert not any(k.startswith(("d ", "d'")) for k in keys), keys


def test_a_failing_step_no_longer_blames_wdqs():
    """The `|| echo` said "bailed (usually HTTP 429 from WDQS)" for an
    ImportError. Naming an unconfirmed mechanism is worse than naming none — it
    is what kept two weekly slots looking like an external problem."""
    # Command lines only. The comment above the corrected block quotes the old
    # wording to explain why it changed, and matching that instead of the `echo`
    # is a mistake three separate tests in this repo have now made in one day.
    text = "\n".join(l for l in open(WORKFLOW, encoding="utf-8").read().splitlines()
                     if not l.lstrip().startswith("#"))
    assert "usually HTTP 429 from WDQS" not in text, (
        "a step warning attributes its failure to WDQS without checking")
    assert "usually WDQS timeout" not in text
    assert text.count("do NOT assume WDQS") >= 3, (
        "the corrected wording is gone from one of the three weekly steps")
