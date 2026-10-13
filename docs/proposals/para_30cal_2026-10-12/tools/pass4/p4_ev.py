"""p4_ev.py <label> <map> <x> <y> <z> <yaw> ev=<hot,belt,nade,nadefoot,far> [purge=1] [park=x,y,z] - fourth pass, task 4:
things made to happen once. Everything the TEST does is a driver command and is logged as such.
  hot       the manned gun is made to fire without a pause ('fireon'): he must stop it at 45 heat and let it bleed
  belt      the belt is cut to 12 rounds with one belt more, fired off; then to 10 with none: new belt after 4s, then pack-up
  nade      a stick grenade is laid 110u from the mounted gunner (goes off after 3.5s)
  nadefoot  a stick grenade is laid 90u from squad member 1 (on foot)
  far       the player is flown 8000u away for 45s (the medic rule, the rescue rules)"""
import json, math, os, re, sys, time
import p3lib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
X, Y, Z, YAW = [float(v) for v in sys.argv[3:7]]
OPT = dict(a.split("=", 1) for a in sys.argv[7:])
EV = OPT.get("ev", "").split(",")
rundir = notes = None
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


def gst():
    p = G.cmd("gst")
    time.sleep(0.1)
    t = " ".join(G.since(p, r"P3 GST[^\r\n]*"))
    m = re.search(r"ammo=(-?\d+) heat=([\d.]+)", t)
    a = re.search(r"ang=\( ([-\d.]+)", t)
    return (int(m.group(1)), float(m.group(2))) if m else (None, None), (a.group(1) if a else "?"), t


def psq_since(p):
    return [l[:200] for l in G.psq(p) if " mg " in l or "nade" in l or "rescue" in l or "walkout" in l or " tac " in l]


def cam(dist=150, ang=125, up=0, back=30):
    c = G.cmd("camg", n=dist, yaw=ang, z=up, pitch=back)
    time.sleep(0.4)
    return G.since(c, r"P3 camg[^\r\n]*")


