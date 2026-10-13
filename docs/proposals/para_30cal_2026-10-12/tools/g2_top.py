"""g2_top.py - bug-3562: a top-down still of the sandbag model with a bipod at its origin (mesh offset check)."""
import os, re, time
import g1lib as G
R, S = G.R, G.S
ov = G.overlay("ov_g2t.pk3", "g2_top.scr")
cg = G.install("new", "integ")
R.MAP = "m3l2"
rundir = notes = None
try:
    extra = ["set coop_st_xp 1", "ui_hud 0", "set developer 1", "set com_maxfpsUnfocused 60", "set com_maxfps 60",
             "set g_ai 0", "set cg_drawviewmodel 0"]
    rundir, notes = S.boot_session("g2_top", cg, 1280, 720, extra, ov)
    p0 = len(R.read_log())
    R.step(["set g2_cmd go", "wait 1500"], timeout=30)
    time.sleep(1.5)
    for l in re.findall(r"G2 TOP[^\r\n]*", R.read_log()[p0:]):
        G.log(l)
    R.step(["screenshotJPEG top_bag", "wait 150"], timeout=30)
except Exception as e:
    import traceback
    G.log("FAILED", repr(e), traceback.format_exc()[-600:])
finally:
    try:
        if rundir:
            S.end_session(rundir, notes or {})
    except Exception as e:
        G.log("end_session", repr(e))
    G.restore_ship()
