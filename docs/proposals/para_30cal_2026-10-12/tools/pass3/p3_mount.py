"""p3_mount.py <label> <map> <x> <y> <z> <yaw> [map=tn1,tn2] [purge=1] - a PLAYER on low guns, seen from the side.
1. a stick is called at x y z; when the gunner has set up on his own, side stills of HIM on the gun (two sides, one
   telephoto), then he is killed there (the test's doing) and the gun is the players'.
2. the player steps behind the left gun, Use: first person + side stills (both sides, one firing), Use again.
3. map=<targetnames>: the same on the map's own guns of those names.
The side view of the player is the engine agent's recipe: a script camera across the gun + cg_3rd_person."""
import json, math, os, re, sys, time
import p3lib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
X, Y, Z, YAW = [float(v) for v in sys.argv[3:7]]
OPT = dict(a.split("=", 1) for a in sys.argv[7:])
rundir = notes = None
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


def side(key, fire=True):
    R.step(["wait 300", "screenshotJPEG %s_%s_first" % (LABEL, key), "wait 200"], timeout=30)
    G.cmd("arc", n=0)
    G.cmd("sidecam", yaw=90, pitch=0)
    R.step(["set cg_cameradist 150", "set cg_cameraheight -14", "set cg_camerasideoffset 0", "ui_hud 0",
            "set cg_3rd_person 1", "wait 1800", "screenshotJPEG %s_%s_side" % (LABEL, key), "wait 200"], timeout=30)
    if fire:
        R.step(["+attackprimary", "wait 700", "screenshotJPEG %s_%s_side_fire" % (LABEL, key), "wait 300",
                "-attackprimary", "wait 600"], timeout=30)
    G.cmd("sidecam", yaw=-90, pitch=0)
    R.step(["wait 900", "screenshotJPEG %s_%s_side_left" % (LABEL, key), "wait 300"], timeout=30)
    G.cmd("sidecam", yaw=150, pitch=12)
    R.step(["set cg_cameradist 120", "wait 900", "screenshotJPEG %s_%s_rear" % (LABEL, key), "wait 300",
            "set cg_3rd_person 0", "wait 300"], timeout=30)
    G.cmd("nocam")
    G.cmd("arc", n=45)


def mount(key, num=0, fire=True):
    pb = G.cmd("behind", n=num)
    log(key, G.since(pb, r"P3 behind[^\r\n]*"))
    time.sleep(0.8)
    R.step(["+use", "wait 120", "-use", "wait 900"], timeout=30)
    pm = G.cmd("pst")
    st = G.since(pm, r"P3 PST[^\r\n]*")
    log(key, "after Use:", st)
    if st and "turret=none" in st[-1]:
        log(key, "DID NOT MOUNT")
        return False
    side(key, fire)
    R.step(["+use", "wait 120", "-use", "wait 700"], timeout=30)
    log(key, "after second Use:", G.since(G.cmd("pst"), r"P3 PST[^\r\n]*"))
    return True


try:
    rundir, notes = G.boot("p3_" + LABEL, MAP, files=["coop_mod/player_legs.st", "coop_mod/player_torso.st",
                                                         "models/player/base/anims_shared.txt"])
    G.cmd("tp", x=X, y=Y, z=Z + 8, yaw=YAW, pitch=0)
    time.sleep(1.0)
    if OPT.get("purge"):
        log(G.since(G.cmd("purge", timeout=60), r"P3 purge[^\r\n]*"))
    p0 = G.cmd("call", x=X, y=Y, z=Z, yaw=YAW, tag="pin")
    if OPT.get("park"):
        px, py, pz = OPT["park"].split(",")
        G.cmd("tp", x=px, y=py, z=float(pz) + 8, yaw=YAW, pitch=0)
    if OPT.get("bring"):
        # TEST SET-UP (said in the report): the gunner is stood 70u behind the hold point until a site is planned
        R.wait_log(r"PSQ t=[\d.]+ brain start", 120, p0)
        tb = time.time()
        while time.time() - tb < 120 and not re.search(r"PSQ t=[\d.]+ mg site", R.read_log()[p0:]):
            G.cmd("bring", x=X - math.cos(math.radians(YAW)) * 70, y=Y - math.sin(math.radians(YAW)) * 70, z=Z + 30, n=0)
            time.sleep(4.0)
    m = R.wait_log(r"PSQ t=[\d.]+ mg setup k=1[^\r\n]*", float(OPT.get("wait", 200)), p0)
    log(m.group(0)[:260] if m else "NO SET-UP")
    if m:
        time.sleep(2.0)
        cams = [(120, 90, 50, 28), (120, 270, 50, 28), (95, 90, 28, 14), (110, 135, 45, 28)]
        if OPT.get("room"):
            cams = [(78, 90, 75, 28), (78, 270, 75, 28), (70, 120, 60, 20), (90, 150, 75, 28)]
        for k, (dist, ang, fov, back) in enumerate(cams):
            c = G.cmd("camg", n=dist, yaw=ang, z=0, pitch=back)
            time.sleep(0.5)
            R.step(["fov %d" % fov, "wait 400", "screenshotJPEG %s_ai_side_%d" % (LABEL, k), "wait 150", "fov 80", "wait 200"], timeout=30)
            log("ai side", k, G.since(c, r"P3 camg[^\r\n]*"), G.since(G.cmd("gunpos"), r"P3 GUN[^\r\n]*"))
            if k in (0, 3):
                # the test makes him fire a burst for the picture (level, down the middle of his arc)
                G.cmd("fireon")
                R.step(["fov %d" % fov, "wait 500", "screenshotJPEG %s_ai_side_%d_fire_a" % (LABEL, k), "wait 170",
                        "screenshotJPEG %s_ai_side_%d_fire_b" % (LABEL, k), "wait 170",
                        "screenshotJPEG %s_ai_side_%d_fire_c" % (LABEL, k), "wait 150", "fov 80", "wait 100"], timeout=30)
                G.cmd("fireoff")
        pk = G.cmd("kill")
        left = R.wait_log(r"PSQ t=[\d.]+ mg left for the players[^\r\n]*", 15, pk)
        log(left.group(0) if left else "NO 'mg left' line")
        time.sleep(1.0)
        G.cmd("camg", n=120, yaw=90, z=0, pitch=14)
        R.step(["fov 45", "wait 400", "screenshotJPEG %s_left_side" % LABEL, "wait 150", "fov 80", "wait 200"], timeout=30)
        log("left gun:", G.since(G.cmd("gunpos"), r"P3 GUN[^\r\n]*"))
        mount("leftgun")
    if OPT.get("map"):
        tl = G.since(G.cmd("turrets", timeout=60), r"P3 turret [^\r\n]*")
        for l in tl:
            log("  ", l[:200])
        for tn in OPT["map"].split(","):
            hit = [l for l in tl if l.rstrip().endswith("tn=" + tn)]
            if not hit:
                log(tn, "not found")
                continue
            num = int(re.search(r"num=(\d+)", hit[0]).group(1))
            mount(tn, num, fire=False)
    log("script errors:", G.errors()[:6])
    for l in G.psq(p0):
        if " mg " in l or "rescue" in l or " lz plan" in l:
            log("   ", l[:300])
except Exception as e:
    import traceback
    log("FAILED", repr(e), traceback.format_exc()[-900:])
    try:
        log("errors:", G.errors()[:8])
    except Exception:
        pass
finally:
    G.end(rundir, notes)
