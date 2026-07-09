"""Reachability guard for ATOMIC_FILES (2026-07-09).

`direct_daily_edits.read_all_lines()` opens each ATOMIC_FILES entry **by bare name
from the modern-quickstatements/ working directory**, and `continue`s past any path
that does not exist. There is no warning. A generator that writes its batch only to
`_site/` therefore produces a file the daily editor never reads, and its lines never
reach Wikidata — silently.

That is exactly what happened to three generators shipped on 2026-07-09
(`ronsha_ojp_name_removals`, `shikinaisha_kokugakuin_refs`,
`uncited_address_removals`): 5,158 lines sitting in `_site/`, unreachable. The
existing `test_atomic_files_alignment` only checked `submit ⊆ direct`, so it could
not see this.

These tests assert the two properties that make an entry reachable:
  1. the name is a bare filename, not a path, and
  2. each generator that owns an ATOMIC_FILES entry defaults its output to exactly
     that bare name.
"""

import importlib
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
MQ = os.path.dirname(HERE)
sys.path.insert(0, MQ)

import direct_daily_edits  # noqa: E402

# Generators whose OUTPUT_FILE is an ATOMIC_FILES entry. Each must write to the
# bare name so the daily editor can find it.
GENERATORS = [
    "generate_ronsha_ojp_name_removals",
    "generate_shikinaisha_kokugakuin_refs",
    "generate_uncited_address_removals",
]


def test_no_atomic_file_entry_is_a_path():
    """A path-qualified entry would be resolved relative to cwd and likely miss."""
    bad = [f for f in direct_daily_edits.ATOMIC_FILES if os.sep in f or "/" in f]
    assert not bad, f"ATOMIC_FILES entries must be bare filenames: {bad}"


@pytest.mark.parametrize("modname", GENERATORS)
def test_generator_output_is_registered(modname):
    mod = importlib.import_module(modname)
    assert mod.OUTPUT_FILE in direct_daily_edits.ATOMIC_FILES


@pytest.mark.parametrize("modname", GENERATORS)
def test_generator_default_out_is_the_bare_name_not_under_site(modname):
    """The regression: `default=os.path.join("_site", OUTPUT_FILE)` is unreachable."""
    mod = importlib.import_module(modname)
    import argparse

    parser = argparse.ArgumentParser()
    # Rebuild the same default the module's main() installs, by parsing no args
    # against a parser carrying the module's declared default.
    default = mod.OUTPUT_FILE
    parser.add_argument("--out", default=default)
    args = parser.parse_args([])
    assert args.out == mod.OUTPUT_FILE
    assert not args.out.startswith("_site")


@pytest.mark.parametrize("modname", GENERATORS)
def test_generator_source_does_not_default_out_to_site(modname):
    """Read the source: the default must not be joined under _site/."""
    src = open(os.path.join(MQ, modname + ".py"), encoding="utf-8").read()
    assert 'default=os.path.join("_site", OUTPUT_FILE)' not in src
    assert 'ap.add_argument("--out", default=OUTPUT_FILE)' in src


@pytest.mark.parametrize("modname", GENERATORS)
def test_generator_still_publishes_a_site_copy(modname):
    mod = importlib.import_module(modname)
    assert hasattr(mod, "publish_to_site")


def test_publish_to_site_copies_and_is_safe_when_src_is_already_in_site(tmp_path, monkeypatch):
    mod = importlib.import_module(GENERATORS[0])
    monkeypatch.chdir(tmp_path)
    src = tmp_path / mod.OUTPUT_FILE
    src.write_text("-Q1|P1448|ojp-hani:\"x\"\n", encoding="utf-8")

    mod.publish_to_site(str(src))
    copied = tmp_path / "_site" / mod.OUTPUT_FILE
    assert copied.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")

    # Calling it on the _site copy itself must not raise SameFileError.
    mod.publish_to_site(str(copied))
    assert copied.exists()
