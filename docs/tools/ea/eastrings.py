#!/usr/bin/env python3
"""MOH European Assault string tables -> TSV. Our own code, stdlib only.

strings.viv / stringMP.viv are C0FB archives holding UTF-16 XML string tables
(stringtable.xml, globalstringtable.xml). This prints alias<TAB>text (English).

usage: python -I eastrings.py <strings.viv> [...]   -> TSV on stdout
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import viv  # noqa: E402

STR_RE = re.compile(r'<(?:global|local)?string\s+name="([^"]*)"[^>]*>(.*?)</(?:global|local)?string>', re.S)
EN_RE = re.compile(r'<english\s+value="([^"]*)"')


def tables(path):
    data = open(path, "rb").read()
    for name, off, size in viv.parse_toc(data):
        blob = data[off:off + size]
        if blob[:2] in (b"\xff\xfe", b"\xfe\xff"):
            yield name, blob.decode("utf-16")
        else:
            yield name, blob.decode("latin-1")


def main(argv):
    for p in argv[1:]:
        for name, text in tables(p):
            # Format discovery: print raw head once if no <string> tags match.
            hits = 0
            for m in STR_RE.finditer(text):
                key = m.group(1)
                en = EN_RE.search(m.group(2))
                val = re.sub(r"\s+", " ", en.group(1) if en else "").strip()
                print(f"{os.path.basename(os.path.dirname(p))}\t{key}\t{val}")
                hits += 1
            if not hits:
                print(f"#RAW {p}:{name}\n{text[:1500]}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