try:
    rundir, notes = G.boot("p4_" + LABEL, MAP)
    G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
    time.sleep(1.0)
    if OPT.get("purge"):
        log(G.since(G.cmd("purge", timeout=60), r"P3 purge[^\r\n]*"))
    G.cmd("meter", x=X, y=Y, z=Z)
    p0 = G.cmd("call", x=X, y=Y, z=Z, yaw=YAW, tag="pin")
    if OPT.get("park"):
        px, py, pz = OPT["park"].split(",")
        G.cmd("tp", x=px, y=py, z=float(pz) + 8, yaw=YAW, pitch=0)
    m = R.wait_log(r"PSQ t=[\d.]+ mg setup k=1[^\r\n]*", float(OPT.get("wait", 200)), p0)
    log(m.group(0)[:200] if m else "NO SET-UP")
    if not m:
        raise RuntimeError("no set-up")
    time.sleep(2.0)
    if "hot" in EV:
        log(cam())
        ph = G.cmd("fireon")
        t0 = time.time()
        rows = []
        while time.time() - t0 < 9:
            (am, ht), ang, _ = gst()
            rows.append("%.1fs heat=%s belt=%s" % (time.time() - t0, ht, am))
            time.sleep(0.25)
        log("HOT (test: fireon at t=0):", " | ".join(rows))
        G.frames(LABEL + "_hot", 10, 150)
        G.cmd("fireoff")
        log("HOT lines:", psq_since(ph))
        time.sleep(3.0)
    if "belt" in EV:
        log(cam())
        pb = G.cmd("mbelt", n=12, z=1)
        G.cmd("fireon")
        t0 = time.time()
        rows = []
        while time.time() - t0 < 12:
            (am, ht), ang, _ = gst()
            rows.append("%.1fs belt=%s heat=%s" % (time.time() - t0, am, ht))
            if time.time() - t0 > 2 and int(time.time() - t0) % 3 == 0:
                G.cmd("fireon")       # the test keeps asking for fire: the script must hold it during the belt change
            time.sleep(0.4)
        log("BELT 1 (test: 12 rounds, one belt more, fireon):", " | ".join(rows))
        log("BELT 1 lines:", psq_since(pb))
        pb = G.cmd("mbelt", n=10, z=0)
        G.cmd("fireon")
        log(cam())
        G.frames(LABEL + "_beltout", 50, 150)
        pk = R.wait_log(r"PSQ t=[\d.]+ mg packup k=1", 20, pb)
        log("BELT 2 (test: 10 rounds, no belt more, fireon): packup=%s" % bool(pk))
        log("BELT 2 lines:", psq_since(pb))
        time.sleep(14)
        log("after the pack-up, 14s:", psq_since(pb)[-4:], G.since(G.cmd("who"), r"P3 WHO[^\r\n]*"))
    if "beltout" in EV:
        log(cam())
        pb = G.cmd("mbelt", n=10, z=0)
        t0 = time.time()
        am = 10
        while time.time() - t0 < 40 and am:
            G.cmd("fireon")           # the test keeps asking for fire until the belt is out
            time.sleep(1.2)
            (am, ht), ang, _ = gst()
        log("BELTOUT (test: 10 rounds, no belt more, fireon): belt=%s after %.1fs" % (am, time.time() - t0))
        G.frames(LABEL + "_beltout", 50, 150)
        pk = R.wait_log(r"PSQ t=[\d.]+ mg packup k=1", 20, pb)
        log("packup=%s" % bool(pk), psq_since(pb))
        time.sleep(15)
        log("15s after the pack-up:", psq_since(pb)[-3:], G.since(G.cmd("who"), r"P3 WHO[^\r\n]*"))
    if "nade" in EV:
        log(cam(float(OPT.get("ncd", 210)), float(OPT.get("nca", 110)), float(OPT.get("ncz", 30)), 60))
        pn = G.cmd("nade", tag=0, n=110, yaw=float(OPT.get("nyaw", 250)), z=3.5)
        log(G.since(pn, r"P3 nade at[^\r\n]*"))
        G.frames(LABEL + "_nade", 110, 150)
        mb = R.wait_log(r"PSQ t=[\d.]+ mg nade back=\d", 25, pn)
        log("NADE:", mb.group(0) if mb else "no 'back' line")
        time.sleep(2.0)
        log("NADE lines:", psq_since(pn))
        log(G.since(G.cmd("sq"), r"P3 SQ[^\r\n]*"))
        (am, ht), ang, t = gst()
        log("gun after:", t[:260])
    if "nadefoot" in EV:
        k = OPT.get("fk", "1")
        c = G.cmd("camk", tag=k, n=190, yaw=140)
        pn = G.cmd("nade", tag=k, n=90, yaw=40, z=3.5)
        log(G.since(pn, r"P3 nade at[^\r\n]*"))
        rows = []
        for i in range(10):
            R.step(["screenshotJPEG %s_foot_%04d" % (LABEL, i), "wait 100"], timeout=30)
            s = G.since(G.cmd("sq"), r"P3 SQ k=%s[^\r\n]*" % k)
            mm = re.search(r"at=\( ([-\d.]+) ([-\d.]+) [-\d.]+ \).*think=(\w+)", s[-1]) if s else None
            rows.append("%s,%s %s" % (mm.group(1), mm.group(2), mm.group(3)) if mm else "?")
            time.sleep(0.25)
        log("NADEFOOT member %s every ~0.6s (x,y think):" % k, " | ".join(rows))
        time.sleep(2.0)
        log(G.since(G.cmd("sq"), r"P3 SQ[^\r\n]*"))
    if "far" in EV:
        pf = len(R.read_log())
        G.cmd("fly", x=X + 8000, y=Y, z=Z + 8, pitch=0, yaw=YAW)
        time.sleep(float(OPT.get("fars", 45)))
        t = R.read_log()[pf:]
        log("FAR 45s: TELE lines:", len(re.findall(r"P3 TELE", t)), "rescue lines:", [l[:160] for l in G.psq(pf) if "rescue" in l or "medic" in l])
        log(G.since(G.cmd("sq"), r"P3 SQ[^\r\n]*"))
    t = R.read_log()[p0:]
    log("TELE:", re.findall(r"P3 TELE[^\r\n]*", t)[:6])
    log("script errors:", G.errors()[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
    try:
        log("errors:", G.errors()[:8])
    except Exception:
        pass
finally:
    G.end(rundir, notes)
