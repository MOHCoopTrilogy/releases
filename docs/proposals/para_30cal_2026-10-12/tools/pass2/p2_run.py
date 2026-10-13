"""p2_run.py <label> <map> <x> <y> <z> <yaw> [key=value ...] - bug-3562 second pass: call a stick at a place, pin where
it holds, and follow the .30 cal man: the plan (why each site was taken or refused), the walk-up, the set-up, the
fire, the pack-up. Frames (JPEG) land in the run folder as <label>_<phase>_NNNN.jpg.
  foe=<dist>     three enemies that far down the squad's facing BEFORE the squad lands (the plan then aims at them)
  foehp=<n>      their health (default 1500, so that the gun has something to fire at for the frames)
  force=A|B|C    the planner's test hook (one mode only)
  pack=0         leave him on the gun at the end
  wait=<s>       how long to wait for a plan that sets up (default 240)
  cams=d:a,...   still cameras: distance : degrees round from the gun's facing (default 150:120,210:60,150:180,200:100,110:95)
"""
import json, math, os, re, sys, time
import p2lib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
HERE_MODE = sys.argv[3] == "here"
X, Y, Z, YAW = (0.0, 0.0, 0.0, float(sys.argv[6])) if HERE_MODE else [float(v) for v in sys.argv[3:7]]
OPT = dict(a.split("=", 1) for a in sys.argv[7:])
CAMS = [tuple(float(v) for v in c.split(":")) for c in OPT.get("cams", "150:120,210:60,150:180,200:100,110:95").split(",")]
GCAM = tuple(float(v) for v in OPT.get("gcam", "170:125").split(":"))
RES = {"label": LABEL, "map": MAP, "at": [X, Y, Z, YAW], "opt": OPT}
rundir = notes = None


def mglines(p0):
    return re.findall(r"\^~\^~\^ (PSQ t=[\d.]+ mg [^\r\n]*)", R.read_log()[p0:])


