"""ox_auto.py <label> <map> [--only id,id] [--hold N] [--end] [--noframes]  - generic auto-player for the extra objectives of one map.

Reads docs/tools/objx_points.json[map].objectives and plays every objective in file order on the private harness client (1 player, god):
  activate  when=near -> teleport near the spot; when=trigger -> driver `fire <targetname>`; after / auto -> wait
  intel     teleport to each pickup, USE
  radio     damage every set (the shot path)
  charge    take the kit (hold USE), plant on every target (hold USE), wait for the chain / fuses
  perform / hold  stand in the zone, wait for the clock, performer close-ups (pfcam) for the GIF
Writes logs/run_<label>.txt and frames runs/ox_<label>/<objid>_<phase>_NNNN.jpg; --end finishes with the exit-gate check (endnow).
Run inside a harness_turn.py turn (runbatch.sh)."""
import os, re, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlib as G
R = G.R

args = sys.argv[1:]
LABEL, MAP = args[0], args[1]
ONLY = None
HOLD = ""
END = "--end" in args
FRAMES = "--noframes" not in args
if "--only" in args:
    ONLY = args[args.index("--only") + 1].split(",")
if "--hold" in args:
    HOLD = args[args.index("--hold") + 1]
DATA = json.load(open("C:/mohaa-coop-dev/docs/tools/objx_points.json", encoding="utf-8"))[MAP]
OBJS = DATA["objectives"]
os.makedirs(os.path.join(G.HERE, "logs"), exist_ok=True)
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
T0 = time.time()


def log(*a):
    s = "%5.0fs " % (time.time() - T0) + " ".join(str(x) for x in a)
    G.log(LABEL, *a)
    OUT.write(s + "\n")
    OUT.flush()


def tp(x, y, z, yaw=0, pitch=0):
    G.cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=pitch)


def aim(x, y, z):
    G.cmd("aim", x=x, y=y, z=z)


def seen(pat, timeout):
    return R.wait_log(pat, timeout, 0)


def frames(tag, n, ms):
    if FRAMES:
        G.frames(tag, n, ms)


