"""cn_radio.py <label> <map> - officer dies, his corpse entity is removed, the radio keeps calling and the waves still come."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cnlib as C
G = C.G; R = C.R
LABEL, MAP = sys.argv[1], sys.argv[2]
rundir = notes = None
try:
    rundir, notes = G.boot("cn_" + LABEL, MAP, extra=["set coop_reinfRadioGap 4", "set coop_reinfRadio 1", "set coop_reinfDebug 1", "set coop_aiScaleTest 1"])
    p0 = len(R.read_log())
    G.cmd("ofsetup", timeout=60)
    G.cmd("ofwaves")
    G.cmd("ofdie", timeout=60)
    time.sleep(1)
    G.cmd("ofremove")
    G.cmd("ofwaves")
    t0 = time.time()
    while time.time() - t0 < 75:
        time.sleep(5)
        txt = R.read_log()[p0:]
        if len(re.findall(r"RNF radio call n=", txt)) >= 1 and re.search(r"RNF entry pick", txt):
            time.sleep(8)
            break
    G.cmd("ofwaves")
    txt = R.read_log()[p0:]
    for l in re.findall(r"\^~\^~\^ (?:CN OF[^\r\n]*|RNF radio call[^\r\n]*|RNF entry[^\r\n]*|OFFICER radio bark[^\r\n]*)", txt):
        G.log(LABEL, "   ", l[:200])
    G.log(LABEL, "script errors:", len(G.errors()), G.errors()[:4])
finally:
    G.end(rundir, notes)
