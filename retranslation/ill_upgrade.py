"""Put old-style {{ill}} links into Emma's form: {{ill|EN|ja|JA|lt=EN display|lt_ja=JA}}.

Emma, 2026-10-08: every link is {{ill|ENGLISH_LINK|ja|JALINK}} with lt= for the English display
and lt_ja= for the Japanese display; "no need for the qids since that is a latter script".

An ill with a Japanese target is rewritten: the English link and display are kept (lt=, else the
link itself), the Japanese target becomes lt_ja= too unless one is already given, and qid=/ltq=
and every other language are dropped. An ill with no Japanese target is left exactly as it is.

    python retranslation/ill_upgrade.py <in.wiki> <out.wiki>
"""
import re
import sys

ILL = re.compile(r"\{\{ill\|([^{}]*)\}\}")


def convert_one(body):
    parts = body.split("|")
    pos, named = [], {}
    for p in parts:
        k, eq, v = p.partition("=")
        if eq and re.fullmatch(r"[A-Za-z_]+", k.strip()):
            named[k.strip()] = v.strip()
        else:
            pos.append(p.strip())
    if not pos:
        return None
    en = pos[0]
    ja = None
    for i in range(1, len(pos) - 1):
        if pos[i] == "ja":
            ja = pos[i + 1]
            break
    if not ja or not en or en == "UNKNOWN":
        return None
    lt = named.get("lt") or en
    lt_ja = named.get("lt_ja") or re.sub(r"\s*\(.*\)$", "", ja)
    return "{{ill|%s|ja|%s|lt=%s|lt_ja=%s}}" % (en, ja, lt, lt_ja)


def convert(text):
    done = kept = 0

    def sub(m):
        nonlocal done, kept
        new = convert_one(m.group(1))
        if new is None:
            kept += 1
            return m.group(0)
        done += 1
        return new

    return ILL.sub(sub, text), done, kept


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src, encoding="utf-8").read().replace("\r\n", "\n")
    out, done, kept = convert(text)
    open(dst, "w", encoding="utf-8", newline="\n").write(out)
    print(f"{src}: {done} converted, {kept} left (no ja target)")
