"""Harness runs for the double-barrel shotgun on OUR private test copy: G:\\mohaa-hudfeed4, slot owner "hudfeed4",
net_port 12761, DISPLAY2 through harness_window only, engine screenshots only.

The ironsights lane's run_ironsights.py is used as a LIBRARY and repointed (as heavy/tools/run_h.py does): its
seed_home / launch / join / step / give and its teardown are unchanged. Binaries: the integ-1.10.22 set already in the
copy (openmohaa_integ.exe, cgames/cgame_integ.dll, games/game_integ.dll, renderers/gl2_integ.dll).

    python tools/run_dbs.py <session> --overlay <abs pk3> --parts look[,fire,reload,...] [--map m3l2] [--w 1280 --h 720]
Frames land in G:/mohaa-hudfeed4/runs/<session>/ (+ qconsole.log, notes.json).
"""
import os, sys, re, time, json, shutil, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
IS = os.path.join(HERE, '..', '..', 'ironsights_2026-09-28', 'tools')
sys.path.insert(0, IS)
import run_ironsights as R          # noqa: E402

CLIENT = r"G:\mohaa-hudfeed4"
R.OWNER = "hudfeed4"
R.CLIENT = CLIENT
R.EXE = os.path.join(CLIENT, "openmohaa_integ.exe")
R.HOME = os.path.join(CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(CLIENT, "pristine")
R.RUNS = "G:/mohaa-hudfeed4/runs"
R.PORT = 12761
TIK = "models/weapons/coop_dbshotgun.tik"
RELEASE = ["-button13", "-movedown", "-leanleft", "-leanright", "-attackprimary", "wait 250"]


def shot(name):
    """ONE engine screenshot in its own step"""
    R.step(["screenshotJPEG %s" % name, "wait 30", "echo ^~^~^ DBSSHOT %s" % name, "wait 30"], timeout=60)


def frames(tag, n, i, every=1):
    out = []
    for k in range(n):
        out += ["screenshotJPEG %s__%04d" % (tag, i[0]), "wait 1", "wait 1"] + ["wait 1", "wait 1"] * (every - 1)
        i[0] += 1
    return out


def cam(yaw, dist, up=4, lookz=50):
    """the overlay's script camera: `dist` u from player 1 at `yaw` deg from the player's facing (+ = to the left)"""
    CAMSEQ[0] += 1
    return ["set coop_dbsCamYaw %g" % yaw, "set coop_dbsCamDist %g" % dist, "set coop_dbsCamUp %g" % up,
            "set coop_dbsCamLookZ %g" % lookz, "set coop_dbsCam %d" % CAMSEQ[0], "wait 900"]


CAMSEQ = [0]
CAMOFF = ["set coop_dbsCam 0", "wait 700"]


def part_look(a, pre="dbs_look", tik=None):
    """the look test: hip, aimed, third person (script camera: right side, front right, left side; hip and aim),
    the item on the ground"""
    R.step(RELEASE + R.give(tik or a.tik) + ["wait 4500"], timeout=90)
    R.step(["set cg_fov 90", "set cg_drawviewmodel 2", "wait 600"]); shot(pre + "_hip")
    R.step(["+button13", "wait 1900"]); shot(pre + "_ads")
    R.step(["-button13", "wait 700"])
    if tik:
        return
    for nm, yaw, dist, up in (("right", -90, 62, 2), ("frontright", -35, 58, 6), ("left", 90, 62, 2)):
        R.step(cam(yaw, dist, up)); shot("%s_third_%s" % (pre, nm))
    R.step(CAMOFF + ["+button13", "wait 1500"] + cam(-90, 62, 2)); shot(pre + "_third_right_aim")
    R.step(CAMOFF + ["-button13", "wait 600"])
    # the item on the ground: two, at right angles, looked at from above; own gun hidden
    R.step(R.give("none", 40.0) + ["wait 600", "set cg_drawviewmodel 0", "set coop_dbsDropTik %s" % a.tik,
                                  "set coop_dbsDropDist 56", "set coop_dbsDropYaw 90", "set coop_dbsDrop 1", "wait 400",
                                  "set coop_dbsDropDist 80", "set coop_dbsDropYaw 20", "set coop_dbsDrop 2", "wait 1500"])
    shot(pre + "_ground")
    R.step(["set cg_drawviewmodel 2"] + R.give("none", 0.0) + ["wait 600"])


def part_var(a):
    """hip + aim of every --vars tik (scale / placement variants built into the overlay only)"""
    for v in a.vars:
        part_look(a, pre="var_" + os.path.basename(v)[:-4], tik=v)


def part_pump(a):
    """the retail pump gun in the same views, for scale and brightness side by side"""
    R.step(RELEASE + R.give("models/weapons/shotgun.tik") + ["wait 4500"], timeout=90)
    R.step(["set cg_drawviewmodel 2", "wait 300"]); shot("ref_pump_hip")
    R.step(["+button13", "wait 1900"]); shot("ref_pump_ads")
    R.step(["-button13", "wait 700"] + cam(-90, 62, 2)); shot("ref_pump_third_right")
    R.step(CAMOFF)


def part_action(a):
    """the gun at work, hip: raise, two shots, the reload of the emptied gun (both cases out, two shells), one shot and
    a reload with one shell left; then aimed: the aim, one shot. One screenshot per captured game frame."""
    i = [0]
    R.step(RELEASE + R.give("models/weapons/shotgun.tik") + ["wait 4500"], timeout=90)
    L = ["set cg_fov 90", "set cg_drawviewmodel 2"] + R.give(a.tik) + ["wait 300"] + frames("act_raise", 14, i, 8)
    R.step(L + ["wait 2500"], timeout=120)
    i = [0]
    L = ["+attackprimary", "wait 1", "wait 1", "-attackprimary"] + frames("act_fire1", 10, i, 1)
    L += ["wait 250", "+attackprimary", "wait 1", "wait 1", "-attackprimary"] + frames("act_fire2", 6, i, 1)
    i = [0]
    L += ["wait 900", "reload"] + frames("act_reload2", 58, i, 3) + ["wait 2500"]
    R.step(L, timeout=240)
    i = [0]
    L = ["+attackprimary", "wait 1", "wait 1", "-attackprimary", "wait 900", "reload"] + frames("act_reload1", 44, i, 3) + ["wait 2500"]
    R.step(L, timeout=240)
    R.step(["+button13", "wait 1900"]); shot("act_aim")
    i = [0]
    R.step(["+attackprimary", "wait 1", "wait 1", "-attackprimary"] + frames("act_aimfire", 8, i, 1) + ["wait 900", "-button13", "wait 600"], timeout=120)


PARTS = {'look': part_look, 'pump': part_pump, 'var': part_var, 'action': part_action}


def run(a):
    rundir = os.path.join(R.RUNS, a.session)
    if os.path.isdir(rundir):
        shutil.rmtree(rundir)
    os.makedirs(rundir)
    notes = {"session": a.session, "overlay": a.overlay, "map": R.MAP, "parts": a.parts}
    R.seed_home(a.cgame, a.overlay)
    shutil.copyfile(os.path.join(CLIENT, "games", a.game + ".dll"), os.path.join(CLIENT, "game.dll"))
    shutil.copyfile(os.path.join(CLIENT, "renderers", a.gl2 + ".dll"), os.path.join(CLIENT, "renderer_opengl2.dll"))
    try:
        R.launch(a.w, a.h, extra=a.set)
        m = R.wait_log(r"Could not load[^\r\n]*|Detected Coop for", 600)
        if not m or m.group(0).startswith("Could not load"):
            raise RuntimeError("map never became ready: %r" % (m.group(0) if m else None))
        time.sleep(8)
        notes["joined"] = R.join()
        time.sleep(22)
        spawned = False
        for k in range(4):
            t_click = len(R.read_log())
            R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
            if R.wait_log(r"\^~\^~\^ KITGIVE", 15, t_click):
                spawned = True
                break
        notes["spawned"] = spawned
        if not spawned:
            raise RuntimeError("player never spawned")
        time.sleep(8)
        R.step(["dog 1", "wait 200", "notarget 1", "wait 200"], timeout=30)
        for p in a.parts:
            R.log("[%s] part %s" % (a.session, p))
            PARTS[p](a)
        lg = R.read_log()
        notes["script_errors_total"] = len(re.findall(r"Script Error", lg))
    finally:
        proc = R.CL["proc"]
        if proc is not None and proc.poll() is None:
            try:
                with open(os.path.join(R.MAINTT, "isstep.cfg"), "w", newline="\n") as f:
                    f.write("quit\n")
                R.CL["c"].post_key(0x7B)
                proc.wait(40)
            except Exception:
                pass
        c = R.CL["c"]
        if c is not None:
            c.close()
            wrep = c.report()
            notes["window"] = {"clean": wrep["clean"], "violations": wrep["violations"]}
        R.CL["c"] = R.CL["proc"] = None
        n = 0
        if os.path.isdir(R.SHOTS):
            for fn in sorted(os.listdir(R.SHOTS)):
                shutil.move(os.path.join(R.SHOTS, fn), os.path.join(rundir, fn)); n += 1
        notes["shots"] = n
        if os.path.exists(R.LOG):
            shutil.copyfile(R.LOG, os.path.join(rundir, "qconsole.log"))
        json.dump(notes, open(os.path.join(rundir, "notes.json"), "w"), indent=1)
        try:
            R.hg.release_slot(R.OWNER)
        except Exception as e:
            R.log("release_slot:", e)
        R.log("[%s] done: %d shots, notes %s" % (a.session, n, {k: notes.get(k) for k in ("joined", "spawned", "script_errors_total", "window")}))
    return rundir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--overlay", required=True)
    ap.add_argument("--parts", default="look")
    ap.add_argument("--cgame", default="cgame_integ")
    ap.add_argument("--game", default="game_integ")
    ap.add_argument("--gl2", default="gl2_integ")
    ap.add_argument("--map", default="m3l2")
    ap.add_argument("--spot", default=None)
    ap.add_argument("--tik", default=TIK)
    ap.add_argument("--vars", default="", help="comma list of variant tiks for the `var` part")
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720)
    ap.add_argument("--set", action="append", default=[], help='extra boot line, e.g. --set "set cg_adsSway 1"')
    a = ap.parse_args()
    a.parts = a.parts.split(",")
    a.vars = [v for v in a.vars.split(",") if v]
    assert R.CLIENT.lower().endswith("hudfeed4") and R.PORT == 12761
    assert a.map not in ("m3l1a", "m3l1b", "e3l1", "e3l2", "obj_team3")
    R.MAP = a.map
    if a.spot:
        R.SPOT = tuple(float(x) for x in a.spot.split(","))
    run(a)


if __name__ == "__main__":
    main()
