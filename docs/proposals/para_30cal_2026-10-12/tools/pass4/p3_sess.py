"""p3_sess.py <label> <map> <x> <y> <z> <yaw> [key=value ...] - one paratrooper session: call a stick at a place and
follow it. Frames (JPEG) land in the run folder G:/mohaa-hudfeed5/runs/p3_<label>/ as <label>_<phase>_NNNN.jpg.
  pin=0          the squad's anchor is the player himself (default 1: a fixed hold point at x y z = a player who stands there)
  park=x,y,z     where the player (the camera, notarget, no damage) waits
  purge=1        TEST SET-UP: the map's Germans are removed       foe=<dist> foehp=<n>: three placed riflemen
  ref=<commit>   the mod scripts of that commit (the 'before' of a comparison)
  gun=1          follow the .30 cal: frames of walk-up / set-up / fire / pack-up (gcam=dist:angle, fire=<frames>, pack=0)
  close=1        close stills of the gunner on the gun (hands, stock, bipod)
  watch=<s>      how long the fight is metered (default 0 = until the gun phases are done)
  wait=<s>       how long to wait for a set-up (default 200)
  kill=1         the gunner is killed on the gun; the player then mounts it (third person stills)
  cv=a:b;c:d     extra cvars
"""
import json, math, os, re, sys, time
import p3lib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
HERE_ = sys.argv[3] == "here"
X, Y, Z, YAW = (0.0, 0.0, 0.0, 0.0) if HERE_ else [float(v) for v in sys.argv[3:7]]
OPT = dict(a.split("=", 1) for a in sys.argv[7:])
GCAM = tuple(float(v) for v in OPT.get("gcam", "170:125").split(":"))
RES = {"label": LABEL, "map": MAP, "at": [X, Y, Z, YAW], "opt": OPT}
rundir = notes = None
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


def camg(dist, ang, up=0, back=30):
    p = G.cmd("camg", n=dist, yaw=ang, z=up, pitch=back)
    time.sleep(0.5)
    m = G.since(p, r"P3 camg[^\r\n]*")
    return m[-1] if m else ""


