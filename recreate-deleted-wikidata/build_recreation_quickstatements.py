#!/usr/bin/env python3
"""Build the FLESHED-OUT recreation QuickStatements from the enriched items/*.json —
the CREATE blocks that actually recreate the deleted items with enough content to
survive deletion review (labels + P31/P279 + P17 + description + family relations +
sitelink), NOT the bare-label stubs that got deleted the first time.

Emma 2026-07-06:
  * Recreate the REAL deletions; SKIP duplicates (any item flagged
    ``enrichment.possible_existing`` — those were relinked to a live item instead)
    and excluded non-items (``recreation_candidate`` false).
  * Only items with a P31/P279 are fleshed enough to recreate; untyped ones are held.
  * Labels: **English + Japanese + whatever other languages already exist** on the
    ill (``fandom.langlinks``) — NOT the 59-language transliteration expansion.
  * Sitelink: only where a safe jawiki sitelink exists (``fandom.ja_sitelink``).
  * Relations: emit P22/P25/P40/P3373/P21 only where the relative already has a live
    QID (deleted-relative links are added after the relative is itself recreated).

HUMAN-GATED — writes ``recreation_quickstatements.txt`` in this isolated dir; nothing
is auto-submitted (CLAUDE.md: QuickStatements pipeline only, human review first).
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
OUT = os.path.join(HERE, "recreation_quickstatements.txt")


def qs(value):
    """QuickStatements string literal — collapse quotes/pipes/newlines."""
    v = value.replace('"', "'").replace("|", "/").replace("\n", " ").strip()
    return f'"{v}"'


def _has_cjk(s):
    return any("぀" <= c <= "ヿ" or "㐀" <= c <= "鿿"
               or "豈" <= c <= "﫿" for c in s)


def _valid_label(lang, value):
    """Reject a CJK-script label (ja/zh/ko/…) that is actually romaji — the ill's
    langlink sometimes carries the romaji in the ja slot, which must NOT become the
    Japanese label. Latin-script languages pass through."""
    if not value:
        return False
    if lang.split("-")[0] in ("ja", "zh", "ko", "yue") and not _has_cjk(value):
        return False
    return True


def block(rec, deleted_qid):
    enr = rec.get("enrichment") or {}
    fa = rec.get("fandom") or {}
    langlinks = fa.get("langlinks") or {}
    en = rec.get("recovered_label") or fa.get("label") or ""
    host = (fa.get("host_pages") or ["?"])[0]

    lines = [f"# recreate {en or '(en name lost)'} (was {deleted_qid}) — from [[{host}]]",
             "CREATE"]
    # Labels: en + every original langlink (ja, de, zh, …). No translit expansion.
    if en:
        lines.append(f"LAST\tLen\t{qs(en)}")
    for lang, label in langlinks.items():
        if _valid_label(lang, label):
            lines.append(f"LAST\tL{lang}\t{qs(label)}")
    if enr.get("description_en"):
        lines.append(f"LAST\tDen\t{qs(enr['description_en'])}")
    # Instance-of / subclass-of.
    prop = enr.get("p31_property") or "P31"
    if enr.get("p31"):
        lines.append(f"LAST\t{prop}\t{enr['p31']}")
    # Country (places only).
    if enr.get("p17"):
        lines.append(f"LAST\tP17\t{enr['p17']}")
    # Family relations — only those whose target already has a live QID.
    for r in enr.get("relations") or []:
        if r.get("target_qid"):
            lines.append(f"LAST\t{r['property']}\t{r['target_qid']}")
    # jawiki sitelink (notability anchor) — only where a safe one exists.
    if fa.get("ja_sitelink"):
        lines.append(f"LAST\tSjawiki\t{qs(fa['ja_sitelink'])}")
    return lines


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    blocks, skipped_dup, skipped_untyped, skipped_excl = [], 0, 0, 0
    skipped_malformed, malformed = 0, []
    for f in sorted(glob.glob(os.path.join(ITEMS, "Q*.json"))):
        rec = json.load(open(f, encoding="utf-8"))
        deleted_qid = os.path.splitext(os.path.basename(f))[0]
        if not rec.get("recreation_candidate"):
            skipped_excl += 1
            continue
        enr = rec.get("enrichment") or {}
        if enr.get("possible_existing"):
            skipped_dup += 1
            continue
        if not enr.get("p31"):
            skipped_untyped += 1
            continue
        # A romaji value in the ja slot means the ILL was authored wrong (romaji where
        # the Japanese title belongs). Don't recreate a malformed ill — it needs fixing
        # to point at the actual thing (Emma 2026-07-06). Held out of recreation.
        ja = ((rec.get("fandom") or {}).get("langlinks") or {}).get("ja")
        if ja and not _has_cjk(ja):
            skipped_malformed += 1
            malformed.append((rec.get("recovered_label") or "", ja,
                              ((rec.get("fandom") or {}).get("host_pages") or ["?"])[0]))
            continue
        blocks.append("\n".join(block(rec, deleted_qid)))

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# FLESHED-OUT recreation QuickStatements — HUMAN-GATED, NOT auto-submitted.\n"
                 "# Labels = en + ja + existing langlinks (no translit expansion); +P31/P279, "
                 "P17, description, family relations (live-QID targets only), sitelink where safe.\n"
                 "# Duplicates (relinked to live items) and untyped items are excluded.\n\n")
        fh.write("\n\n".join(blocks) + "\n")

    print(f"Wrote {len(blocks)} CREATE blocks to {os.path.relpath(OUT, HERE)}")
    print(f"  skipped: {skipped_dup} duplicates (relinked), {skipped_untyped} untyped, "
          f"{skipped_excl} excluded non-items, {skipped_malformed} malformed-ill (romaji ja)")
    for en, ja, host in malformed:
        print(f"    MALFORMED ILL (fix, don't recreate): {en} — ja='{ja}' on [[{host}]]")
    print("\n=== sample block ===")
    print(blocks[0] if blocks else "(none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
