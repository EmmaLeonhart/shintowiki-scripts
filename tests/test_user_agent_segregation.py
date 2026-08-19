"""The two bot User-Agents are separate and must stay separate.

`user_agent.USER_AGENT` serves shinto.miraheze.org and fandom; `wikidata_user_agent.WIKIDATA_USER_AGENT`
serves wikidata.org, WDQS and QuickStatements. They are defined independently, neither imports the
other, and no code path lets one stand in for the other.

These tests assert that mechanically, without hardcoding either value: each agent must carry its own
configured contact and not the other's, the two strings must differ, and the Wikidata agent must not
carry a source URL. If one of these fails, fix the User-Agent — not the assertion.
"""
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from shinto_miraheze.ua_contact import contact
from shinto_miraheze.ua_for import ua_for
from shinto_miraheze.user_agent import USER_AGENT
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT


def test_each_agent_carries_its_own_contact_and_not_the_others():
    mh, wd = contact("miraheze"), contact("wikidata")
    assert mh != wd, "both User-Agents resolved to the same contact"
    assert mh in USER_AGENT and wd not in USER_AGENT
    assert wd in WIKIDATA_USER_AGENT and mh not in WIKIDATA_USER_AGENT


def test_the_two_agents_are_distinct():
    assert USER_AGENT != WIKIDATA_USER_AGENT
    assert USER_AGENT.split("/")[0] != WIKIDATA_USER_AGENT.split("/")[0]


def test_each_agent_has_a_contact_address():
    # A UA with no route back to the operator is what gets a bot blanket-blocked.
    for name, ua in (("miraheze", USER_AGENT), ("wikidata", WIKIDATA_USER_AGENT)):
        assert re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", ua), f"{name} UA has no contact address: {ua!r}"


def test_the_wikidata_agent_carries_no_source_url():
    assert "github.com" not in WIKIDATA_USER_AGENT.lower()


def test_ua_for_routes_wikidata_hosts_to_the_wikidata_agent():
    for url in ("https://www.wikidata.org/w/api.php", "https://query.wikidata.org/sparql",
                "https://quickstatements.toolforge.org/api.php", "www.wikidata.org"):
        assert ua_for(url) == WIKIDATA_USER_AGENT, url


def test_ua_for_routes_wiki_and_fandom_hosts_to_the_wiki_agent():
    for url in ("https://shinto.miraheze.org/w/api.php", "shinto.miraheze.org",
                "https://shinto.fandom.com/api.php"):
        assert ua_for(url) == USER_AGENT, url


def test_ua_for_refuses_unknown_hosts_rather_than_guessing():
    for bad in ("https://example.com/api.php", "https://en.wikipedia.org/w/api.php", ""):
        try:
            ua_for(bad)
        except ValueError:
            continue
        raise AssertionError(f"ua_for({bad!r}) returned a UA instead of refusing")


def test_no_wikidata_only_script_imports_the_other_agent():
    """Checked against the tree rather than trusted: a Wikidata-only script must not hold the
    Miraheze/Fandom constant."""
    wd = re.compile(r"wikidata\.org|query\.wikidata|quickstatements", re.I)
    mh = re.compile(r"miraheze\.org|fandom\.com|wikia\.", re.I)
    offenders = []
    for dirpath, dirnames, files in os.walk(_ROOT):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", "node_modules", "tests"}]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            if os.path.basename(p) == "ua_for.py":
                continue
            t = open(p, encoding="utf-8", errors="replace").read()
            if "user_agent import USER_AGENT" not in t:
                continue
            if wd.search(t) and not mh.search(t):
                offenders.append(os.path.relpath(p, _ROOT).replace("\\", "/"))
    assert not offenders, (
        "these Wikidata-only scripts import the Miraheze/Fandom User-Agent: " + ", ".join(sorted(offenders))
    )


def test_wikimedia_projects_route_to_the_wikidata_agent():
    """en/ja Wikipedia, Commons and friends carry the same identity as Wikidata.

    Regression test for 2026-08-19: ua_for() fails closed on unknown hosts, and en.wikipedia.org was
    in neither list, so check_enwiki_mentions.py raised on every run. Its workflow reported that as
    "mentions remain" and the gate — which is designed to open by itself — silently froze.
    """
    for url in ("https://en.wikipedia.org/w/api.php", "https://ja.wikipedia.org/w/api.php",
                "https://commons.wikimedia.org/w/api.php", "https://en.wiktionary.org/w/api.php"):
        assert ua_for(url) == WIKIDATA_USER_AGENT, url
