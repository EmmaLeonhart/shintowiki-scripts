"""The two bot identities must never leak into each other's User-Agent.

Emma, 2026-08-18: *"if you use the wrong one on either one of the bots, it'll basically be complete
operational risk. We have strictly segregated user agents for the two of them. Wikidata cannot
associate contact@emmaleonhart.com with me."*

So this is not a formatting test. It asserts that:

  * the Wikidata UA carries the Immanuelle identity and NOTHING that names the wiki-side persona —
    not the contact address, not a work address, and not a `github.com/EmmaLeonhart/...` source
    link, which is the innocuous-looking one that would hand Wikidata the association;
  * the Miraheze/Fandom UA carries the wiki-side identity and never names Immanuelle;
  * the two strings are not equal, and neither is derived from the other.

If this test fails, the fix is the UA, never the assertion.
"""
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from shinto_miraheze.user_agent import USER_AGENT
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT

# Tokens that identify the wiki-side (Emma Leonhart / Topaz) persona. None may appear in the
# Wikidata UA. "emmaleonhart" covers both the contact address and the GitHub org in a source link.
WIKI_SIDE_TOKENS = ("emmaleonhart", "emma@", "topazcomputing", "topaz", "emmabot")

# Tokens that identify the Wikidata-side persona. None may appear in the Miraheze/Fandom UA.
WIKIDATA_SIDE_TOKENS = ("immanuelle",)


def test_wikidata_ua_names_no_wiki_side_identity():
    low = WIKIDATA_USER_AGENT.lower()
    leaked = [t for t in WIKI_SIDE_TOKENS if t in low]
    assert not leaked, (
        f"Wikidata User-Agent leaks the wiki-side identity {leaked}: {WIKIDATA_USER_AGENT!r}. "
        "Wikidata must not be able to associate the two personas."
    )


def test_miraheze_ua_names_no_wikidata_side_identity():
    low = USER_AGENT.lower()
    leaked = [t for t in WIKIDATA_SIDE_TOKENS if t in low]
    assert not leaked, (
        f"Miraheze/Fandom User-Agent leaks the Wikidata identity {leaked}: {USER_AGENT!r}."
    )


def test_the_two_agents_are_distinct():
    assert USER_AGENT != WIKIDATA_USER_AGENT
    assert USER_AGENT.split("/")[0] != WIKIDATA_USER_AGENT.split("/")[0]


def test_each_agent_carries_a_contact_address():
    # A UA with no way to reach the operator is what gets a bot blanket-blocked.
    for name, ua in (("miraheze", USER_AGENT), ("wikidata", WIKIDATA_USER_AGENT)):
        assert re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", ua), f"{name} UA has no contact address: {ua!r}"


def test_expected_contact_address_on_each_side():
    # Pinned deliberately: these two addresses are the decision, and a silent swap is the failure.
    assert "contact@emmaleonhart.com" in USER_AGENT
    assert "immanuelleleonhart@gmail.com" in WIKIDATA_USER_AGENT


# --- ua_for(): the runtime resolver used by scripts that talk to both sites -----------------

from shinto_miraheze.ua_for import ua_for  # noqa: E402


def test_ua_for_routes_wikidata_hosts_to_the_wikidata_agent():
    for url in (
        "https://www.wikidata.org/w/api.php",
        "https://query.wikidata.org/sparql",
        "https://quickstatements.toolforge.org/api.php",
        "www.wikidata.org",
    ):
        assert ua_for(url) == WIKIDATA_USER_AGENT, url


def test_ua_for_routes_wiki_and_fandom_hosts_to_the_wiki_agent():
    for url in (
        "https://shinto.miraheze.org/w/api.php",
        "shinto.miraheze.org",
        "https://shinto.fandom.com/api.php",
    ):
        assert ua_for(url) == USER_AGENT, url


def test_ua_for_refuses_unknown_hosts_rather_than_guessing():
    # Failing closed is the point: a default is how one site's identity reaches another.
    for bad in ("https://example.com/api.php", "https://en.wikipedia.org/w/api.php", ""):
        try:
            ua_for(bad)
        except ValueError:
            continue
        raise AssertionError(f"ua_for({bad!r}) returned a UA instead of refusing")


def test_no_wikidata_only_script_still_imports_the_wiki_agent():
    """The sweep's invariant, checked against the tree rather than trusted."""
    import os, re
    wd = re.compile(r"wikidata\.org|query\.wikidata|quickstatements", re.I)
    mh = re.compile(r"miraheze\.org|fandom\.com|wikia\.", re.I)
    offenders = []
    for dirpath, dirnames, files in os.walk(_ROOT):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", "node_modules"}]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            if os.path.basename(p) in ("ua_for.py", "test_user_agent_segregation.py"):
                continue
            t = open(p, encoding="utf-8", errors="replace").read()
            if "user_agent import USER_AGENT" not in t:
                continue
            # A wikidata-only script must not hold the wiki identity at all.
            if wd.search(t) and not mh.search(t):
                offenders.append(os.path.relpath(p, _ROOT))
    assert not offenders, (
        "these Wikidata-only scripts still import the Miraheze/Fandom User-Agent: " + ", ".join(offenders)
    )
