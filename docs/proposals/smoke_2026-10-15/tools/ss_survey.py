"""ss_survey.py <label> <map> - candidate (player, squad) spots from the map's own Germans, one still each, to pick a clean open view by eye."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smokelib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
rundir = notes = None
try:
    rundir, notes = G.boot("ss_" + LABEL, MAP, extra=["set g_ai 1"])
    G.cmd("god")
    G.cmd("pairs", timeout=90)
    n = int(re.findall(r"SS CANDS (\d+)", R.read_log())[-1])
    for k in range(1, n + 1):
        G.cmd("usepair", n=k, timeout=30)
        time.sleep(1.5)
        G.still("%s_c%02d" % (LABEL, k))
    print("cands", n)
except Exception as e:
    import traceback; print("FAILED", repr(e), traceback.format_exc()[-600:])
finally:
    G.end(rundir, notes)
