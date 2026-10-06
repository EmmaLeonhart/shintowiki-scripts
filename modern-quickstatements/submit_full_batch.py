#!/usr/bin/env python3
"""Submit the ENTIRE QuickStatements batch through the QuickStatements API, once a day.

Emma, 2026-10-05: *"It should use this api key ... to attempt to run the entire
quickstatements batch every single day at noon. Submitting quickstatements and such. I was
intending on running it manually but it took way too long."*

The batch is exactly the site's home page: `site/build_qs_home.build()` is called here, at
submit time, so the lines are the current ones (every registered drip file,
sequential_misc.txt as one ordered block, every not-yet-created CREATE block), freshly
shuffled. The whole thing goes up as ONE batch, so blocks that must stay together still do.

The QS API path was retired on 2026-07-04 because the API refused every batch until the
account had run one batch by hand in the web UI. Emma has since run batches by hand, so
that precondition is met.

Env: QS_TOKEN (the QuickStatements API key), QS_USERNAME (the Wikidata username it
belongs to). Gated on shinto_miraheze/wikidata_editing_lockout.state like every other
Wikidata write path. `--dry-run` builds the batch and prints its size without submitting.
"""
import os as _uos, sys as _usys
_uar = _uos.path.dirname(_uos.path.abspath(__file__))
while _uar != _uos.path.dirname(_uar) and not _uos.path.isdir(_uos.path.join(_uar, "shinto_miraheze")):
    _uar = _uos.path.dirname(_uar)
if _uar not in _usys.path:
    _usys.path.insert(0, _uar)
from shinto_miraheze.wikidata_edit_allowed import editing_allowed
from shinto_miraheze.wikidata_user_agent import WIKIDATA_USER_AGENT
import io
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import build_qs_home  # noqa: E402

QS_API = "https://quickstatements.toolforge.org/api.php"
UA = WIKIDATA_USER_AGENT
MAX_RETRIES = 3
RETRY_DELAY = 60
# Emma, 2026-10-06: smaller batches are fine if the whole one will not go up. A 36,119-line
# "Run in background" from the web UI never became a batch; 9,002 commands had worked on 10-03.
CHUNK_LINES = 5000


def chunk_units(units, size=CHUNK_LINES):
    """Pack whole units into batches of at most `size` lines. A unit is never split, so
    CREATE blocks, ||-pairs and sequential_misc stay together; one bigger than `size` goes alone."""
    chunks, cur = [], []
    for u in units:
        if cur and len(cur) + len(u) > size:
            chunks.append(cur)
            cur = []
        cur.extend(u)
    if cur:
        chunks.append(cur)
    return chunks


def submit(lines, token, username, batch_name):
    """POST the batch. Returns (ok, message)."""
    try:
        r = requests.post(
            QS_API,
            data={
                "action": "import",
                "submit": "1",
                "format": "v1",
                "data": "\n".join(lines),
                "username": username,
                "token": token,
                "batchname": batch_name,
                "compress": "1",
            },
            headers={"User-Agent": UA},
            timeout=600,
        )
    except Exception as e:
        return False, "request failed: {}".format(e)
    if r.status_code != 200:
        return False, "HTTP {}: {}".format(r.status_code, r.text[:500])
    try:
        result = r.json()
    except ValueError:
        return False, "non-JSON response: {}".format(r.text[:500])
    if "batch_id" in result:
        return True, "batch created: #{} https://quickstatements.toolforge.org/#/batch/{}".format(
            result["batch_id"], result["batch_id"])
    return False, "API error: {}".format(result)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    dry = "--dry-run" in argv

    units = build_qs_home.build_units()
    chunks = chunk_units(units)
    lines = [l for c in chunks for l in c]
    creates = sum(1 for l in lines if l == "CREATE")
    print("batch: {:,} lines, {:,} item creations, {} chunks of <= {:,} lines".format(
        len(lines), creates, len(chunks), CHUNK_LINES))
    if dry:
        print("dry run: not submitted")
        return 0

    allowed, detail = editing_allowed()
    if not allowed:
        print("SKIPPED: " + detail)
        return 0

    token, username = os.environ.get("QS_TOKEN", ""), os.environ.get("QS_USERNAME", "")
    if not token or not username:
        print("QS_TOKEN and QS_USERNAME must both be set")
        return 1

    day = time.strftime("%Y-%m-%d", time.gmtime())
    created = 0
    for i, chunk in enumerate(chunks, 1):
        name = "shintowiki daily batch {} part {}/{}".format(day, i, len(chunks))
        for attempt in range(1, MAX_RETRIES + 1):
            ok, msg = submit(chunk, token, username, name)
            print("part {}/{} ({:,} lines) attempt {}: {}".format(i, len(chunks), len(chunk), attempt, msg))
            if ok:
                created += 1
                break
            if "OAuth" in msg or "HTTP 4" in msg or "do not match" in msg:
                if created == 0:
                    return 1            # the account is refused outright; the rest will be too
                break
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    print("{} of {} batches created".format(created, len(chunks)))
    return 0 if created == len(chunks) else 1

if __name__ == "__main__":
    sys.exit(main())
