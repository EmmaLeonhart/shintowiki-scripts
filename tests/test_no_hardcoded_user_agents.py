"""No script may build a User-Agent by hand. The two identities must never meet in one string.

The two agents are separate by design and must never be built by hand. Which agent a request
carries is decided by its destination, and nothing else.

The constants and ua_for() enforce that -- but only for code that USES them. Three scripts had
hand-built UA strings that bypassed the whole mechanism, found 2026-08-19:

  * recreate-deleted-wikidata/rag_deleted_logs.py built one header that mixed identifiers from
    both sides and sent it to www.wikidata.org. It had even been half-fixed -- the contact came
    from the right place while the rest of the string did not. A partial fix reads as a fixed file.
  * modern-quickstatements/generate_multi_p13677_page.py sent the Miraheze persona to the Wikidata
    API, and a spoofed "Mozilla/5.0 (compatible; EmmaBot/1.0; +https://shinto.miraheze.org/...)"
    to the Kokugakuin database.

So this test bans the pattern rather than the instances: a literal that looks like a User-Agent and
names a persona must not appear in source outside the two constant modules.
"""
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The only files allowed to spell a persona into a UA literal.
ALLOWED = {
    os.path.join("shinto_miraheze", "user_agent.py"),
    os.path.join("shinto_miraheze", "wikidata_user_agent.py"),
}
SKIP_DIRS = {".git", "__pycache__", "node_modules", "_site", "venv", ".venv"}

# A string literal that both looks like a UA (Name/version) and names one of the personas.
UA_LITERAL = re.compile(
    r"""["'][^"'\n]*?(?:EmmaBot|ImmanuelleBot|Mozilla)/[\d.]+[^"'\n]*?["']""")
PERSONA = re.compile(r"miraheze\.org|fandom\.com|User:Immanuelle|User:EmmaBot|@")


def _python_files():
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".py"):
                full = os.path.join(root, f)
                rel = os.path.relpath(full, REPO)
                if rel not in ALLOWED and os.path.basename(root) != "tests":
                    yield rel, full


def test_no_handbuilt_user_agent_naming_a_persona():
    offenders = []
    for rel, full in _python_files():
        with open(full, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                stripped = line.lstrip()
                if stripped.startswith("#"):
                    continue          # the fix notes quote the old strings on purpose
                for m in UA_LITERAL.finditer(line):
                    if PERSONA.search(m.group(0)):
                        offenders.append(f"{rel}:{n}: {m.group(0)[:90]}")
    assert not offenders, (
        "hand-built User-Agent naming a persona -- import USER_AGENT / WIKIDATA_USER_AGENT, or "
        "resolve it with ua_for(url):\n  " + "\n  ".join(offenders))


def test_ua_for_still_fails_closed_on_an_unknown_host():
    """The listing of jmapps must not have turned the router into a guesser."""
    import sys
    sys.path.insert(0, REPO)
    from shinto_miraheze.ua_for import ua_for
    for host in ("https://example.com/x", "https://shrine-db.invalid/a"):
        try:
            ua_for(host)
        except ValueError:
            continue
        raise AssertionError(f"ua_for({host!r}) returned a UA instead of refusing")


def test_no_module_level_user_agent_built_from_a_literal():
    """Stronger than the persona check: ban ANY hand-built agent, whatever it is named.

    The persona test above only fires on a literal naming EmmaBot / ImmanuelleBot / Mozilla.
    That was too narrow, and it hid the real scale of the problem: an audit on 2026-08-19 found
    roughly thirty distinct bot names in circulation -- ShintoWikiBot, ShintoOrchestrator,
    ShintoWikiLabels, ShintoWikiBeppyo, ShrineRankingPageBot, ShikinaishaListBot, ShintowikiPages,
    shintowiki-bunrei, shintowiki-descfix, and more -- across 58 files. None of them tripped a
    name-based check, and none of them matched the one agent string the wiki farm allowlists, so
    the requests carrying them could not succeed no matter what else was fixed.

    Fourteen of those literals also contained an unexpanded "{contact(...)}" -- a plain string
    where an f-string was meant -- so the agent went out carrying no contact address at all, just
    the source text of the interpolation.

    The rule this encodes: the agent is chosen by DESTINATION and comes from a constant or from
    ua_for(url). A module-level assignment to a UA-ish name whose value is a literal product token
    is banned outright, regardless of what it calls itself.
    """
    import ast

    UA_NAMES = {"USER_AGENT", "_USER_AGENT", "UA", "_UA", "UAW", "UAK", "WP_UA"}
    TOKEN = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*/[0-9][0-9.]*")
    offenders = []
    for rel, full in _python_files():
        with open(full, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            tgt = node.targets[0]
            if not isinstance(tgt, ast.Name) or tgt.id not in UA_NAMES:
                continue
            seg = ast.get_source_segment(src, node) or ""
            if TOKEN.search(seg):
                offenders.append(f"{rel}:{node.lineno}: {tgt.id} = {' '.join(seg.split())[:70]}")
    assert not offenders, (
        "module-level User-Agent built from a literal -- use USER_AGENT / WIKIDATA_USER_AGENT, "
        "or ua_for(url) at the request site:\n  " + "\n  ".join(offenders))


def test_no_unexpanded_contact_interpolation_anywhere():
    """A plain string containing "{contact(" ships the braces verbatim as the contact address."""
    offenders = []
    for rel, full in _python_files():
        with open(full, encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if line.lstrip().startswith("#"):
                    continue
                for m in re.finditer(r'(?<![fF])"([^"\n]*\{contact\([^"\n]*)"', line):
                    offenders.append(f"{rel}:{n}: {m.group(0)[:70]}")
    assert not offenders, (
        "unexpanded {contact(...)} in a plain string -- it is shipped literally, so the agent "
        "carries no contact at all. Use an f-string:\n  " + "\n  ".join(offenders))
