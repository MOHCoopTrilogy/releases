#!/usr/bin/env python
"""ads_audit.py - which shipped guns have NO ADS tune?

Simulates cgame's CG_FindAdsTune resolution (exact row -> "(Finish)" strip -> donor alias)
against every weapon tik under hzm-mohaa-coop-mod/models/weapons. A gun listed here aims
with the GLOBAL cg_ads* defaults - either give it a donor line in s_adsDonor (cg_modelanim.c)
or dial it with the in-game workbench (cg_adsTune 1, numpad, adssave).

Scoped guns and non-aiming items (binoculars, mine detectors, signal smoke) are expected
misses: scoped ADS is the zoom overlay, items do not aim.
"""
import re, io, glob, os, sys

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
SRC  = os.path.join(ROOT, "openmohaa-hzm", "code", "cgame", "cg_modelanim.c")

src   = io.open(SRC, encoding="latin-1").read()
tbl   = re.search(r"s_adsGunTune\[\] = \{(.*?)\n\};", src, re.S).group(1)
tuned = {m.group(1).lower() for m in re.finditer(r'\{\s*"([^"]+)"', tbl)}
dt    = re.search(r"s_adsDonor\[\]\[2\] = \{(.*?)\n\};", src, re.S)
donor = {}
if dt:
    for m in re.finditer(r'\{"([^"]+)",\s*"([^"]+)"\s*\}', dt.group(1)):
        donor[m.group(1).lower()] = m.group(2).lower()

def resolves(nm):
    lo = nm.lower()
    if lo in tuned:
        return True
    base = lo.split(" (")[0]
    if base in tuned:
        return True
    d = donor.get(base)
    return bool(d and d in tuned)

miss, ok = set(), 0
pat = os.path.join(ROOT, "hzm-mohaa-coop-mod", "models", "weapons", "**", "*.tik")
for p in glob.glob(pat, recursive=True):
    m = re.search(r'^\s*name\s+"([^"]+)"', io.open(p, encoding="latin-1").read(), re.M | re.I)
    if not m:
        continue
    if resolves(m.group(1)):
        ok += 1
    else:
        miss.add(m.group(1).split(" (")[0])

print(f"{len(tuned)} tuned rows, {len(donor)} donor aliases, {ok} tiks resolve")
bases = sorted(miss)
print(f"{len(bases)} base guns with NO tune (finish tiks collapse into their base):")
for b in bases:
    print("  " + b)
sys.exit(1 if bases else 0)
