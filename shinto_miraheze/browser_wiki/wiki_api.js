// Local wiki editing channel for shinto.miraheze.org (Emma, 2026-10-08).
//
// Scripts get a Cloudflare 403 from this machine and the CI runners are blocked by Miraheze, but
// Emma's Chrome session gets through, logged in as Immanuelle. This file is injected into a tab
// open on https://shinto.miraheze.org/ (claude-in-chrome javascript_tool) and drives the MediaWiki
// API with that session. Emma approved editing and undeleting as Immanuelle on 2026-10-08.
//
// Rules carried over from CLAUDE.md: THROTTLE 2.5 s between writes; every edit summary says it is
// Claude-assisted; every write is appended to shinto_miraheze/browser_wiki/edit_log.tsv by the
// session after the call returns.
//
// Usage (in the tab):  await shintoWiki.read("Title")
//                      await shintoWiki.edit("Title", text, "summary")
//                      await shintoWiki.undelete("Title", "reason")

window.shintoWiki = (() => {
  const API = "/w/api.php";
  const THROTTLE_MS = 2500;
  const TAG = " (Claude-assisted)";
  let last = 0;

  async function pace() {
    const wait = last + THROTTLE_MS - Date.now();
    if (wait > 0) await new Promise(r => setTimeout(r, wait));
    last = Date.now();
  }

  async function get(params) {
    const q = new URLSearchParams({ format: "json", formatversion: "2", ...params });
    const r = await fetch(API + "?" + q, { credentials: "include" });
    return r.json();
  }

  async function post(params) {
    const body = new URLSearchParams({ format: "json", formatversion: "2", ...params });
    const r = await fetch(API, { method: "POST", body, credentials: "include" });
    return r.json();
  }

  async function token() {
    const d = await get({ action: "query", meta: "tokens" });
    return d.query.tokens.csrftoken;
  }

  async function read(title) {
    const d = await get({ action: "query", prop: "revisions|info", titles: title,
                          rvprop: "content|timestamp|ids", rvslots: "main" });
    const p = d.query.pages[0];
    if (p.missing) return { title, missing: true };
    const rev = p.revisions[0];
    return { title: p.title, revid: rev.revid, timestamp: rev.timestamp,
             text: rev.slots.main.content };
  }

  async function edit(title, text, summary, basetimestamp) {
    await pace();
    const params = { action: "edit", title, text, summary: summary + TAG,
                     token: await token(), bot: "0" };
    if (basetimestamp) params.basetimestamp = basetimestamp;
    return post(params);
  }

  async function undelete(title, reason) {
    await pace();
    return post({ action: "undelete", title, reason: reason + TAG, token: await token() });
  }

  async function deletedRevisions(title) {
    return get({ action: "query", list: "deletedrevs", titles: title, drprop: "revid|timestamp|comment|user" });
  }

  return { read, edit, undelete, deletedRevisions, get };
})();
"shintoWiki ready";
