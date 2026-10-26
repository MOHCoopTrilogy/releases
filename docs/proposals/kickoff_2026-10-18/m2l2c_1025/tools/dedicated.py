"""dedicated.py <label> [stock-client]  - dedicated server (G:/mohaa-dedtest, edited map in an overlay pk3) + harness client joining it.
Checks: server load (0 Script Errors, $mesh_gate found), client joins, rcon opens/closes the gate, client sees it; with OXNOBSP=1 the CLIENT has the stock map."""
import os, sys, re, time, zipfile, subprocess, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
DED = "G:/mohaa-dedtest"
HOME = "H:/hzm_work/m2l2c_work/ded_home"
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
LOG = HOME + "/maintt/qconsole.log"
os.makedirs(HOME + "/maintt", exist_ok=True)
for fn in os.listdir(HOME + "/maintt"):
    if fn.lower().endswith(".pid"): os.remove(os.path.join(HOME, "maintt", fn))
ov = HOME + "/maintt/zzzzzzzzzzzz_m2ded.pk3"
bspfiles = ["maps/m2l2c.bsp", "maps/m2l2c.pth"]
with zipfile.ZipFile(ov, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("coop_mod/coop_selftest_xp.scr", open(os.path.join(G.HERE, "ox_drv.scr"), "rb").read())
    for rel in G.FILES:
        p = os.path.join(G.MOD, rel)
        if os.path.exists(p) and rel not in bspfiles: z.write(p, rel)
    for rel in (bspfiles if os.environ.get("OXNOBSP") != "1" else []): z.write(os.path.join(G.MOD, rel), rel)
open(LOG, "w").close()
args = [DED + "/omohaaded.exe", "+set", "com_target_game", "2", "+set", "fs_basepath", GOG, "+set", "dedicated", "1", "+set", "fs_homepath", HOME.replace("/", "\\"),
        "+set", "net_port", "12900", "+set", "sv_maxclients", "8", "+set", "g_gametype", "2", "+set", "logfile", "2", "+set", "developer", "1",
        "+set", "com_abnormalExit", "0", "+set", "coop_st_xp", "1", "+set", "coop_objx", "1", "+set", "rconpassword", "m2pw", "+set", "sv_pure", "0", "+map", "m2l2c"]
srv = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
rundir = notes = None
try:
    t0 = time.time()
    while time.time() - t0 < 90:
        t = open(LOG, errors="replace").read()
        if "OX armed" in t: break
        time.sleep(2)
    log("server armed:", "OX armed" in t, "after %.0fs" % (time.time() - t0))
    rundir, notes = G.boot("m2_" + LABEL, "m1l1", extra=[])
    G.cmd("god")
    R.step(["connect 127.0.0.1:12900", "wait 20000"], timeout=60)
    time.sleep(5)
    st = open(LOG, errors="replace").read()
    log("server saw client:", bool(re.search(r"(connected|entered|begin|Client.*connect)", st[-6000:], re.I)), re.findall(r"[^\n]*(?:entered the game|connected)[^\n]*", st)[-2:])
    R.step(["screenshotJPEG ded_client_closed", "wait 300"], timeout=20)
    R.step(["rconpassword m2pw", "rcon set ox_k 1", "rcon set ox_cmd rgset", "wait 3000", "screenshotJPEG ded_client_open", "wait 300"], timeout=40)
    R.step(["rcon set ox_k 0", "rcon set ox_cmd rgset", "wait 2500", "screenshotJPEG ded_client_closed2", "wait 300"], timeout=40)
    time.sleep(2)
    st = open(LOG, errors="replace").read()
    errs = sorted(set(l[-170:] for l in st.splitlines() if "Script Error" in l or "Couldn't compile" in l or "parse error" in l))
    log("server script errors:", len(errs), errs[:4])
    log("server mesh gate lines:", re.findall(r"\^~\^~\^ (M2L2C mesh gate[^\r\n]*)", st))
    log("server rgset lines:", re.findall(r"\^~\^~\^ (OX rgset[^\r\n]*)", st))
    log("server bad-submodel/CM lines:", [l[-140:] for l in st.splitlines() if re.search(r"submodel|bad model|CM_|Drop|dropped|Server disconnected", l, re.I)][:6])
    ct = R.read_log()
    log("client log notable:", [l[-150:] for l in ct.splitlines() if re.search(r"submodel|bad model|CM_|disconnect|Drop|error", l, re.I)][:8])
    log("client script errors:", len(G.errors()))
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
    try: srv.terminate()
    except Exception: pass
