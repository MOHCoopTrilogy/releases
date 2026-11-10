#!/usr/bin/env python3
"""print printable ASCII runs (>=N) with offsets: probe_strings.py <file> [N] [max]"""
import re, sys
d = open(sys.argv[1], "rb").read()
n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
mx = int(sys.argv[3]) if len(sys.argv) > 3 else 400
for i, m in enumerate(re.finditer(rb"[\x20-\x7e]{%d,}" % n, d)):
    if i >= mx: break
    print(f"{m.start():08x} {m.group().decode()}")
