"""p4_pitch.py <label> <map> <x> <y> <z> <yaw> [purge=1] [bring=1] [park=x,y,z] [room=1] - fourth pass, task 1:
the gun under pitch and at rest. A stick is called; the set-up is filmed from the side (the gun muzzle-up while it is
set down, level when he takes it); then the AI gunner is aimed (the TEST'S doing: 'aimp') 0 / +12 / +20 / +25 / -10
degrees and photographed from the side; he is killed (the test's doing); the left gun at rest; a player takes it and
looks 0 / +12 / +20 / -10; he gets off; the rest again."""
import json, math, os, re, sys, time
import p3lib as G
R = G.R
LABEL, MAP = sys.argv[1], sys.argv[2]
X, Y, Z, YAW = [float(v) for v in sys.argv[3:7]]
OPT = dict(a.split("=", 1) for a in sys.argv[7:])
rundir = notes = None
OUT = open(os.path.join(G.HERE, "logs", "run_%s.txt" % LABEL), "w")
SIDE = (78, 90, 70, 28) if OPT.get("room") else (112, 90, 42, 28)
CZ = float(OPT.get("cz", -44))


def log(*a):
    G.log(LABEL, *a)
    OUT.write(" ".join(str(x) for x in a) + "\n")
    OUT.flush()


def gst(tag):
    p = G.cmd("gst")
    time.sleep(0.2)
    log(tag, G.since(p, r"P3 GST[^\r\n]*"))


def shot(name, fov):
    R.step(["fov %d" % fov, "wait 350", "screenshotJPEG %s_%s" % (LABEL, name), "wait 150", "fov 80", "wait 150"], timeout=30)


