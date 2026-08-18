"""THE single canonical bot User-Agent — the one and only spot it is defined.

Emma 2026-07-14: every wiki/API request the bot makes must use this exact
User-Agent. It used to be copy-pasted into ~86 places with drifting values;
now it lives here and everything imports it. To change the bot's UA, edit the
one string below.

Consumers import it with a run-context-independent bootstrap (the scripts are
launched both as `python3 dir/foo.py` and as `python3 -m shinto_miraheze.foo`,
from several directories), e.g.:

    import os, sys
    _r = os.path.dirname(os.path.abspath(__file__))
    while _r != os.path.dirname(_r) and not os.path.isdir(os.path.join(_r, "shinto_miraheze")):
        _r = os.path.dirname(_r)
    if _r not in sys.path:
        sys.path.insert(0, _r)
    from shinto_miraheze.user_agent import USER_AGENT

--------------------------------------------------------------------------
2026-08-18 — bumped to 3.0, and the reason matters for anyone reading this later.

shinto.miraheze.org has been behind a Cloudflare block since 2026-07-11; the
Sunday edit-test has failed every week since (07-19, 07-26, 08-02, 08-09,
08-16) and `wiki_editing_lockout.state` has kept every writing workflow gated
off, so the bot has made effectively no wiki requests for five weeks. The farm
side (PetraMagna, 2026-08-18) explained why: shintowiki is being scraped at
about **2 million requests/day** with almost no legitimate traffic, so bots are
challenged by default and have to be allowlisted **by User-Agent**.

That makes the UA an identity we hand to a stranger who is deciding whether to
trust it, so it now carries everything needed to hold us accountable for a
request: the bot, its on-wiki user page, the source repo it runs from, and a
**work** contact address that is monitored — not the personal gmail that was
here before, and emphatically not the pre-name-change address still sitting in
some of the older sibling pipelines.

Two rules that follow from being on an allowlist, both easy to get wrong:

  1. **Changing this string can un-allowlist the bot.** If the farm has keyed an
     allowlist entry to the exact UA, editing it here silently drops us back
     behind the challenge. Tell them before changing it, not after.
  2. **A UA is a claim, so keep it true.** No browser impersonation on any path
     that touches the wiki — a bot claiming to be Chrome is exactly the traffic
     the 2M/day problem is made of, and it is why blanket challenges exist.
"""

USER_AGENT = (
    "EmmaBot/3.0 "
    "(https://shinto.miraheze.org/wiki/User:EmmaBot; "
    "+https://github.com/EmmaLeonhart/shintowiki-scripts; "
    "emma@topazcomputing.com)"
)
