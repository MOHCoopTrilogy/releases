"""la_run.py <label> <map> <single|chain|campaign|off>
single  : menu Apply path (mission_start.cfg) on <map> -> lobby -> (chapter briefing if <map> opens a chapter) -> <map>
chain   : single, then award XP + set coop_carryReinf 1, finish the level (-> lobby -> m1l2a), report carry-over state
campaign: campaign_start.cfg -> expect NO LOBBYALL_ENTER, co_lobby1, ready, LAUNCH briefing/briefing1
off     : mission_start.cfg with coop_lobbyAlways 0 -> expect straight into <map>, no lobby"""
import os, re, sys, time, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lalib as G
R = G.R
LABEL, MAP, MODE = sys.argv[1], sys.argv[2], sys.argv[3]
BR = {"m1l1": "briefing/briefing1", "m2l1": "briefing/briefing2"}
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
STATE = re.compile(r"\^~\^~\^ LA (?:state|report)[^\r\n]*")


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


def need(pat, t, start=0, what=""):
    m = R.wait_log(pat, t, start)
    log(("OK   " if m else "FAIL ") + (what or pat))
    if not m:
        raise RuntimeError("missing: " + (what or pat))
    return m


def shots(tag, n=3, ms=700):
    seq = []
    for k in range(n):
        seq += ["screenshotJPEG %s_%d" % (tag, k), "wait %d" % ms]
    R.step(seq, timeout=60)


def report(what):
    p = len(R.read_log())
    G.cmd("report")
    found = STATE.findall(R.read_log()[p:])
    log("REPORT", what, found[-1] if found else "(none)")


def savefiles():
    d = os.path.join(R.MAINTT, "coop_mod", "save")
    out = []
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            fp = os.path.join(d, fn)
            out.append("%s %dB mtime=%s" % (fn, os.path.getsize(fp), time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(fp)))))
    return out


rundir = notes = None
try:
    G.patch_launch("coop_mod/cfg/campaign_start.cfg" if MODE == "campaign" else "coop_mod/cfg/mission_start.cfg")
    extra = G.EXTRA + (["set coop_lobbyAlways 0"] if MODE == "off" else [])
    cg = G.install()
    R.MAP = MAP
    rundir = os.path.join(R.RUNS, "la_" + LABEL)
    if os.path.isdir(rundir):
        shutil.rmtree(rundir)
    os.makedirs(rundir)
    R.seed_home(cg, G.overlay())
    notes = {"session": "la_" + LABEL, "W": 1280, "H": 720}
    R.launch(1280, 720, extra)
    t0 = len(R.read_log())
    if MODE in ("single", "chain"):
        need(r"\^~\^~\^ COOP_LOBBYALL_ENTER " + MAP, 600, t0, "menu start on %s was redirected to the lobby" % MAP)
    need(r"\^~\^~\^ LA armed map=(co_lobby1|%s)" % MAP, 600, t0, "driver armed on first map")
    time.sleep(10)
    if MODE == "off":
        G.join_loop(); time.sleep(10)
        need(r"Detected Coop for", 120, t0, "coop active on %s" % MAP)
        log("lobby entered:", "COOP_LOBBYALL_ENTER" in R.read_log()[t0:])
    else:
        need(r"\^~\^~\^ LA armed map=co_lobby1", 600, t0, "lobby (co_lobby1) loaded")
        time.sleep(15)
        G.join_loop(); time.sleep(8)
        report("lobby 1")
        shots("lobby", 3)
        p2 = len(R.read_log())
        G.cmd("ready")
        if MODE == "campaign":
            want = "briefing/briefing1"
        else:
            want = BR.get(MAP, MAP)
        need(r"\^~\^~\^ COOP_CAMPAIGN_LAUNCH " + re.escape(want), 90, p2, "ready-up -> lobby launches %s" % want)
        if MODE == "campaign":
            need(r"\^~\^~\^ LA armed map=briefing", 600, p2, "briefing1 loaded")
            time.sleep(8); shots("briefing", 2)
        else:
            if want != MAP:
                need(r"\^~\^~\^ LA armed map=briefing", 600, p2, "chapter briefing loaded after the lobby")
                time.sleep(15); G.join_loop(); time.sleep(8)
                shots("brief", 3)
                p2 = len(R.read_log())
                G.cmd("ready")
            need(r"\^~\^~\^ LA armed map=%s" % MAP, 600, p2, "%s loaded" % MAP)
            time.sleep(12)
            G.join_loop(); time.sleep(10)
            need(r"Detected Coop for", 120, p2, "coop active on %s" % MAP)
            shots("mission", 3)
        if MODE == "chain":
            G.cmd("god")
            G.cmd("xp")
            G.cmd("carry")
            time.sleep(3)
            report("m1l1 before the level end")
            log("save files before:", savefiles())
            p4 = len(R.read_log())
            R.step(["set la_next m1l2b"], timeout=30); G.cmd("complete", timeout=60)
            need(r"\^~\^~\^ LA armed map=co_lobby1", 300, p4, "level end hopped through the lobby")
            time.sleep(15); G.join_loop(); time.sleep(8)
            report("in the lobby between levels")
            shots("lobby2", 3)
            p5 = len(R.read_log())
            G.cmd("ready")
            need(r"\^~\^~\^ COOP_CAMPAIGN_LAUNCH m1l2b", 90, p5, "second lobby launches m1l2b")
            need(r"\^~\^~\^ LA armed map=m1l2b", 600, p5, "m1l2a loaded")
            time.sleep(12); G.join_loop(); time.sleep(10)
            need(r"Detected Coop for", 120, p5, "coop active on m1l2b")
            report("m1l2b")
            log("save files after:", savefiles())
            shots("mission2", 3)
        log("ENTER marker seen:", "COOP_LOBBYALL_ENTER" in R.read_log()[t0:])
    errs = [e for e in G.errors() if "coop_lobbyMap" not in e]
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-600:])
finally:
    try:
        G.S.end_session(rundir, notes or {})
    except Exception as e:
        log("end_session", repr(e))