try:
    rundir, notes = G.boot("p2_" + LABEL, MAP, extra=OPT.get("extra", "").split(";") if OPT.get("extra") else ())
    if OPT.get("force"):
        G.cmd("force", tag=OPT["force"])
    if HERE_MODE:
        ph = G.cmd("here")
        X, Y, Z = [float(v) for v in re.search(r"P2 here \(([^)]*)\)", R.read_log()[ph:]).group(1).split()]
        G.log(LABEL, "the player's own position:", X, Y, Z)
    else:
        G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
        time.sleep(1.0)
    if OPT.get("purge"):
        pp = G.cmd("purge", timeout=60)
        G.log(LABEL, G.since(pp, r"P2 purge[^\r\n]*"))
    if OPT.get("foe"):
        d = float(OPT["foe"])
        G.cmd("foe", x=X + math.cos(math.radians(YAW)) * d, y=Y + math.sin(math.radians(YAW)) * d, z=Z + 40,
              yaw=YAW + 180, n=OPT.get("foehp", "1500"))
    p0 = G.cmd("call", x=X, y=Y, z=Z, yaw=YAW, tag="pin")
    if OPT.get("park"):
        px, py, pz = OPT["park"].split(",")
        G.cmd("tp", x=px, y=py, z=float(pz) + 8, yaw=YAW, pitch=0)
    seen = p0
    if OPT.get("bring"):
        # TEST SET-UP (said in the report): the gunner is stood 70u behind the hold point once the stick is down
        R.wait_log(r"PSQ t=[\d.]+ brain start", 120, p0)
        for k in range(20):
            time.sleep(2.0)
            pb = G.cmd("bring", x=X - math.cos(math.radians(YAW)) * 70, y=Y - math.sin(math.radians(YAW)) * 70, z=Z + 30,
                       n=OPT.get("hp", "0"))
            if "P2 bring k=" in R.read_log()[pb:]:
                G.log(LABEL, re.search(r"P2 bring k=[^\r\n]*", R.read_log()[pb:]).group(0))
                break
    t0 = time.time()
    done = False
    shot = 0
    wait = float(OPT.get("wait", 240))
    plans = 0
    lastbring = time.time()
    while time.time() - t0 < wait and not done:
        R.guard()
        m = re.search(r"PSQ t=[\d.]+ mg (site|nosite|setup k=1|setup abort=\w+)[^\r\n]*", R.read_log()[seen:])
        if not m:
            time.sleep(0.5)
            # TEST SET-UP: until a site is planned the gunner is kept 70u behind the hold point (the squad's
            # wedge would otherwise send him 300u off it, across ground this spot has no path over)
            if OPT.get("bring") and plans == 0 and time.time() - lastbring > 4:
                lastbring = time.time()
                G.cmd("bring", x=X - math.cos(math.radians(YAW)) * 70, y=Y - math.sin(math.radians(YAW)) * 70, z=Z + 30,
                      n=OPT.get("hp", "0"))
            continue
        seen += m.end()
        G.log(LABEL, m.group(0)[:330])
        if m.group(1) == "site":
            plans += 1
            if shot < 2:
                shot += 1
                G.cam(*GCAM)
                G.frames("%s_setup%d" % (LABEL, shot), 64, 150)
        if m.group(1) == "setup k=1":
            done = True
    RES["plans"] = plans
    RES["setup"] = done
    p1 = G.cmd("who")
    for l in G.since(p1, r"P2 (?:WHO|MEM)[^\r\n]*"):
        G.log("   ", l[:240])
    if done:
        time.sleep(1.5)
        for k, (dist, ang) in enumerate(CAMS):
            G.cam(dist, ang)
            G.still("%s_still_%d" % (LABEL, k))
        G.cam(*GCAM)
        if not OPT.get("foe"):
            G.cmd("enemy", n=OPT.get("edist", "800"))
        G.frames(LABEL + "_fire", 44, 150)
        G.cam(130, 100)
        G.still(LABEL + "_still_fire")
        if OPT.get("kill"):
            # he dies at the gun: the emplacement must stay, with a belt, and a player must be able to use it
            m = re.search(r"mg setup k=1 mode=(\w) gun=\(([^)]*)\) yaw=([-\d.]+) arc=\d+ top=[-\d.]+ seat=\(([^)]*)\)",
                          R.read_log()[p0:])
            gun = [float(v) for v in m.group(2).split()]
            gyaw = float(m.group(3))
            seat = [float(v) for v in m.group(4).split()]
            G.cam(*GCAM)
            pk = G.cmd("kill")
            G.frames(LABEL + "_death", 16, 150)
            left = R.wait_log(r"PSQ t=[\d.]+ mg left for the players[^\r\n]*", 15, pk)
            G.log(LABEL, left.group(0) if left else "NO 'mg left' line")
            RES["left"] = left.group(0) if left else None
            for k, (dist, ang) in enumerate(CAMS[:3]):
                G.cam(dist, ang)
                G.still("%s_left_%d" % (LABEL, k))
            if OPT.get("belt"):
                pb = G.cmd("belt", n=OPT["belt"])
                G.log(LABEL, G.since(pb, r"P2 belt set[^\r\n]*"))
            # the player steps up behind the gun and presses Use
            bx = gun[0] - math.cos(math.radians(gyaw)) * 52
            by = gun[1] - math.sin(math.radians(gyaw)) * 52
            G.cmd("tp", x=bx, y=by, z=seat[2] + 4, yaw=gyaw, pitch=0)
            time.sleep(0.8)
            R.step(["ui_hud 1", "set cg_drawviewmodel 1", "wait 200", "+use", "wait 120", "-use", "wait 900",
                    "screenshotJPEG %s_mount_0" % LABEL, "wait 150"], timeout=30)
            pm = G.cmd("pst")
            G.log(LABEL, "after Use:", G.since(pm, r"P2 PST[^\r\n]*"))
            R.step(["+attackprimary", "wait 1200", "screenshotJPEG %s_mount_fire" % LABEL, "wait 2400",
                    "screenshotJPEG %s_mount_hot" % LABEL, "wait 300", "-attackprimary", "wait 6000",
                    "screenshotJPEG %s_mount_cool" % LABEL, "wait 5000"], timeout=60)
            R.step(["+attackprimary", "wait 3500", "-attackprimary", "wait 9000", "+attackprimary", "wait 3500",
                    "screenshotJPEG %s_mount_empty" % LABEL, "wait 300", "-attackprimary", "wait 500"], timeout=60)
            R.step(["+use", "wait 120", "-use", "wait 900", "screenshotJPEG %s_dismount" % LABEL, "wait 150"], timeout=30)
            pm = G.cmd("pst")
            G.log(LABEL, "after second Use:", G.since(pm, r"P2 PST[^\r\n]*"))
            R.step(["+forward", "wait 600", "-forward", "wait 300"], timeout=30)
            pm = G.cmd("pst")
            G.log(LABEL, "after walking on:", G.since(pm, r"P2 PST[^\r\n]*"))
            for l in re.findall(r"(?:BELT EMPTY|coop_mg_overheat)[^\r\n]*", R.read_log()[pk:])[:4]:
                G.log("   LOG", l[:120])
        elif OPT.get("pack", "1") == "1":
            G.cam(*GCAM)
            G.cmd("nofoe")
            hx = X - math.cos(math.radians(YAW)) * 800
            hy = Y - math.sin(math.radians(YAW)) * 800
            p2 = G.cmd("hold", x="%.0f" % hx, y="%.0f" % hy, z=Z, yaw=YAW)
            G.frames(LABEL + "_packup", 44, 150)
            pk = R.wait_log(r"PSQ t=[\d.]+ mg packup", 25, p2)
            RES["packup"] = bool(pk)
            G.log(LABEL, "packup:", bool(pk))
    errs = G.errors()
    RES["errors"] = errs
    G.log("script errors:", len(errs), errs[:6])
    for l in mglines(p0):
        G.log("   ", l[:330])
    for l in re.findall(r"Path not found[^\r\n]*\r?\n[^\r\n]*", R.read_log()[p0:])[:6]:
        G.log("   PATH", l[:260])
except Exception as e:
    import traceback
    G.log("FAILED", repr(e), traceback.format_exc()[-900:])
    try:
        G.log("errors:", G.errors()[:8])
    except Exception:
        pass
finally:
    json.dump(RES, open(os.path.join(G.HERE, "run_%s.json" % LABEL), "w"), indent=1)
    G.end(rundir, notes)
