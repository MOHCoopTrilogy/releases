"""sr_run.py <label> <map> <mode> [n]   mode = ignore | convert
ignore : prep a lone wounded german, surrender, allies around him, 60 s of snapshots, then un-ignore control.
convert: n times prep -> surrender -> convert -> sample activity + sound log slice."""
import os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import srlib as G
R = G.R
LABEL, MAP, MODE = sys.argv[1], sys.argv[2], sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else 1
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
def log(*a):
    G.log(LABEL, *a); OUT.write(" ".join(str(x) for x in a) + "\n"); OUT.flush()
DL = re.compile(r"deathvox|gurgle|death|dying|pain|bleed|gore|scream|dfr_.*(?:death|k)", re.I)
SND = re.compile(r"S_StartSound: ([^\r\n]*)")
def sounds(p0):
    return [m for m in SND.findall(R.read_log()[p0:])]
def surrendered(p0, wait):
    t = time.time()
    while time.time() - t < wait:
        G.cmd("snap")
        if re.search(r"\^~\^~\^ SURRENDER ent=", R.read_log()[p0:]) or re.search(r"SR SNAP[^\r\n]*surr=1", R.read_log()[p0:]):
            return True
        time.sleep(1)
    return False
rundir = notes = None
try:
    rundir, notes = G.boot("sr_" + LABEL, MAP, extra=[
        "set coop_aiSurrenderChance 100", "set coop_aiSurrenderMax 99", "set coop_aiSurrenderCooldown 0",
        "set coop_aiSurrenderHpPct 60"])
    G.cmd("god")
    if MODE == "ignore":
        p0 = len(R.read_log())
        for tries in range(8):
            G.cmd("prep", timeout=40)
            G.cmd("god")
            if surrendered(p0, 12):
                break
        G.cmd("allies")
        p1 = len(R.read_log())
        G.frames("ign", 36, 200)
        for k in range(7):
            G.cmd("snap")
            time.sleep(10)
        G.cmd("snap")
        for l in G.since(p0, r"\^~\^~\^ ((?:SR SNAP|SR prep|SR ally|SURRENDER)[^\r\n]*)"):
            log("  ", l[:230])
        log("-- control: un-ignore, allies may now shoot him")
        G.cmd("unignore")
        c0 = len(R.read_log())
        for k in range(6):
            time.sleep(5)
            G.cmd("snap")
        for l in G.since(c0, r"\^~\^~\^ (SR SNAP[^\r\n]*)"):
            log("  ctl", l[:230])
    else:
        ok = 0
        for i in range(N):
            p0 = len(R.read_log())
            got = False
            for tries in range(3):
                G.cmd("mksquad", timeout=40)
                time.sleep(5)
                G.cmd("prep", timeout=40)
                G.cmd("god")
                if surrendered(p0, 10):
                    got = True
                    break
            if not got:
                log("conv", i + 1, "no surrender reached"); continue
            time.sleep(14)   # let the prep kills' gurgle tails finish so the sound window is clean
            q0 = len(R.read_log())
            time.sleep(5)
            pre = [x for x in sounds(q0) if DL.search(x)]
            c0 = len(R.read_log())
            G.cmd("convert", timeout=60)
            time.sleep(5)
            s = sounds(c0)
            bad = [x for x in s if DL.search(x)]
            skip = len(G.since(c0, r"CONVERT death-path skipped"))
            G.cmd("mkfight")
            G.cmd("act")
            if i == 0:
                G.frames("cv", 30, 200)
            for k in range(5):
                time.sleep(3)
                G.cmd("act")
            acts = G.since(c0, r"SR ACT pd=(\d+) t=[\d.]+ ent=\d+ alive=(\d) team=(\w+) gun=(.*?) en=(\S+) moved=(\d+)")
            active = any(a[1] == "1" and a[2] == "american" and a[3] not in ("-", "") and (a[4] == "enemy" or int(a[5]) > 24 or int(a[0]) < 350) for a in acts)
            kicks = G.since(c0, r"CONVERT_KICK ([^\r\n]*)")
            log("conv", i + 1, "active=%s quiet-window sounds=%d pre-convert-deathlike=%d post-convert(5s,no fight)-deathlike=%d %s skipmarker=%d kicks=%s last=%s" % (active, len(s), len(pre), len(bad), bad[:3], skip, kicks, acts[-1] if acts else None))
            ok += 1 if active else 0
        log("CONVERT SUMMARY active %d / %d" % (ok, N))
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-800:])
finally:
    G.end(rundir, notes)