try:
    extra = ["set %s %s" % tuple(c.split(":", 1)) for c in OPT.get("cv", "").split(";") if c]
    rundir, notes = G.boot("p3_" + LABEL, MAP, extra=extra, ref=OPT.get("ref"))
    if HERE_:
        hh = G.since(G.cmd("here"), r"P3 here \( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) ang=\( [-\d.]+ ([-\d.]+)")
        X, Y, Z, YAW = [float(v) for v in hh[-1]]
        RES["at"] = [X, Y, Z, YAW]
        log("call at the player's spawn:", X, Y, Z, YAW)
    G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
    time.sleep(1.0)
    if OPT.get("purge"):
        pp = G.cmd("purge", timeout=60)
        log(G.since(pp, r"P3 purge[^\r\n]*"))
    pg = G.cmd("ger", x=X, y=Y, z=Z, n=OPT.get("gr", "3000"))
    gl = G.since(pg, r"P3 GER d=[^\r\n]*")
    log("germans within", OPT.get("gr", "3000"), ":", G.since(pg, r"P3 GERN \d+"))
    for l in sorted(gl, key=lambda s: int(re.search(r"d=(\d+)", s).group(1)))[:14]:
        log("   ", l[:110])
    if OPT.get("foe"):
        d = float(OPT["foe"])
        G.cmd("foe", x=X + math.cos(math.radians(YAW)) * d, y=Y + math.sin(math.radians(YAW)) * d, z=Z + 40,
              yaw=YAW + 180, n=OPT.get("foehp", "300"))
    if OPT.get("force"):
        G.cmd("force", tag=OPT["force"])      # TEST SET-UP: only this kind of gun site is planned (A = cover)
    G.cmd("meter", x=X, y=Y, z=Z)
    p0 = G.cmd("call", x=X, y=Y, z=Z, yaw=YAW, tag="pin" if OPT.get("pin", "1") == "1" else "free")
    if OPT.get("park"):
        px, py, pz = OPT["park"].split(",")
        G.cmd("tp", x=px, y=py, z=float(pz) + 8, yaw=YAW, pitch=0)
    t0 = time.time()
    seen = p0
    done = False
    plans = 0
    lastbring = 0
    wait = float(OPT.get("wait", 200))
    gun = OPT.get("gun") == "1" or OPT.get("close") == "1" or OPT.get("kill") == "1"
    while gun and time.time() - t0 < wait and not done:
        R.guard()
        m = re.search(r"PSQ t=[\d.]+ mg (site|nosite|setup k=1|setup abort=\w+|refuse)[^\r\n]*", R.read_log()[seen:])
        if not m:
            time.sleep(0.4)
            # bring=1, TEST SET-UP (said in the report): until a site is planned the gunner is stood 70u behind the
            # hold point (a room with no pathnodes: he cannot walk in by himself)
            if OPT.get("bring") and plans == 0 and time.time() - lastbring > 4 and "brain start" in R.read_log()[p0:]:
                lastbring = time.time()
                G.cmd("bring", x=X - math.cos(math.radians(YAW)) * 70, y=Y - math.sin(math.radians(YAW)) * 70, z=Z + 30, n=0)
            continue
        seen += m.end()
        log(m.group(0)[:330])
        if m.group(1) == "site":
            plans += 1
            if plans <= 2 and OPT.get("gun") == "1":
                log(camg(*GCAM))
                G.frames("%s_setup%d" % (LABEL, plans), int(OPT.get("upf", 70)), 150)
        if m.group(1) == "setup k=1":
            done = True
    RES["plans"] = plans
    RES["setup"] = done
    if done:
        time.sleep(1.0)
        ms = re.search(r"mg setup k=1 mode=(\w) gun=\(([^)]*)\) yaw=([-\d.]+) arc=\d+ top=[-\d.]+ seat=\(([^)]*)\)", R.read_log()[p0:])
        gunp, gyaw, seat = G.vec(ms.group(2)), float(ms.group(3)), G.vec(ms.group(4))
        if OPT.get("gun") == "1":
            fc = tuple(float(v) for v in OPT.get("fcam", "125:120").split(":"))
            pf = p0 + ms.end()
            if OPT.get("enemy"):
                # TEST SET-UP (said in the report): three riflemen placed <enemy> units down the gun's line
                pe = G.cmd("enemy", n=OPT["enemy"])
                log(G.since(pe, r"P3 enemy at=[^\r\n]*"))
            for rep in range(int(OPT.get("firereps", 2))):
                log(camg(*fc))
                mf = R.wait_log(r"PSQ t=[\d.]+ mg (track|suppress)[^\r\n]*", float(OPT.get("firewait", 45)), pf)
                log("fire trigger:", mf.group(0)[:90] if mf else None)
                if not mf and rep > 0:
                    break
                log(camg(*fc))
                G.frames("%s_fire%d" % (LABEL, rep), int(OPT.get("fire", 60)), 150)
                pq = G.cmd("gunpos")
                log(G.since(pq, r"P3 GUN[^\r\n]*"))
                pf = len(R.read_log())
        if OPT.get("close") == "1":
            # close stills: side, rear quarter, front quarter, the other side; first now, then after a wait (in a fight)
            for rnd in range(int(OPT.get("rounds", 2))):
                for k, (dist, ang, up, back) in enumerate([(62, 90, 0, 28), (70, 150, 0, 28), (66, 270, 0, 28), (75, 215, 0, 28),
                                                           (58, 100, -30, 20)]):
                    c = camg(dist, ang, up, back)
                    pq = G.cmd("gunpos")
                    G.still("%s_close%d_%d" % (LABEL, rnd, k))
                    log("close", rnd, k, c[:70], G.since(pq, r"P3 GUN[^\r\n]*"))
                if rnd == 0:
                    c = camg(70, 90, 0, 6)
                    R.step(["fov 28", "wait 400", "screenshotJPEG %s_tele_mount" % LABEL, "wait 150", "fov 80", "wait 200"], timeout=30)
                    c = camg(85, 115, 0, 34)
                    R.step(["fov 34", "wait 400", "screenshotJPEG %s_tele_hands" % LABEL, "wait 150", "fov 80", "wait 200"], timeout=30)
                    time.sleep(float(OPT.get("closewait", 6)))
        if OPT.get("kill"):
            log(camg(*GCAM))
            pk = G.cmd("kill")
            G.frames(LABEL + "_death", 14, 150)
            left = R.wait_log(r"PSQ t=[\d.]+ mg left for the players[^\r\n]*", 15, pk)
            log(left.group(0) if left else "NO 'mg left' line")
            bx = gunp[0] - math.cos(math.radians(gyaw)) * 52
            by = gunp[1] - math.sin(math.radians(gyaw)) * 52
            G.cmd("tp", x=bx, y=by, z=seat[2] + 4, yaw=gyaw, pitch=0)
            time.sleep(0.8)
            R.step(["wait 200", "+use", "wait 120", "-use", "wait 900"], timeout=30)
            pm = G.cmd("pst")
            log("after Use:", G.since(pm, r"P3 PST[^\r\n]*"))
            # third person: what the others see of him
            for k, (yaw_, rng) in enumerate([(90, 110), (150, 120), (210, 120), (270, 110)]):
                R.step(["set cg_3rd_person 1", "set cg_cameradist %d" % rng, "set cg_camerascale 1", "set cg_cameraheight 30",
                        "wait 300", "screenshotJPEG %s_mount3p_%d" % (LABEL, k), "wait 150"], timeout=30)
            R.step(["+attackprimary", "wait 900", "screenshotJPEG %s_mount3p_fire" % LABEL, "wait 300", "-attackprimary",
                    "wait 300", "set cg_3rd_person 0", "wait 200", "screenshotJPEG %s_mount1p" % LABEL, "wait 200",
                    "+use", "wait 120", "-use", "wait 600"], timeout=60)
        elif OPT.get("gun") == "1" and OPT.get("pack", "1") == "1":
            log(camg(*GCAM))
            hx = X - math.cos(math.radians(YAW)) * 800
            hy = Y - math.sin(math.radians(YAW)) * 800
            p2 = G.cmd("hold", x="%.0f" % hx, y="%.0f" % hy, z=Z, yaw=YAW)
            G.frames(LABEL + "_packup", 50, 150)
            pk = R.wait_log(r"PSQ t=[\d.]+ mg packup", 25, p2)
            log("packup:", bool(pk))
    w = float(OPT.get("watch", 0))
    if OPT.get("top"):
        # TEST VIEW: from <top> units straight above the hold point, one frame a second until <watch> seconds are up
        G.cmd("fly", x=X, y=Y, z=Z + float(OPT["top"]), pitch=89, yaw=YAW)
        R.step(["fov %s" % OPT.get("topfov", "90"), "wait 300"], timeout=20)
        n = max(1, int(w - (time.time() - t0)))
        for k0 in range(0, n, 30):
            G.frames("%s_top%03d" % (LABEL, k0), min(30, n - k0), 1000)
        R.step(["fov 80", "wait 100"], timeout=20)
    while time.time() - t0 < w:
        R.guard()
        time.sleep(1.0)
    p1 = G.cmd("sq")
    for l in G.since(p1, r"P3 SQ[^\r\n]*"):
        log("   ", l[:250])
    t = R.read_log()[p0:]
    for l in re.findall(r"P3 (?:LAND|TELE)[^\r\n]*", t):
        log("   ", l[:200])
    mt = re.findall(r"P3 METER t=[^\r\n]*", t)
    for l in mt[::max(1, len(mt) // 8)] + mt[-1:]:
        log("   ", l[:220])
    RES["meter"] = mt[-1] if mt else None
    errs = G.errors()
    RES["errors"] = errs
    log("script errors:", len(errs), errs[:6])
    for l in G.psq(p0):
        if OPT.get("all") == "1" or " mg " in l or "walkout" in l or " land" in l or "rescue" in l or " lz " in l or " tac " in l or "cover k" in l:
            log("   ", l[:330])
    cnt = {}
    for l in G.psq(p0):
        k = " ".join(l.split()[2:4])
        cnt[k] = cnt.get(k, 0) + 1
    log("PSQ line kinds:", sorted(cnt.items(), key=lambda kv: -kv[1])[:30])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
    try:
        log("errors:", G.errors()[:8])
    except Exception:
        pass
finally:
    json.dump(RES, open(os.path.join(G.HERE, "logs", "run_%s.json" % LABEL), "w"), indent=1)
    G.end(rundir, notes)
