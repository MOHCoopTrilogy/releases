"""[flguns] DEV TOOL (not bundled): the base-gun sight rows of the release engine's cg_adssights.h ->
discguns_baserows.json, the converter's copy of that compiled table (our engine data, no disc bytes; ship-safe).
Regenerate whenever cg_adssights.h changes on the release engine branch:

    python -I flgunrows.py <engine tree>/code/cgame/cg_adssights.h [discguns_baserows.json]"""
import json
import os
import re
import sys

RX = re.compile(r'\{"(models/weapons/[^"]+)", "([^"]+)", \{([^}]*)\}, \{([^}]*)\}, ([-\d.]+)f?, \{([^}]*)\}, ([-\d.]+)f?\}')


def vec(t):
    return [float(x.strip().rstrip("f")) for x in t.split(",")]


def main(header, out):
    s = open(header, encoding="latin-1").read()
    rows = {}
    for tik, name, F, R, d, U, rel in RX.findall(s):
        rows[tik] = dict(name=name, F=vec(F), R=vec(R), delta=float(d), U=vec(U), relief=float(rel))
    json.dump(rows, open(out, "w"), indent=0, sort_keys=True)
    print(out, len(rows))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else
         os.path.join(os.path.dirname(os.path.abspath(__file__)), "discguns_baserows.json"))
