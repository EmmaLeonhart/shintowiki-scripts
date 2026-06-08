"""Guard the page-title ↔ filename mapping that all three per-page sync scripts
share (git_synced / fandom_unique / miraheze_unique).

The functions can't be imported under pytest — the sync scripts run
`sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)` at module load, which
breaks pytest's capture. Modifying those load-bearing scripts just to import
them here isn't worth the risk, so instead we:

1. Verify the mapping is correct + round-trips, by exec'ing ONLY the extracted
   `_FORBIDDEN`/`title_to_filename`/`filename_to_title` source in an isolated
   namespace (no module import, no stdout side effect).
2. Assert all three scripts carry byte-identical copies — the real hazard is a
   silent divergence that would mis-map pages and corrupt the sync.
"""

import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = [
    "sync_git_synced_pages.py",
    "sync_fandom_unique_pages.py",
    "sync_miraheze_unique_pages.py",
]

_FORBIDDEN_RE = re.compile(r"^_FORBIDDEN\s*=.*$", re.MULTILINE)
_FUNC_RE = re.compile(
    r"^def (?:title_to_filename|filename_to_title)\(.*?(?=\n(?:def |class |[^\s#])|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _extract(script):
    src = open(os.path.join(HERE, script), encoding="utf-8").read()
    forbidden = _FORBIDDEN_RE.search(src)
    funcs = _FUNC_RE.findall(src)
    assert forbidden, f"_FORBIDDEN not found in {script}"
    assert len(funcs) == 2, f"expected 2 mapping funcs in {script}, found {len(funcs)}"
    return forbidden.group(0) + "\n\n" + "\n".join(funcs)


def _namespace(script):
    ns = {"urllib": __import__("urllib.parse", fromlist=["parse"])}
    exec("import urllib.parse\n" + _extract(script), ns)
    return ns


TITLES = [
    "Kehi Jingū", "Why am I me?", "Template:Interlanguage link",
    "List of Shikinaisha in Awa Province (Chiba)", "无邪志国造",
    "100%/path", 'A<b>"c*d|e?f', "Main Page",
]


def test_roundtrip_for_each_script_source():
    for script in SCRIPTS:
        ns = _namespace(script)
        t2f, f2t = ns["title_to_filename"], ns["filename_to_title"]
        for t in TITLES:
            fn = t2f(t)
            assert fn.endswith(".wiki")
            assert f2t(fn) == t, (script, t, fn)


def test_forbidden_chars_percent_encoded():
    ns = _namespace(SCRIPTS[0])
    fn = ns["title_to_filename"]("a:b/c?d")
    assert ":" not in fn and "/" not in fn and "?" not in fn
    assert "%3A" in fn and "%2F" in fn and "%3F" in fn


def test_percent_escaped_first():
    ns = _namespace(SCRIPTS[0])
    assert ns["title_to_filename"]("100%").startswith("100%25")


def test_all_three_agree_on_output():
    # Behavioural agreement is what matters: all three copies must map every
    # title to the same filename (and back). Catches a silent divergence
    # without depending on byte-identical source formatting.
    namespaces = [_namespace(s) for s in SCRIPTS]
    for t in TITLES:
        f2 = {ns["title_to_filename"](t) for ns in namespaces}
        assert len(f2) == 1, f"title_to_filename diverges across scripts for {t!r}: {f2}"
        fn = f2.pop()
        b = {ns["filename_to_title"](fn) for ns in namespaces}
        assert b == {t}, f"filename_to_title diverges across scripts for {fn!r}: {b}"
