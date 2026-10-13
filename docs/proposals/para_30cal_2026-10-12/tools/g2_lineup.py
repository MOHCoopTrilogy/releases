"""g2_lineup.py - bug-3562: candidate support models side by side on m3l2 (lit, level), bounds printed, two stills."""
import os, re, sys, time
import g1lib as G
R, S = G.R, G.S
ov = G.overlay("ov_g2.pk3", "g2_lineup.scr")
cg = G.install("new", "integ")
R.MAP = "m3l2"
rundir = notes = None


def cmd(what, **kv):
    p0 = len(R.read_log())
    R.step(["set g2_%s %s" % (k, v) for k, v in kv.items()] + ["set g2_cmd %s" % what], timeout=30)
    R.wait_log(r"\^~\^~\^ G2 did %s" % what, 30, p0)
    return p0


try:
    extra = ["set coop_st_xp 1", "ui_hud 0", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
             "set cg_drawviewmodel 0"]
    rundir, notes = S.boot_session("g2_lineup", cg, 1280, 720, extra, ov)
    cmd("tp", x=-3608, y=2303, z=84, yaw=225, pitch=12)
    time.sleep(1)
    for row in (0, 1):
        p0 = cmd("line", row=row)
        time.sleep(1.2)
        for l in re.findall(r"\^~\^~\^ G2 MODEL[^\r\n]*", R.read_log()[p0:]):
            G.log(l[9:])
        R.step(["screenshot lineup_%d" % row, "wait 80"], timeout=30)
        time.sleep(0.5)
        cmd("clear")
        time.sleep(0.5)
    t = R.read_log()
    G.log("script errors:", len([l for l in t.splitlines() if "Script Error" in l]))
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
