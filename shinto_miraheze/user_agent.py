"""THE canonical User-Agent for MIRAHEZE + FANDOM requests — strictly segregated from Wikidata's.

Emma 2026-07-14: every wiki request the bot makes must use this exact User-Agent. It used to be
copy-pasted into ~86 places with drifting values; now it lives here and everything imports it.
To change the wiki-side UA, edit the one string below.

Emma 2026-08-18 — the segregation rule, which is operational security, not style:

    "contact@emmaleonhart.com for miraheze and fandom / immanuelleleonhart@gmail.com for wikidata
     […] if you use the wrong one on either one of the bots, it'll basically be complete
     operational risk. We have strictly segregated user agents for the two of them."

    "The mirahaze one should be different from the Wikidata one for very, very, very important
    reasons […] because politically we're in a different situation with mirahaze and Wikidata."

    shinto_miraheze/user_agent.py           USER_AGENT           -> shinto.miraheze.org + fandom
    shinto_miraheze/wikidata_user_agent.py  WIKIDATA_USER_AGENT  -> wikidata.org / WDQS / QuickStatements

Fandom shares THIS string, by her instruction the same day. Wikidata must never see it, and the
Immanuelle identity must never appear here. `tests/test_user_agent_segregation.py` enforces both
directions; if it fails, do not relax the assertion.

Why 3.1 exists, since the history is instructive: shinto.miraheze.org has been Cloudflare-blocked
since 2026-07-11 (the Sunday edit-test failed 07-19 through 08-16 and the lockout gate has kept
every writing workflow skipping its wiki steps, so the bot has made effectively no wiki requests
for five weeks). The farm allowlists bots **by User-Agent**, which is why this string now carries
the bot, its on-wiki user page, the source repo and a monitored contact address. 3.0 briefly used a
work address; 3.1 is the address Emma chose for the wiki-facing identity.

**Changing this string can un-allowlist the bot** — if the farm keyed an entry to the exact UA,
editing it here silently drops us back behind the challenge. Tell them before changing it.

**A UA is a claim, so keep it true.** No browser impersonation on any path that touches the wiki:
a bot claiming to be Chrome is exactly the traffic the farm's ~2M requests/day problem is made of,
and it is why blanket challenges exist in the first place.

Consumers import it with a run-context-independent bootstrap (the scripts are launched both as
`python3 dir/foo.py` and as `python3 -m shinto_miraheze.foo`, from several directories), e.g.:

    import os, sys
    _r = os.path.dirname(os.path.abspath(__file__))
    while _r != os.path.dirname(_r) and not os.path.isdir(os.path.join(_r, "shinto_miraheze")):
        _r = os.path.dirname(_r)
    if _r not in sys.path:
        sys.path.insert(0, _r)
    from shinto_miraheze.user_agent import USER_AGENT
"""

USER_AGENT = (
    "EmmaBot/3.1 "
    "(https://shinto.miraheze.org/wiki/User:EmmaBot; "
    "+https://github.com/EmmaLeonhart/shintowiki-scripts; "
    "contact@emmaleonhart.com)"
)
