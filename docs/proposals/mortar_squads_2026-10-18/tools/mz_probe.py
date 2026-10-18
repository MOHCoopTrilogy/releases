"""mz_probe.py <label> <map> [map...] - for each map: boot, put the player in open ground 1500u from the officer in 3 directions, run the
German site finder (mortar.scr::mz_site_g) from each; a map keeps its whitelist entry only if >= 2 of the 3 placements find a hidden site."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mzlib as G
R = G.R
LABEL = sys.argv[1]
MAPS = sys.argv[2:]
OUT = open(os.path.join(G.HERE, "logs", "probe_%s.txt" % LABEL), "a")


def log(*a):
    G.log("probe", *a)
    OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()


for mp in MAPS:
    rundir = notes = None
    try:
        rundir, notes = G.boot("mzp_" + mp, mp)
        G.cmd("purge", timeout=90)
        G.cmd("god")
        found = 0
        afound = 0
        for k in range(8):
            G.cmd("toofficer", yaw=45 * k, n=(1200, 1500, 1800)[k % 3], timeout=90)
            p0 = len(R.read_log())
            G.cmd("sitetest", timeout=60)
            m = re.search(r"MZ SITETEST map=\S+ player=[^\r\n]*alliedspots=(\d+) site=([^\r\n]*)", R.read_log()[p0:])
            res = m.group(2).strip() if m else "?"
            na = int(m.group(1)) if m else 0
            log(mp, "placement", k, "-> german site", res, "| allied spots", na)
            if res not in ("none", "?"):
                found += 1
            if na >= 3:
                afound += 1
        log("RESULT", mp, "german sites", found, "of 8; allied-spot placements", afound, "of 8",
            "KEEP-G" if found >= 2 else "drop-G", "KEEP-A" if afound >= 2 else "drop-A")
        errs = G.errors()
        if errs:
            log("errors", mp, errs[:3])
    except Exception as e:
        log("FAILED", mp, repr(e))
    finally:
        G.end(rundir, notes)
