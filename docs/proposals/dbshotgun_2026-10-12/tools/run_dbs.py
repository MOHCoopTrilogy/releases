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
sys.path.insert(0, HERE)
import dbslib as _L      # noqa: E402
R.RUNS = _L.RUNS
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


def part_third(a):
    """THIRD PERSON through the script camera (front right, far enough to hold the whole upper body and the gun): a
    shot standing, the second shot and the reload of the emptied gun, a shot crouched; then the pump gun's standing
    shot for comparison. Every capture starts from a fresh `give` (it re-faces the player) and its own camera.
    (run tp1: one camera at 52 u for all of it - the gun was out of the frame, the pump gun's player not in it at all)"""
    FIRE = ["+attackprimary", "wait 1", "wait 1", "-attackprimary"]
    CAM = cam(-62, 92, 10, 50)
    R.step(RELEASE + R.give(a.tik) + ["wait 4500"] + CAM, timeout=90)
    i = [0]
    R.step(FIRE + frames("tp_fire", 34, i, 2) + ["wait 600"], timeout=120)
    i = [0]
    R.step(FIRE + frames("tp_reload", 76, i, 3) + ["wait 1500"] + CAMOFF, timeout=240)
    R.step(RELEASE + R.give(a.tik) + ["wait 4500", "set coop_proneHold 999", "+movedown", "wait 1100"] + cam(-62, 92, 10, 36), timeout=90)
    i = [0]
    R.step(FIRE + frames("tp_cfire", 30, i, 2) + ["wait 600", "-movedown", "wait 900"] + CAMOFF, timeout=120)
    R.step(RELEASE + R.give("models/weapons/shotgun.tik") + ["wait 4500"] + cam(-62, 92, 10, 50), timeout=90)
    i = [0]
    R.step(FIRE + frames("tp_pumpfire", 34, i, 2) + ["wait 600"] + CAMOFF, timeout=120)


def part_misc(a):
    """first person, hip: the second barrel right after the first, raise, lower (holster), sprint"""
    FIRE = ["+attackprimary", "wait 1", "wait 1", "-attackprimary"]
    R.step(RELEASE + R.give(a.tik) + ["wait 4500", "set cg_fov 90", "set cg_drawviewmodel 2", "wait 300"], timeout=90)
    i = [0]
    R.step(FIRE + frames("ms_fire", 8, i, 1) + ["wait 4"] + FIRE + frames("ms_fire", 22, i, 1) + ["wait 5000"], timeout=120)
    i = [0]
    R.step(RELEASE + R.give("models/weapons/shotgun.tik") + ["wait 4500"] + R.give(a.tik) + frames("ms_raise", 24, i, 3) + ["wait 2500"], timeout=180)
    i = [0]
    R.step(["holster"] + frames("ms_lower", 20, i, 3) + ["wait 1500"], timeout=180)
    R.step(RELEASE + R.give(a.tik) + ["wait 4500"], timeout=90)
    i = [0]
    R.step(["+forward", "+speed"] + frames("ms_sprint", 26, i, 3) + ["-speed", "-forward"] + frames("ms_sprint", 12, i, 3) + ["wait 1200"], timeout=180)


def _respawn(tag):
    """die, click to respawn, wait for the spawn kit; -> the log lines of interest since the kill"""
    t0 = len(R.read_log())
    R.step(["kill", "wait 3500"], timeout=60)
    ok = False
    for k in range(5):
        t = len(R.read_log())
        R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
        if R.wait_log(r"\^~\^~\^ KITGIVE", 15, t):
            ok = True
            break
    time.sleep(5)
    lg = R.read_log()[t0:]
    hits = [l.strip()[-150:] for l in lg.splitlines() if re.search(r"KITGIVE|DBSPICK|coop_dbshotgun|Script Error|not on list", l) and "echo" not in l]
    R.log("[wire] %s: respawned=%s  %s" % (tag, ok, hits[-6:]))
    return ok, hits


