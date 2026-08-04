"""Importing a generator must not run it.

2026-08-04: `generate_soja_only.py` had no `if __name__ == "__main__"` guard, so
importing it — to read a single constant during the SPARQL endpoint migration —
fired its migration queries and rewrote migrate_soja_add.txt /
migrate_soja_remove.txt. Nothing was lost only because both files happened to be
empty already.

That is the same shape as the CI bug fixed the same morning: a process rewriting
generated files it had no business touching. This test makes the guard a
standing property rather than a one-off repair, because the failure is silent —
an unguarded module looks completely normal until something imports it.
"""
import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)

# Generators: modules whose job is to produce output. A module that only defines
# functions/constants (kana_english, romaji_phonology, user_agent, ...) is meant
# to be imported and is not in scope here.
GENERATORS = sorted(
    f for f in os.listdir(MQ)
    if f.startswith(("generate_", "fetch_", "resolve_", "submit_", "select_"))
    and f.endswith(".py")
)


def test_there_are_generators_to_check():
    """Guard against the glob silently matching nothing and the suite passing
    vacuously."""
    assert len(GENERATORS) > 10


@pytest.mark.parametrize("name", GENERATORS)
def test_generator_has_a_main_guard(name):
    """Every generator must gate its work behind `if __name__ == "__main__"`.

    Checked textually rather than by importing: importing is precisely the
    dangerous act, and a module that fails this test would run its work during
    the test that was meant to catch it.
    """
    src = open(os.path.join(MQ, name), encoding="utf-8").read()
    assert '__main__' in src, (
        f"{name} has no `if __name__ == \"__main__\"` guard — importing it would "
        f"run its work. Wrap the module body in a main()."
    )


def test_soja_specifically_is_import_safe(monkeypatch):
    """The module that actually bit us, verified by import rather than by grep:
    it must define main(), reach no network, and leave its outputs alone."""
    import requests

    def _boom(*a, **k):
        raise AssertionError("network call during import")

    monkeypatch.setattr(requests, "get", _boom)
    monkeypatch.setattr(requests, "post", _boom)

    outs = [os.path.join(MQ, f) for f in
            ("migrate_soja_add.txt", "migrate_soja_remove.txt")]
    before = [os.path.getmtime(p) for p in outs if os.path.exists(p)]

    spec = importlib.util.spec_from_file_location(
        "generate_soja_only_undertest", os.path.join(MQ, "generate_soja_only.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert callable(mod.main)
    after = [os.path.getmtime(p) for p in outs if os.path.exists(p)]
    assert before == after, "importing the module rewrote its output files"


def test_soja_writes_relative_to_its_own_file():
    """Its two writes used bare filenames, so output landed wherever cwd was.
    CLAUDE.md requires __file__-relative paths for a script's own data."""
    src = open(os.path.join(MQ, "generate_soja_only.py"), encoding="utf-8").read()
    for fname in ("migrate_soja_add.txt", "migrate_soja_remove.txt"):
        assert f'open(_uos.path.join(HERE, "{fname}")' in src, (
            f"{fname} is written to a bare path; it must be HERE-relative")
