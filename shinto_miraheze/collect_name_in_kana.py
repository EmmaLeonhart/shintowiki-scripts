#!/usr/bin/env python3
"""
collect_name_in_kana.py
=======================
Collector for the `name_in_kana/` work-queue (queue item A0). Scans the
work-files for a filled `<!-- ANSWER: ... -->` marker and turns each answer into
QuickStatements:

  * `KANA: <hiragana>`  -> `Qxxx|P1814|"<hiragana>"|S143|Q177837|S4656|"<url>"`
    into modern-quickstatements/name_in_kana.txt (atomic file; the single daily
    submitter drains it). P1814's datatype is `string`, not monolingual text —
    checked against the property itself — so the value takes bare quotes with no
    `ja:` prefix.
    For a BUCKET b item (no en label) the deterministic Stage-1 labeller
    (`kana_english.label_for`) also runs, and any label it can build confidently
    is appended to modern-quickstatements/kana_en_labels.txt, which
    select_label_proposals.py already drips.
  * `KATAKANA: <katakana>` -> recorded, NO Wikidata line. Katakana is the
    signature of the ancient-reading error the kana-qualifier cleanup exists to
    undo; P1814 wants modern hiragana.
  * `NO_KANA: <reason>`    -> recorded, no line.

THE GATE. A `KANA:` answer is written out only if it is hiragana (plus ー). One
katakana character, one kanji, one latin letter and it is rejected into the log
instead — the answer is a reading, and anything else in it means the reading was
not what got extracted. That is deliberately the ONLY gate: Emma's instruction is
not to over-gate on confidence, because producing kana is the priority.

Deterministic, idempotent, no network. Mirrors collect_label_typo_answers.py.

Usage: python collect_name_in_kana.py [--dry-run]
"""
import argparse
import io
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(ROOT, "modern-quickstatements"))

WORKDIR = os.path.join(ROOT, "name_in_kana")
QS_OUT = os.path.join(ROOT, "modern-quickstatements", "name_in_kana.txt")
LABEL_OUT = os.path.join(ROOT, "modern-quickstatements", "kana_en_labels.txt")
LOG = os.path.join(WORKDIR, "_resolved.log")

JAWIKI_ITEM = "Q177837"          # imported from Wikimedia project: Japanese Wikipedia

ANSWER_RE = re.compile(r"<!--\s*ANSWER:\s*(.*?)\s*-->", re.S)
QID_RE = re.compile(r"^(Q\d+)\.wiki$")
META_RE = re.compile(r"<!--\s*JA:\s*(.*?)\s*\|\s*EN_LABEL:\s*(.*?)\s*\|\s*"
                     r"BUCKET:\s*([ab])\s*-->")
ARTICLE_RE = re.compile(r"<!--\s*ARTICLE:\s*(\S+)\s*-->")

# ぁ-ゖ hiragana, ー the long-vowel mark, ゝゞ the iteration marks.
HIRAGANA_ONLY = re.compile(r"^[ぁ-ゖーゝゞ]+$")

# Any kana, and "does it contain hiragana at all". Together these express the
# real gate — see acceptable_reading().
KANA_ONLY = re.compile(r"^[ぁ-ゖァ-ヺーゝゞヽヾ]+$")
HAS_HIRAGANA = re.compile(r"[ぁ-ゖ]")


def acceptable_reading(kana):
    """True if this may be written to P1814.

    RELAXED 2026-08-05 on Emma's ruling. The gate used to demand pure hiragana,
    which also rejected readings that are legitimately part-katakana because the
    name contains a foreign place-name or loanword — ハワイだいじんぐう,
    ペリリューじんじゃ (Peleliu), スワトウじんじゃ, サムハラじんじゃ,
    アラハバキかみ. The colonial-era and overseas shrines make that a growing
    class, not a handful of oddities, and every one of them produced nothing.

    WHY RELAXING IS SAFE, which is Emma's own argument and was checked in the
    cleanup's code rather than assumed: the katakana this gate exists to keep out
    is the ancient-reading error, and the cleanup undoing it
    (`generate_kana_qualifier_remove.py`) only ever touches items carrying an
    **ojp-hani P1448** official name with a confirmed カミノヤシロ qualifier, and
    emits VALUE-MATCHED removals. An overseas shrine has no ojp-hani P1448 at
    all, so the cleanup cannot reach it and there is nothing to collide with.

    The shape separates the two cleanly. A legitimate case is always MIXED,
    because a shrine name ends in 神社/神宮/宮 and those read as hiragana. The
    error values are ALL katakana (アスキ-, ツキタノ-, カミノヤシロ). So: all
    kana, and at least one hiragana character.
    """
    if not kana or not KANA_ONLY.match(kana):
        return False
    return bool(HAS_HIRAGANA.search(kana))


def parse_answer(text):
    """(kind, payload) from a work-file body, or None while ANSWER is empty."""
    m = ANSWER_RE.search(text)
    if not m or not m.group(1).strip():
        return None
    ans = m.group(1).strip()
    km = re.match(r"(KANA|GUESS|KATAKANA|NO_KANA)\s*:\s*(.*)", ans, re.S)
    if not km:
        return ("MALFORMED", ans)
    return (km.group(1), km.group(2).strip())