def hold_use(ms):
    R.step(["+use", "wait %d" % ms, "-use", "wait 250"], timeout=40 + ms // 1000)


def idx(oid):
    for i, o in enumerate(OBJS, 1):
        if o["id"] == oid:
            return i


def activate(i, o):
    w = o["when"]
    if w == "near":
        p = o["near"]["pos"]
        tp(p[0], p[1], p[2] + 28, 0, 0)
    elif w == "trigger":
        G.cmd("fire", s=o["arg"])
    ok = seen(r"\^~\^~\^ OBJX ACTIVE %s " % o["id"], 120 if o.get("after_id") or w == "after" else 40)
    if not ok:
        log("  !! %s did not activate by itself - forcing" % o["id"])
        G.cmd("force", k=i)
        ok = seen(r"\^~\^~\^ OBJX ACTIVE %s " % o["id"], 10)
    log("ACTIVE", o["id"], bool(ok))
    time.sleep(1.5)
    frames("%s_active" % o["id"], 6, 300)


def do_intel(i, o):
    for it in o["items"]:
        if it["kind"] != "pickup":
            continue
        x, y, z = it["pos"]
        tp(x + 50, y, z + 4 - 24 + 24, 180, 0)
        aim(x, y, z + 10)
        frames("%s_view" % o["id"], 3, 300)
        hold_use(450)
    log("DONE %s seen:" % o["id"], bool(seen(r"\^~\^~\^ OBJX DONE %s " % o["id"], 20)))


def do_radio(i, o):
    base = 0
    for oo in OBJS:
        if oo is o:
            break
        base += len(oo.get("items", []))
    for n, it in enumerate(o["items"], 1):
        if it["kind"] == "radio":
            x, y, z = it["pos"]
            tp(x + 200, y, z + 28, 180, 4)
            aim(x, y, z + 20)
            frames("%s_set%d_before" % (o["id"], n), 4, 250)
            G.cmd("dmgradio", k=base + n)
            frames("%s_set%d_blast" % (o["id"], n), 8, 250)
    log("DONE %s seen:" % o["id"], bool(seen(r"\^~\^~\^ OBJX DONE %s " % o["id"], 25)))


_NODES = None


def nodes():
    global _NODES
    if _NODES is None:
        sys.path.insert(0, "C:/mohaa-coop-dev/docs/tools")
        import bsptrace as T
        _NODES = [[float(v) for v in e["origin"].split()] for e in T.BSP.load(MAP).entities() if e["classname"] == "info_pathnode"]
    return _NODES


_BSP = None


def vantage(pos, want=330):
    """a walkable pathnode 220-480 u from pos with a clear sight line to it (chest height) - the camera spot for set pieces"""
    import math
    global _BSP
    if _BSP is None:
        sys.path.insert(0, "C:/mohaa-coop-dev/docs/tools")
        import bsptrace as T
        _BSP = T.BSP.load(MAP)
    x, y, z = pos
    best = None
    for n in nodes():
        d = math.hypot(n[0] - x, n[1] - y)
        if 220 <= d <= 480 and abs(n[2] - 48 - z) < 45:
            t = _BSP.trace((n[0], n[1], n[2] - 48 + 56), (x, y, z + 56))
            if t and t[0] < 0.97:
                continue
            sc = abs(d - want)
            if best is None or sc < best[0]:
                best = (sc, n)
    return best[1] if best else None


def stand_near(pos, yaw=180, off=170, nodewalk=True):
    """stand on a real walkable spot: the pathnode 90-230 u from the item (nearest to 150 u), else item + off"""
    import math
    x, y, z = pos
    best = None
    for n in nodes():
        d = math.hypot(n[0] - x, n[1] - y)
        if 90 <= d <= 175 and abs(n[2] - 48 - z) < 45:
            sc = abs(d - 130)
            if best is None or sc < best[0]:
                best = (sc, n)
    if best and nodewalk:
        n = best[1]
        log("   stand for", [round(v) for v in pos], "at node", [round(v) for v in n])
        tp(n[0], n[1], n[2] - 22, 0, 0)
    else:
        tp(x + off, y, z + 28, yaw, 0)
    aim(x, y, z + 50)


def do_charge(i, o):
    kit = [it for it in o["items"] if it["kind"] == "kit"]
    tgs = [it for it in o["items"] if it["kind"] == "target"]
    if kit:
        stand_near(kit[0]["pos"], off=60, nodewalk=False)
        frames("%s_kit" % o["id"], 3, 300)
        hold_use(1900)
        log("KIT taken:", bool(seen(r"\^~\^~\^ OBJX KIT taken", 10)))
    for n, t in enumerate(tgs, 1):
        stand_near(t["pos"])
        R.step(["+use", "wait 300"], timeout=20)
        for k in range(5):
            R.step(["screenshotJPEG %s_plant%d_%04d" % (o["id"], n, k), "wait 480"] if FRAMES else ["wait 480"], timeout=20)
        R.step(["-use", "wait 300"], timeout=20)
        log("PLANT", n, bool(seen(r"\^~\^~\^ OBJX PLANT %d/%d" % (n, len(tgs)), 8)))
    # watch the blast from a distance
    if o.get("chain"):
        p = tgs[0]["pos"]
        c = o.get("chain_cam")
        vp = vantage(tgs[min(len(tgs) - 1, o.get("chain_target", 0))]["pos"])
        if c:
            tp(c[0], c[1], c[2] + 4, c[3], c[4])
        elif vp:
            tp(vp[0], vp[1], vp[2] - 22, 0, 0)
            aim(*tgs[min(len(tgs) - 1, o.get("chain_target", 0))]["pos"][:2], tgs[min(len(tgs) - 1, o.get("chain_target", 0))]["pos"][2] + 60)
            log("   chain vantage", [round(v) for v in vp])
        else:
            tp(p[0] + 420, p[1], p[2] + 28, 180, 5)
        frames("%s_chain" % o["id"], 36, 400)
    log("DONE %s seen:" % o["id"], bool(seen(r"\^~\^~\^ OBJX DONE %s " % o["id"], 60)))
    frames("%s_after" % o["id"], 6, 350)


def do_escort(i, o):
    act = [it for it in o["items"] if it["kind"] == "actor"][0]
    x, y, z = act["pos"]
    tp(x + 70, y, z + 28, 180, 0)
    aim(x, y, z + 50)
    frames("%s_captive" % o["id"], 6, 250)
    hold_use(500)
    seen(r"\^~\^~\^ OBJX ESCORT freed", 8)
    frames("%s_freed" % o["id"], 8, 250)
    dest = o["zone"]["pos"]
    tp(dest[0], dest[1], dest[2] + 28, 0, 0)       # he runs to the nearest player along the real navigation
    t0 = time.time()
    while time.time() - t0 < 240:
        if R.wait_log(r"\^~\^~\^ OBJX DONE %s " % o["id"], 0.1, 0):
            break
        frames("%s_walk" % o["id"], 1, 300)
        time.sleep(5)
    log("DONE %s seen:" % o["id"], bool(seen(r"\^~\^~\^ OBJX DONE %s " % o["id"], 10)), "after %.0f s" % (time.time() - t0))


def do_zone(i, o):
    z = o["zone"]
    cx, cy, cz = z["pos"]
    tp(cx, cy, cz + 28, 0, 0)
    perf = [it for it in o.get("items", []) if it["kind"] == "actor"]
    if o["type"] == "perform" and perf and FRAMES:
        R.step(["set cg_drawviewmodel 0", "wait 100"], timeout=20)
        for nm, (dx, dy, dz) in enumerate(o.get("cam", [[-60, -140, 0], [-60, 140, 0], [-130, -90, 20]])):
            G.cmd("pfcam", x=dx, y=dy, z=dz, k=i)
            time.sleep(0.6)
            G.frames("%s_perf%d" % (o["id"], nm), 10, 220)
        R.step(["set cg_drawviewmodel 1", "wait 100"], timeout=20)
    tp(cx, cy, cz + 28, 0, 0)
    secs = int(o.get("secs", 60))
    t0 = time.time()
    while time.time() - t0 < secs * 1.6 + 90:
        if R.wait_log(r"\^~\^~\^ OBJX DONE %s " % o["id"], 0.1, 0):
            break
        frames("%s_hold" % o["id"], 2, 350)
        R.step(["+attackprimary", "wait 500", "-attackprimary", "wait 100"], timeout=20)
        time.sleep(4)
    log("DONE %s seen:" % o["id"], bool(seen(r"\^~\^~\^ OBJX DONE %s " % o["id"], 20)))
    if o["type"] == "perform" and perf and FRAMES:
        R.step(["set cg_drawviewmodel 0", "wait 100"], timeout=20)
        G.cmd("pfcam", x=-60, y=-140, z=0, k=i)
        G.frames("%s_finish" % o["id"], 18, 250)
        R.step(["set cg_drawviewmodel 1", "wait 100"], timeout=20)


rundir = notes = None
try:
    extra = ["set coop_counterDebug 1", "set coop_objxFailsafe 900"]
    if HOLD:
        extra.append("set coop_objxHoldSecs " + HOLD)
    rundir, notes = G.boot("ox_" + LABEL, MAP, extra=extra)
    log("booted; players joined", notes.get("joined"))
    G.cmd("god")
    log("player active after intro:", G.wait_active())
    for i, o in enumerate(OBJS, 1):
        if ONLY and o["id"] not in ONLY:
            continue
        log("== objective", o["id"], o["type"])
        activate(i, o)
        t = o["type"]
        if t == "intel":
            do_intel(i, o)
        elif t == "radio":
            do_radio(i, o)
        elif t == "charge":
            do_charge(i, o)
        elif t == "escort":
            do_escort(i, o)
        elif t in ("perform", "hold"):
            do_zone(i, o)
        else:
            log("  (no auto handler for", t, ")")
    if END:
        log("-- exit gate check")
        G.cmd("endnow")
        ok = seen(r"==-----briefing|OBJX GATE open", 90)
        log("exit chain:", bool(ok))
    log("---- OBJX log ----")
    for l in G.objx_lines():
        if "tick" in l or "HOLD state" in l:
            continue
        log(l[:240])
    errs = G.errors()
    log("script errors:", len(errs), errs[:6])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
