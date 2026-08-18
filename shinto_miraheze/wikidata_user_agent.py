"""THE canonical User-Agent for WIKIDATA requests — strictly segregated from the wiki one.

Emma, 2026-08-18, and this is an operational-security rule, not a style preference:

    "This particular thing is extremely important […] if you use the wrong one on either one of
    the bots, it'll basically be complete operational risk. […] We have strictly segregated user
    agents for the two of them. Wikidata cannot associate contact@emmaleonhart.com with me."

    "There should be a standard Wikidata one and a standard mirahaze one, because politically
    we're in a different situation with mirahaze and Wikidata."

One standard UA per destination site, and the two identities must never meet:

    shinto_miraheze/user_agent.py           USER_AGENT           -> shinto.miraheze.org + fandom
    shinto_miraheze/wikidata_user_agent.py  WIKIDATA_USER_AGENT  -> wikidata.org / WDQS / QuickStatements

**Nothing that identifies the Miraheze-side persona may appear in the string below.** That means
no contact@emmaleonhart.com, no work address, and no `github.com/EmmaLeonhart/...` link — a source
URL looks harmless and is the easiest way to hand Wikidata the association she is keeping apart.
The Wikidata UA carries the Immanuelle identity and nothing else. The reverse holds too: the
Miraheze constant must not name Immanuelle.

`tests/test_user_agent_segregation.py` enforces both directions. If that test fails, do not
"fix" it by relaxing the assertion.

Do NOT merge these into one constant, do not import one from the other, and do not add a shared
fallback either can reach. The duplication is the whole point.

Why it needed fixing the same hour it was found: 71 Wikidata-facing scripts were importing the
MIRAHEZE constant, so a UA edit made for a Cloudflare allowlist request to the Miraheze farm
travelled straight onto every Wikidata edit path. A per-site constant is what stops a change made
for one host from reaching another.

Consumers use the same run-context-independent bootstrap as the Miraheze constant:

    import os, sys
    _r = os.path.dirname(os.path.abspath(__file__))
    while _r != os.path.dirname(_r) and not os.path.isdir(os.path.join(_r, "shinto_miraheze")):
        _r = os.path.dirname(_r)
    if _r not in sys.path:
        sys.path.insert(0, _r)
    from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
"""

WIKIDATA_USER_AGENT = (
    "ImmanuelleBot/1.0 "
    "(https://www.wikidata.org/wiki/User:Immanuelle; "
    "immanuelleleonhart@gmail.com)"
)