def clean_kana(value):
    """Strip the punctuation a reading should never carry, then judge it."""
    v = re.sub(r"[\s・･,、。]+", "", (value or "").strip())
    v = v.strip("「」『』（）()【】\"'")
    return v


def already_staged(qs_out=None):
    """QIDs that already have a P1814 line in the staged file.

    The builder has had `already_handled()` since 2026-08-04; the collector had
    nothing, and it appends to the staged file unconditionally. That is the same
    duplicate-statement hazard from the other end: a line staged BY HAND leaves
    the work-file sitting in the queue directory, and whoever fills its ANSWER
    marker next — the remote routine, or a local batch — gets a second, identical
    P1814 statement appended for that item.

    Found 2026-08-20 with exactly one live instance: Q11544511 (機殿神社) was
    hand-staged on 2026-08-19 and its work-file never retired, so it still read
    as pending with an empty marker.

    Keyed on the staged file only, deliberately. `_resolved.log` also records
    REJECTED_/NOT_A_SHRINE outcomes, and those are the builder's business to not
    re-queue; here the question is narrower — does a statement for this item
    already exist to be duplicated.
    """
    done = set()
    path = qs_out or QS_OUT
    if os.path.exists(path):
        for line in io.open(path, encoding="utf-8"):
            m = re.match(r"^(Q\d+)\|", line)
            if m:
                done.add(m.group(1))
    return done


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(WORKDIR):
        print("no name_in_kana/ dir; nothing to collect")
        return

    from kana_english import label_for            # noqa: E402  (path set above)

    qs_lines, label_lines, resolved, done_files = [], [], [], []
    pending = rejected = skipped = 0
    staged = already_staged()
    for name in sorted(os.listdir(WORKDIR)):
        qm = QID_RE.match(name)
        if not qm:
            continue
        qid = qm.group(1)
        path = os.path.join(WORKDIR, name)
        if qid in staged:
            # Checked before the answer is read on purpose: the stale work-files
            # this catches have an EMPTY marker, so an answer-first order would
            # count them pending forever and never retire them.
            skipped += 1
            resolved.append(f"{qid}	ALREADY_STAGED	P1814 line already in "
                            f"{os.path.basename(QS_OUT)}")
            done_files.append(path)
            continue
        body = open(path, encoding="utf-8").read()
        ans = parse_answer(body)
        if ans is None:
            pending += 1
            continue
        kind, payload = ans
        meta = META_RE.search(body)
        ja, en_label, bucket = meta.groups() if meta else ("", "", "a")
        art = ARTICLE_RE.search(body)
        url = art.group(1) if art else ""

        if kind in ("KANA", "GUESS"):
            kana = clean_kana(payload)
            if not acceptable_reading(kana):
                rejected += 1
                why = ("ALL_KATAKANA" if KANA_ONLY.match(kana or "")
                       else "NOT_KANA")
                resolved.append(f"{qid}\tREJECTED_{why}\t{payload}")
                done_files.append(path)
                continue
            line = f'{qid}|P1814|"{kana}"'
            # THE REFERENCE IS THE DIFFERENCE BETWEEN THE TWO KINDS, and it is the
            # whole reason GUESS is a separate answer rather than a flavour of KANA.
            # S143/S4656 says "the Japanese Wikipedia article states this". For a
            # KANA answer that is true — the reading was read out of the lead. For a
            # GUESS it is not: the article gave no reading, which is why a guess was
            # asked for. Attaching the reference anyway would put a false claim of
            # provenance on Wikidata, and a sourced-looking wrong reading is worse
            # than an unsourced one because nothing downstream can tell it apart.
            if url and kind == "KANA":
                line += f'|S143|{JAWIKI_ITEM}|S4656|"{url}"'
            qs_lines.append(line)
            if bucket == "b" and ja:
                built = label_for(ja, kana)
                if built:
                    label_lines.append(f'{qid}|Len|"{built.label}"')
                    if built.alias:
                        label_lines.append(f'{qid}|Aen|"{built.alias}"')
            resolved.append(f"{qid}\t{kind}\t{kana}")
        else:
            resolved.append(f"{qid}\t{kind}\t{payload[:120]}")
        done_files.append(path)

    print(f"pending={pending} resolved={len(resolved)} "
          f"qs-lines={len(qs_lines)} label-lines={len(label_lines)} "
          f"rejected-not-hiragana={rejected} already-staged={skipped}"
          + (" [DRY]" if args.dry_run else ""))
    for r in resolved[:10]:
        print("   " + r.replace("\t", "\t"))

    if args.dry_run or not resolved:
        return

    if qs_lines:
        with open(QS_OUT, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(qs_lines) + "\n")
    if label_lines:
        with open(LABEL_OUT, "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(label_lines) + "\n")
    with open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(resolved) + "\n")
    for p in done_files:
        os.remove(p)
    print(f"appended {len(qs_lines)} QS lines + {len(label_lines)} label lines; "
          f"removed {len(done_files)} work-files")


if __name__ == "__main__":
    main()
