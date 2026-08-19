"""No script may build a User-Agent by hand. The two identities must never meet in one string.

Emma, on the segregation: "This particular thing is extremely important... if you use the wrong one
on either one of the bots, it'll basically be complete operational risk... Wikidata cannot associate
contact@emmaleonhart.com with me."

The constants and ua_for() enforce that -- but only for code that USES them. Three scripts had
hand-built UA strings that bypassed the whole mechanism, found 2026-08-19:

  * recreate-deleted-wikidata/rag_deleted_logs.py sent
        "EmmaBot/1.0 (https://shinto.miraheze.org/wiki/User:Immanuelle; <wikidata contact>)"
    to www.wikidata.org -- the wiki-side bot name, the Miraheze URL and User:Immanuelle in ONE
    header. It had even been half-fixed: the email came from contact('wikidata') while the
    persona-mixing prefix stayed. A partial fix reads as a fixed file.
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
