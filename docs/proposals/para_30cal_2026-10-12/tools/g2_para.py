"""g2_para.py <label> <new|old> <map> [site,site,...] - bug-3562: call a stick, hold it at each site in turn and
photograph the gunner's emplacement. new = overlay carries the patched parasquad.scr / mg42_idle.scr and the para
gun tik; old = the deployed scripts. Frames (JPEG) land in the run folder: <label>_<site>_<phase>_NNNN.jpg."""
import json, os, re, sys, time
import g1lib as G
R, S = G.R, G.S
LABEL, WHICH, MAP = sys.argv[1], sys.argv[2], sys.argv[3]
SITES = {
    # name: (x, y, z, yaw the squad faces, mode forced in the new script)
    "m3l2": {"obj": (-3608, 2303, 84, 225, "A"), "ground": (-3608, 2303, 84, 45, "B"), "bag": (-3194, 1460, 84, 0, "C")},
    "m4l1": {"obj": (-4577, -5881, -505, 0, "A"), "ground": (-3932, -6024, -500, 0, "B"), "bag": (-4905, -6105, -415, 122, "C")},
}
ORDER = sys.argv[4].split(",") if len(sys.argv) > 4 else ["obj", "ground", "bag"]
RES = {}


def cmd(what, timeout=40, **kv):
    p0 = len(R.read_log())
    R.step(["set g2_%s %s" % (k, v) for k, v in kv.items()] + ["set g2_cmd %s" % what], timeout=30)
    if not R.wait_log(r"\^~\^~\^ G2 did %s" % what, timeout, p0):
        raise RuntimeError("driver never did %s" % what)
    time.sleep(0.2)
    return p0


def who():
    p0 = cmd("who")
    m = re.search(r"\^~\^~\^ G2 WHO[^\r\n]*", R.read_log()[p0:])
    return m.group(0)[9:] if m else "?"


def frames(tag, n, ms=150, pre=()):
    seq = list(pre)
    for k in range(n):
        seq += ["screenshotJPEG %s_%04d" % (tag, k), "wait %d" % ms]
    R.step(seq, timeout=120 + n)


def cam(dist, ang):
    cmd("cam", n=dist, yaw=ang)
    time.sleep(0.6)


ex = []
if WHICH == "new":
    ex = [(os.path.join(G.HERE, "para_out/coop_mod/parasquad.scr"), "coop_mod/parasquad.scr"),
          (os.path.join(G.HERE, "para_out/anim/mg42_idle.scr"), "anim/mg42_idle.scr"),
          (os.path.join(G.HERE, "coop_30cal_para.tik"), "models/statweapons/coop_30cal_para.tik")]
ov = G.overlay("ov_g2p.pk3", "g2_para.scr", ex)
cg = G.install("new", "integ")
R.MAP = MAP
rundir = notes = None
try:
    extra = ["set coop_st_xp 1", "ui_hud 0", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
             "set g_ai 1", "set cg_drawviewmodel 0", "set coop_paraShootdownChance 0", "set s_volume 0"]
    rundir, notes = S.boot_session("g2_para_" + LABEL, cg, 1280, 720, extra, ov)
    G.log("booted", LABEL, WHICH, MAP, notes.get("md5"), "dog", notes.get("dog"))
    first = True
    for sname in ORDER:
        x, y, z, yaw, force = SITES[MAP][sname]
        tag = "%s_%s" % (LABEL, sname)
        cmd("force", tag=force if WHICH == "new" else "0")
        p0 = len(R.read_log())
        if first:
            cmd("tp", x=x, y=y, z=z, yaw=yaw, pitch=0)
            cmd("call", x=x, y=y, z=z, yaw=yaw)
            first = False
        else:
            cmd("hold", x=x, y=y, z=z, yaw=yaw)
        if WHICH == "old":
            cmd("fails", n=0)
        # wait for the plan (new script prints it) or the finished set-up (old script)
        pat = r"PSQ t=[\d.]+ mg (spot mode=(\w) gun=\(([^)]*)\) yaw=([-\d.]+)|setup k=1|nospot[^\r\n]*)"
        t0 = time.time()
        plan = None
        nospot = 0
        seen = p0
        while time.time() - t0 < 200:
            R.guard()
            m = re.search(pat, R.read_log()[seen:])
            if m:
                seen += m.end()
                if m.group(1).startswith("nospot"):
                    nospot += 1
                    G.log(tag, m.group(1)[:110])
                    if WHICH == "old" and nospot == 1:
                        pass
                    continue
                plan = m
                break
            time.sleep(0.5)
        if not plan:
            G.log(tag, "NO PLAN in 200 s (nospot x%d) -" % nospot, who())
            RES[sname] = {"result": "no spot", "nospot": nospot}
            continue
        done = plan.group(1).startswith("setup")
        tries = 0
        while not done and tries < 6:
            tries += 1
            G.log(tag, "plan %d:" % tries, plan.group(1)[:120])
            cam(165, 118)
            frames("%s_setup%d" % (tag, tries), 70, 150)          # the walk-up and the set-down, ~10 s at 6.7 fps
            ok = R.wait_log(r"PSQ t=[\d.]+ mg setup (k=1|abort=\w+)", 30, seen)
            G.log(tag, "setup:", ok.group(0)[-40:] if ok else "never")
            if ok and "k=1" in ok.group(0):
                done = True
                break
            seen = len(R.read_log())
            plan = R.wait_log(r"PSQ t=[\d.]+ mg (spot mode=(\w) gun=\(([^)]*)\) yaw=([-\d.]+))", 60, seen)
            if not plan:
                break
            seen = plan.end()
        if not done:
            RES[sname] = {"result": "abort", "tries": tries}
            continue
        time.sleep(1.5)
        w = who()
        G.log(tag, w)
        RES[sname] = {"result": "setup", "who": w}
        for k, (dist, ang) in enumerate(((165, 118), (120, 75), (150, 180), (190, 20), (105, 92))):
            cam(dist, ang)
            R.step(["screenshotJPEG %s_still_%d" % (tag, k), "wait 120"], timeout=30)
        cam(165, 118)
        cmd("enemy")
        frames(tag + "_fire", 36, 150)
        time.sleep(1.0)
        R.step(["screenshotJPEG %s_still_fire" % tag, "wait 120"], timeout=30)
        # pack-up: the hold point jumps 700u behind the gun
        import math
        hx = x - math.cos(math.radians(yaw)) * 700
        hy = y - math.sin(math.radians(yaw)) * 700
        if sname == ORDER[-1]:
            cmd("force", tag="0")
            cmd("hold", x="%.0f" % hx, y="%.0f" % hy, z=z, yaw=yaw)
            frames(tag + "_packup", 40, 150)
            pk = R.wait_log(r"PSQ t=[\d.]+ mg packup", 20, seen)
            G.log(tag, "packup:", bool(pk), who())
            RES[sname]["packup"] = bool(pk)
    t = R.read_log()
    errs = sorted(set(l[-150:] for l in t.splitlines() if "Script Error" in l or "not properly loaded" in l))
    G.log("script errors:", len(errs), errs[:6])
    for l in re.findall(r"\^~\^~\^ PSQ[^\r\n]*mg[^\r\n]*", t):
        G.log("   ", l[6:150])
except Exception as e:
    import traceback
    G.log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    json.dump(RES, open(os.path.join(G.HERE, "para_%s.json" % LABEL), "w"), indent=1)
    try:
        if rundir:
            S.end_session(rundir, notes or {})
    except Exception as e:
        G.log("end_session", repr(e))
    G.restore_ship()
