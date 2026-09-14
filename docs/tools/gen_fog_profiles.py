#!/usr/bin/env python3
"""Generate the shipped per-map fog profiles from a hand-filled table.

Reads  docs/tools/fog_profiles.tsv  and emits one
    hzm-mohaa-coop-mod/coop_mod/fog/<map>.dat
per row, in the fogv1 wire format that coop_mod/fogmode.scr::coop_fog_loadProfile
parses:

    fogv1,<dist>,<bias>,<r>,<g>,<b>,<cull>,<skyfar>

Design source: hzm-mohaa-coop-mod/_research/fog_grade_research.md (USER DECISIONS
2026-09-13). SUBTLE DEPTH: native fog DISTANCE is preserved (no AI-sight change),
only bias + colour are authored. Scripted-fog maps get a colour-only profile
(dist 0) so the fogmode keeper (fogmode.scr:334-339, re-applies only when
dist > 0) never flattens the map's scripted ramps.

.dat format is deliberately byte-exact (matches the two pre-existing shipped
profiles e2l2.dat / m1l3c.dat): ASCII, LF (there is no trailing newline at all),
no BOM, one line, no trailing whitespace. Files are written in binary so the
host newline convention cannot corrupt them (TRAPS T2).

The TSV is the single source of truth. This tool never invents a colour: every
value is hand-filled from the research inventory (measured sky-horizon averages
and native worldspawn fog). It also never touches a .dat that has no TSV row, so
the two existing shipped profiles (e2l2, m1l3c) are left alone.

Usage:
    python gen_fog_profiles.py build    # write the .dat files
    python gen_fog_profiles.py check    # regenerate in memory, byte-compare, exit 1 on drift
    python gen_fog_profiles.py list     # print what would be written
"""
import sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))            # docs/tools -> docs -> repo root
TSV = os.path.join(HERE, "fog_profiles.tsv")
FOGDIR = os.path.join(REPO, "hzm-mohaa-coop-mod", "coop_mod", "fog")

COLS = ["map", "class", "dist", "bias", "r", "g", "b", "cull", "sky", "eyes", "note"]


def load_rows():
    """Return list of dict rows from the TSV, skipping comments/blank/header."""
    rows = []
    with open(TSV, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split("\t")
            if parts[0].strip() == "map":       # header row
                continue
            if len(parts) < 9:
                raise SystemExit("fog_profiles.tsv:%d: expected >=9 tab-separated "
                                 "columns, got %d: %r" % (lineno, len(parts), line))
            row = {COLS[i]: parts[i].strip() for i in range(min(len(parts), len(COLS)))}
            rows.append((lineno, row))
    return rows


def render(row):
    """(filename, ascii_content) for one TSV row. Deterministic."""
    name = row["map"].lower()
    dist = int(row["dist"])
    bias = int(row["bias"])
    r = float(row["r"]); g = float(row["g"]); b = float(row["b"])
    cull = int(row["cull"]); sky = int(row["sky"])
    content = "fogv1,%d,%d,%.3f,%.3f,%.3f,%d,%d" % (dist, bias, r, g, b, cull, sky)
    return name + ".dat", content


def all_outputs():
    seen = {}
    out = []
    for lineno, row in load_rows():
        fn, content = render(row)
        if fn in seen:
            raise SystemExit("fog_profiles.tsv:%d: duplicate map %r (also line %d)"
                             % (lineno, row["map"], seen[fn]))
        seen[fn] = lineno
        out.append((fn, content))
    return out


def build():
    if not os.path.isdir(FOGDIR):
        raise SystemExit("fog dir not found: " + FOGDIR)
    n = 0
    for fn, content in all_outputs():
        path = os.path.join(FOGDIR, fn)
        with open(path, "wb") as f:
            f.write(content.encode("ascii"))     # ASCII, LF-irrelevant (no newline), no BOM
        n += 1
    print("build: wrote %d fog profiles to %s" % (n, os.path.relpath(FOGDIR, REPO)))
    return 0


def check():
    drift = []
    for fn, content in all_outputs():
        path = os.path.join(FOGDIR, fn)
        want = content.encode("ascii")
        try:
            with open(path, "rb") as f:
                have = f.read()
        except FileNotFoundError:
            drift.append("%s: missing (would be created by build)" % fn)
            continue
        if have != want:
            drift.append("%s: on-disk %r != generated %r"
                         % (fn, have.decode("latin-1"), content))
    if drift:
        print("check: FAIL - %d fog profile(s) drifted from the table:" % len(drift))
        for d in drift:
            print("  " + d)
        return 1
    print("check: OK - %d fog profiles byte-identical to the table" % len(all_outputs()))
    return 0


def list_():
    for fn, content in all_outputs():
        print("%-16s %s" % (fn, content))
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "check"
    if cmd == "build":
        return build()
    if cmd == "check":
        return check()
    if cmd == "list":
        return list_()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
