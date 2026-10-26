"""verify.py <label> : edited-vs-stock behaviour tests on the harness (set OXNOBSP=1 for the stock map). Prints PASS-able evidence lines."""
import os, sys, time, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R
LABEL = sys.argv[1]
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
def log(*a):
    s = " ".join(str(x) for x in a); G.log(LABEL, *a); OUT.write(s + "\n"); OUT.flush()
def here():
    p0 = G.cmd("here")
    r = G.since(p0, r"\^~\^~\^ OX here \( ([-\d.]+) ([-\d.]+) ([-\d.]+)")
    return tuple(float(v) for v in r[0]) if r else None
def walk(keys, ms):
    seq = ["+%s" % k for k in keys] + ["wait %d" % ms] + ["-%s" % k for k in keys] + ["wait 300"]
    R.step(seq, timeout=40)
def pump(pat, p0):
    return G.since(p0, pat)
rundir = notes = None
try:
    rundir, notes = G.boot("m2_" + LABEL, "m2l2c", extra=[])
    G.cmd("god"); G.cmd("kit"); time.sleep(3)
    p0 = G.cmd("rgstate"); log("RGSTATE", pump(r"\^~\^~\^ OX (rgstate[^\r\n]*)", p0))
    edited = "EDITED" in str(pump(r"\^~\^~\^ OX (rgstate[^\r\n]*)", p0))
    log("map is", "EDITED" if edited else "STOCK")
    # ---- (4) player clip: east-bound at many y, with jump / crouch; west-bound from behind
    for tag, keys in (("walk", ["forward"]), ("jump", ["forward", "moveup"]), ("crouch", ["forward", "movedown"])):
        res = []
        for y in (-3480, -3470, -3460, -3400, -3300, -3200, -3160, -3150, -3145):
            G.cmd("tp", x=3560, y=y, z=-505, yaw=0, pitch=0); time.sleep(0.25)
            walk(keys, 2600)
            h = here(); res.append((y, round(h[0]) if h else None))
        log("CLIP east-bound", tag, res)
    res = []
    for y in (-3470, -3400, -3300, -3200, -3150):
        G.cmd("tp", x=3700, y=y, z=-505, yaw=180, pitch=0); time.sleep(0.25)
        walk(["forward"], 2600)
        h = here(); res.append((y, round(h[0]) if h else None))
    log("CLIP west-bound from behind", res)
    # ---- (3) bullets, explosion, AI sight
    for tag, tx in (("control: man in FRONT of the fence", 3590), ("man BEHIND the closed fence", 3700)):
        G.cmd("tp", x=3540, y=-3300, z=-505, yaw=0, pitch=0)
        G.cmd("mkai", x=tx, y=-3300, z=-512)
        time.sleep(0.5)
        G.cmd("aim", x=tx, y=-3300, z=-470)
        p1 = G.cmd("aihp"); h0 = G.since(p1, r"OX aihp ([-\d.]+)")
        R.step(["+attackprimary", "wait 1500", "-attackprimary", "wait 300"], timeout=30)
        p1 = G.cmd("aihp"); h1 = G.since(p1, r"OX aihp ([-\d.]+)")
        log("BULLET", tag, "hp", h0, "->", h1)
    p0 = G.cmd("mktgt2", x=3680, y=-3300, z=-512)
    p1 = G.cmd("rdmg", x=3600, y=-3300, z=-480, pitch=300, k=0)
    p1 = G.cmd("rdmg", x=3600, y=-3300, z=-480, pitch=300, k=100)
    p1 = G.cmd("targethp"); log("EXPLOSION (radiusdamage 300 at 3600, target 3680 behind the fence) hp", pump(r"\^~\^~\^ OX (targethp[^\r\n]*)", p1))
    p1 = G.cmd("mkai", x=3700, y=-3300, z=-512)
    G.cmd("tp", x=3560, y=-3300, z=-505, yaw=0, pitch=0); time.sleep(0.3)
    p1 = G.cmd("aisee"); log("AI SIGHT (man behind the fence, player in front)", pump(r"\^~\^~\^ OX (aisee[^\r\n]*)", p1))
    p1 = G.cmd("trc"); log("TRACE through the fence", pump(r"\^~\^~\^ OX (trc[^\r\n]*)", p1))
    # ---- (1) AI paths closed / open
    if edited:
        for k, tag in ((0, "CLOSED"), (1, "OPEN")):
            G.cmd("rgset", k=k)
            time.sleep(1.0)
            p1 = G.cmd("aitest", x=3730, y=-3300, z=-490, yaw=3560, pitch=-3300, k=-496)
            for i in range(5):
                time.sleep(2.0)
                p1 = G.cmd("aipos"); r = pump(r"\^~\^~\^ OX (aipos[^\r\n]*)", p1)
            log("AI PATH gate", tag, "goal x=3560 (in front); final", r)
    log("errors", G.errors())
except Exception as e:
    import traceback; log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
