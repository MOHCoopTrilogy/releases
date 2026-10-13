"""g2_probe.py <map> [x,y,z ...] - bug-3562: where around here would the gunner find a place, per mode?
No stick is called: the driver runs parasquad.scr::findMgSpot for the player at each point, 8 facings x 3 modes."""
import os, re, sys, time
import g1lib as G
R, S = G.R, G.S
MAP = sys.argv[1]
ONLY = os.environ.get("ONLY", "")
GRID = None
ARGS = sys.argv[2:]
if ARGS and ARGS[0].startswith("grid:"):
    GRID = tuple(int(v) for v in ARGS[0][5:].split(","))
    ARGS = ARGS[1:]
PTS = [tuple(float(v) for v in a.split(",")) for a in ARGS]
ex = [(os.path.join(G.HERE, "para_out/coop_mod/parasquad.scr"), "coop_mod/parasquad.scr"),
      (os.path.join(G.HERE, "para_out/anim/mg42_idle.scr"), "anim/mg42_idle.scr"),
      (os.path.join(G.HERE, "coop_30cal_para.tik"), "models/statweapons/coop_30cal_para.tik")]
ov = G.overlay("ov_g2p.pk3", "g2_para.scr", ex)
cg = G.install("new", "integ")
R.MAP = MAP
rundir = notes = None


def cmd(what, timeout=60, **kv):
    p0 = len(R.read_log())
    R.step(["set g2_%s %s" % (k, v) for k, v in kv.items()] + ["set g2_cmd %s" % what], timeout=30)
    if not R.wait_log(r"\^~\^~\^ G2 did %s" % what, timeout, p0):
        raise RuntimeError("driver never did %s" % what)
    time.sleep(0.2)
    return p0


try:
    extra = ["set coop_st_xp 1", "ui_hud 0", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
             "set g_ai 0", "set cg_drawviewmodel 0"]
    rundir, notes = S.boot_session("g2_probe_" + MAP, cg, 1280, 720, extra, ov)
    p0 = cmd("here")
    m = re.search(r"G2 here \(([^)]*)\)", R.read_log()[p0:])
    here = [float(v) for v in m.group(1).split()]
    G.log(MAP, "spawn", here)
    pts = PTS or [(here[0] + dx, here[1] + dy, here[2] + 40) for dx in (-700, 0, 700) for dy in (-700, 0, 700)]
    if GRID:
        span, step = GRID
        pts = [(here[0] + dx, here[1] + dy, here[2] + 60) for dx in range(-span, span + 1, step) for dy in range(-span, span + 1, step)]
    for (x, y, z) in pts:
        cmd("tp", x=x, y=y, z=z, yaw=0, pitch=0)
        time.sleep(1.2)
        pr = cmd("ray") if not ONLY else len(R.read_log())
        for l in re.findall(r"G2 RAY[^\r\n]*", R.read_log()[pr:]):
            G.log("    ", l[7:])
        p0 = cmd("probe", timeout=90, tag=ONLY or "ABC")
        t = R.read_log()[p0:]
        hits = re.findall(r"\^~\^~\^ G2 PROBE (\w) yaw=(\d+) from=\(([^)]*)\) gun=\(([^)]*)\) stand=\(([^)]*)\) top=(\d+)", t)
        ns = re.findall(r"PSQ t=[\d.]+ mg nospot ([^\r\n]*)", t)
        frm = hits[0][2] if hits else "?"
        G.log("point %.0f,%.0f,%.0f (on ground at %s): A x%d  B x%d  C x%d" % (
            x, y, z, frm, sum(1 for h in hits if h[0] == "A"), sum(1 for h in hits if h[0] == "B"), sum(1 for h in hits if h[0] == "C")))
        for h in hits:
            if h[0] in ("A", "C"):
                G.log("     %s yaw=%s gun=(%s) stand=(%s) top=%s" % (h[0], h[1], h[3], h[4], h[5]))
        if not any(h[0] == "A" for h in hits):
            for n in ns[:2]:
                G.log("     nospot(A): " + n[:110])
    t = R.read_log()
    errs = sorted(set(l[-140:] for l in t.splitlines() if "Script Error" in l or "not properly loaded" in l))
    G.log("script errors:", len(errs), errs[:5])
except Exception as e:
    import traceback
    G.log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    try:
        if rundir:
            S.end_session(rundir, notes or {})
    except Exception as e:
        G.log("end_session", repr(e))
    G.restore_ship()