try:
    rundir, notes = G.boot("p4_" + LABEL, MAP, files=["coop_mod/player_legs.st", "coop_mod/player_torso.st",
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
        R.wait_log(r"PSQ t=[\d.]+ brain start", 120, p0)
        tb = time.time()
        while time.time() - tb < 120 and not re.search(r"PSQ t=[\d.]+ mg site", R.read_log()[p0:]):
            G.cmd("bring", x=X - math.cos(math.radians(YAW)) * 70, y=Y - math.sin(math.radians(YAW)) * 70, z=Z + 30, n=0)
            time.sleep(4.0)
    # the set-down and the take, from the side: frames from the moment he is at the seat
    m = R.wait_log(r"PSQ t=[\d.]+ mg walk how=\d+ left=[-\d.]+ ok=1", float(OPT.get("wait", 200)), p0)
    log("walk:", m.group(0) if m else None)
    if m:
        c = G.cmd("camg", n=SIDE[0], yaw=SIDE[1], z=CZ, pitch=SIDE[3])
        log(G.since(c, r"P3 camg[^\r\n]*"))
        G.frames(LABEL + "_take", 44, 100, pre=["fov %d" % SIDE[2], "wait 100"])
        R.step(["fov 80", "wait 100"], timeout=20)
    m = R.wait_log(r"PSQ t=[\d.]+ mg setup k=1[^\r\n]*", 40, p0)
    log(m.group(0)[:260] if m else "NO SET-UP")
    if m:
        time.sleep(1.5)
        G.cmd("others", n=1)        # TEST SET-UP: the rest of the squad is hidden for the stills
        for el, fire in ((0, 0), (12, 0), (20, 0), (20, 1), (25, 0), (-10, 0), (0, 0)):
            G.cmd("aimp", pitch=el, yaw=0, n=fire)
            time.sleep(1.8)
            c = G.cmd("camg", n=SIDE[0], yaw=SIDE[1], z=CZ, pitch=SIDE[3])
            gst("ai el=%d fire=%d" % (el, fire))
            shot("ai_el%+03d%s" % (el, "_fire" if fire else ""), SIDE[2])
            if el == 20 and not fire:
                G.cmd("camg", n=SIDE[0], yaw=270, z=CZ, pitch=SIDE[3])
                shot("ai_el+20_left", SIDE[2])
            if fire:
                G.cmd("aimp", pitch=el, yaw=0, n=0)
        # the test kills him: the gun is left, and lies back
        G.cmd("camg", n=SIDE[0], yaw=SIDE[1], z=CZ, pitch=SIDE[3])
        pk = G.cmd("kill")
        G.frames(LABEL + "_death", 16, 120, pre=["fov %d" % SIDE[2], "wait 60"])
        R.step(["fov 80", "wait 100"], timeout=20)
        left = R.wait_log(r"PSQ t=[\d.]+ mg left for the players[^\r\n]*", 15, pk)
        log(left.group(0) if left else "NO 'mg left' line")
        time.sleep(1.5)
        gst("rest after death")
        G.cmd("camg", n=SIDE[0], yaw=SIDE[1], z=CZ, pitch=28)
        shot("rest_side", 45 if not OPT.get("room") else 70)
        G.cmd("camg", n=SIDE[0], yaw=270, z=CZ, pitch=28)
        shot("rest_left", 45 if not OPT.get("room") else 70)
        G.cmd("camg", n=SIDE[0] + 10, yaw=150, z=CZ + 30, pitch=28)
        shot("rest_rear", 50 if not OPT.get("room") else 75)
        G.cmd("nocorpse")           # TEST SET-UP: the dead gunner is taken out of the picture
        G.cmd("others", n=1)
        time.sleep(0.5)
        G.cmd("camg", n=SIDE[0], yaw=SIDE[1], z=CZ, pitch=28)
        shot("rest_side_clean", 45 if not OPT.get("room") else 70)
        G.cmd("camg", n=SIDE[0] + 10, yaw=150, z=CZ + 30, pitch=28)
        shot("rest_rear_clean", 50 if not OPT.get("room") else 75)
        # a player takes it
        pb = G.cmd("behind", n=0)
        log(G.since(pb, r"P3 behind[^\r\n]*"))
        time.sleep(0.8)
        R.step(["+use", "wait 120", "-use", "wait 250"], timeout=30)
        gst("player 0.4s after Use")
        time.sleep(0.6)
        st = G.since(G.cmd("pst"), r"P3 PST[^\r\n]*")
        log("after Use:", st)
        if st and "turret=none" not in st[-1]:
            G.cmd("arc", n=0)
            G.cmd("sidecam", yaw=90, pitch=0)
            R.step(["set cg_cameradist 150", "set cg_cameraheight -14", "set cg_camerasideoffset 0", "ui_hud 0",
                    "set cg_3rd_person 1", "wait 1500"], timeout=30)
            for el, fire in ((0, 0), (12, 0), (20, 0), (20, 1), (25, 0), (-10, 0), (0, 0)):
                G.cmd("pcap", pitch=el, n=1)      # TEST SET-UP: the pitch is pinned for the still
                time.sleep(1.0)
                gst("player el=%d" % el)
                if fire:
                    R.step(["+attackprimary", "wait 600", "screenshotJPEG %s_pl_el%+03d_fire" % (LABEL, el), "wait 200",
                            "-attackprimary", "wait 400"], timeout=30)
                else:
                    R.step(["wait 200", "screenshotJPEG %s_pl_el%+03d" % (LABEL, el), "wait 200"], timeout=30)
                if el == 20 and not fire:
                    G.cmd("sidecam", yaw=-90, pitch=0)
                    R.step(["wait 900", "screenshotJPEG %s_pl_el+20_left" % LABEL, "wait 200"], timeout=30)
                    G.cmd("sidecam", yaw=90, pitch=0)
                    time.sleep(0.9)
            G.cmd("pcap", pitch=0, n=0)
            R.step(["set cg_3rd_person 0", "wait 300"], timeout=30)
            G.cmd("nocam")
            G.cmd("arc", n=45)
            R.step(["+use", "wait 120", "-use", "wait 400"], timeout=30)
            log("after second Use:", G.since(G.cmd("pst"), r"P3 PST[^\r\n]*"))
            # he is off it: it lies back again
            G.cmd("camg", n=SIDE[0], yaw=SIDE[1], z=CZ, pitch=28)
            G.frames(LABEL + "_off", 12, 120, pre=["fov %d" % (45 if not OPT.get("room") else 70), "wait 60"])
            R.step(["fov 80", "wait 100"], timeout=20)
            time.sleep(1.0)
            gst("rest after the player")
    log("script errors:", G.errors()[:6])
    for l in G.psq(p0):
        if " mg " in l or "rescue" in l:
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