def part_wire(a):
    """the WIRING (overlay built with --wire): the trench gun in slot 1, the page switch ON by the token its button
    sends, spawn with it, die with it (death drop), respawn with the switch OFF and pick the dropped gun up with Use,
    switch ON again and restart the map (the pick must come back by itself). One screenshot per step; log lines in
    notes.json."""
    out = {}
    R.step(RELEASE + ["set cg_fov 90", "set cg_drawviewmodel 2", "exec ui/loadout/w44_s1.cfg", "wait 8000"], timeout=60)
    R.step(["exec ui/loadout/dbs_on.cfg", "wait 8000"], timeout=60)
    out['pick_on'] = [l.strip()[-120:] for l in R.read_log().splitlines() if "DBSPICK" in l and "echo" not in l][-2:]
    out['spawn1'] = _respawn("spawn with the switch on")
    R.step(["wait 1500"]); shot("wire_1_spawned_with_it")
    R.step(R.face(0.0) + ["wait 2500"], timeout=60); shot("wire_2_at_the_spot")
    out['spawn2'] = _respawn("died with it at the spot")                         # the death drop lies at the spot now
    R.step(["exec ui/loadout/dbs_off.cfg", "wait 8000"], timeout=60)
    out['spawn3'] = _respawn("switch off")                                        # kit = the trench gun again
    R.step(["wait 1500"]); shot("wire_3_switch_off_trench_gun")
    R.step(["+back", "wait 450", "-back", "wait 600", "set coop_isPitch 62", "wait 100"], timeout=60)
    R.step(["+lookdown", "wait 900", "-lookdown", "wait 800"], timeout=60); shot("wire_4_death_drop_on_the_ground")
    t = len(R.read_log())
    R.step(["+use", "wait 900", "-use", "wait 2500"], timeout=60); shot("wire_5_after_use")
    R.step(R.face(0.0) + ["wait 1500", "useweaponclass shotgun", "wait 2500"], timeout=60); shot("wire_6_picked_up_in_hand")
    out['use'] = [l.strip()[-150:] for l in R.read_log()[t:].splitlines() if re.search(r"loot|LOOT|pick|coop_dbshotgun|Shotgun", l) and "echo" not in l][-8:]
    # the pick across a map restart: switch on, restart the map the mod's own way, join, spawn
    R.step(["exec ui/loadout/dbs_on.cfg", "wait 8000"], timeout=60)
    t = len(R.read_log())
    R.step(["set ui_dmmap %s" % R.MAP, "ui_startdmmap 2"], timeout=60)
    m = R.wait_log(r"Could not load[^\r\n]*|Detected Coop for", 600, t)
    out['restart'] = m.group(0) if m else None
    time.sleep(8)
    out['rejoined'] = R.join()
    time.sleep(45)                 # the join replay of the archived picks is staggered over ~20 s
    ok = False
    for k in range(5):
        tc = len(R.read_log())
        R.step(["popmenu 0", "wait 20", "+attackprimary", "wait 60", "-attackprimary", "wait 200"])
        if R.wait_log(r"\^~\^~\^ KITGIVE", 15, tc):
            ok = True
            break
    time.sleep(30)                 # the replay now waits for the spawn, then needs a few seconds
    tq = len(R.read_log())
    R.step(["coop_loDbsA", "wait 300", "coop_loDbsShow", "wait 300"], timeout=30)
    out['cvars_after_restart'] = [l.strip()[-110:] for l in R.read_log()[tq:].splitlines() if "coop_loDbs" in l and "isstep" not in l][-4:]
    out['after_restart'] = (ok, [l.strip()[-150:] for l in R.read_log()[t:].splitlines() if re.search(r"KITGIVE|DBSPICK|DBSRESEND|Script Error", l) and "echo" not in l][-8:])
    R.step(["set cg_fov 90", "set cg_drawviewmodel 2", "wait 1500"]); shot("wire_7_after_map_restart")
    tq = len(R.read_log())
    R.step(["vstr coop_loDbsA", "wait 9000"], timeout=60)                       # the replay by hand, to tell the cvar from the timing
    out['manual_replay'] = [l.strip()[-60:] for l in R.read_log()[tq:].splitlines() if "DBSPICK" in l and "echo" not in l][-2:]
    json.dump(out, open(os.path.join(R.RUNS, a.session, "wire.json"), "w"), indent=1, default=str)
    R.log("[wire] %s" % json.dumps(out, default=str)[:1500])


def part_loot(a):
    """USE-TO-LOOT: another gun in hand, the double barrel lying 46 u ahead (the overlay's coop_dbsDrop), look at it
    (the prompt with its picture), press Use, bring it up"""
    R.step(RELEASE + R.give("models/weapons/colt45.tik") + ["wait 4500", "set cg_fov 90", "set cg_drawviewmodel 2",
                                                            "set coop_dbsDropTik %s" % a.tik, "set coop_dbsDropDist 46", "set coop_dbsDropYaw 80",
                                                            "set coop_dbsDrop 71", "wait 2500"], timeout=90)
    R.step(R.give("none", 58.0) + ["wait 2000"], timeout=60); shot("loot_1_item_and_prompt")
    t = len(R.read_log())
    R.step(["+use", "wait 900", "-use", "wait 2500"], timeout=60); shot("loot_2_after_use")
    R.step(R.give("none", 0.0) + ["wait 1500", "useweaponclass shotgun", "wait 3000"], timeout=60); shot("loot_3_in_hand")
    hits = [l.strip()[-140:] for l in R.read_log()[t:].splitlines() if re.search(r"LOOT|loot|Shotgun|coop_dbshotgun|pick", l) and "echo" not in l and "screenshots" not in l][-8:]
    R.log("[loot] %s" % hits)


def part_menu(a):
    """the armory page of the trench gun with the switch (overlay built with --wire): off, then on"""
    R.step(RELEASE + ["exec ui/loadout/dbs_off.cfg", "wait 6000", "pushmenu coop_loadout", "wait 2500", "exec ui/loadout/p44.cfg", "wait 1500"], timeout=60)
    shot("menu_1_trench_gun_page_switch_off")
    R.step(["exec ui/loadout/dbs_on.cfg", "wait 6000"], timeout=60); shot("menu_2_trench_gun_page_switch_on")
    R.step(["exec ui/loadout/p01.cfg", "wait 1500"], timeout=60); shot("menu_3_other_page_no_switch")
    R.step(["popmenu 0", "wait 800"], timeout=60)


PARTS = {'loot': part_loot, 'menu': part_menu, 'wire': part_wire, 'look': part_look, 'pump': part_pump, 'var': part_var, 'action': part_action, 'third': part_third, 'misc': part_misc}


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
