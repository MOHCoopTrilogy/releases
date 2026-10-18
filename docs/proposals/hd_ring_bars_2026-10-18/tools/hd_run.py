"""hd_run.py - ONE in-engine run for the HD hold-progress ring/bars, on the private harness copy G:\\mohaa-hudfeed4
(slot owner "hudfeed4", net_port 12761, DISPLAY2 through harness_window only, engine `screenshot` only = lossless TGA).

    python hd_run.py <session> --look old|hd --map m3l2 [--w 1920 --h 1080] [--spot x,y,z,yaw]

old = the LIVE binaries (G:\\mohaa-gl2 exe/cgame/game/renderer, byte copies) + the live code pak: the shipped look.
hd  = hdring-engine exe + cgame (G:\\mohaa-hudfeed4\\cgames\\cgame_hdring.dll, openmohaa_hdring.exe) + the fixes pak's
      coop_hd_ramp.tga in the test overlay. game.dll / renderer are the live ones in both.
Scenes (tools/over/coop_mod/hd_probe.scr draws the real scripts' huddraw elements; the ring uses the real coop_setbleed):
ringa ringb heal revive place objective, then the weapon pickup hold bar (cgame, coop_lootT/coop_lootH).
Frames land in G:/mohaa-hudfeed4/runs/<session>/.
"""
import os, sys, re, time, json, shutil, argparse, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\dbshotgun_2026-10-12\tools")
import run_dbs as D                 # noqa: E402  (repoints run_ironsights as R at G:\mohaa-hudfeed4)
R = D.R
CANDIDATES = [("hudfeed4", 12761), ("hudfeed5", 12781), ("hudfeed2", 12721), ("hudfeed3", 12741)]   # same-layout private copies; first free slot wins
CLIENT = r"G:\mohaa-hudfeed3"


def use_copy(owner, port):
    global CLIENT
    CLIENT = r"G:\mohaa-" + owner
    R.OWNER = owner
    R.CLIENT = CLIENT
    R.HOME = os.path.join(CLIENT, "home")
    R.MAINTT = os.path.join(R.HOME, "maintt")
    R.LOG = os.path.join(R.MAINTT, "qconsole.log")
    R.SHOTS = os.path.join(R.MAINTT, "screenshots")
    R.PRISTINE = os.path.join(CLIENT, "pristine")
    R.RUNS = os.path.join(CLIENT, "runs")
    R.PORT = port


use_copy(*CANDIDATES[-1])
GOG = R.GOG
LIVE = r"G:\mohaa-gl2"
LIVECODE = os.path.join(GOG, "maintt", "zzzzzz_co-op_hzm_mod_code.pk3")
RAMP = r"C:\mohaa-coop-dev\docs\tools\assets\fixes\textures\hud\coop_hd_ramp.tga"
ENGINE_EXE = r"C:\mohaa-coop-dev\openmohaa-hzm-hdring\.cmake\Release\openmohaa.exe"
ENGINE_CG = r"C:\mohaa-coop-dev\openmohaa-hzm-hdring\.cmake\code\client\cgame\Release\cgame.dll"
OVER = os.path.join(HERE, "over")
OLD_CG = r"C:\mohaa-coop-dev\openmohaa-hzm-hdring-old\.cmake\code\client\cgame\Release\cgame.dll"
SC = os.path.join(R.SCRATCH, "hdring")
SCENES = ["heal", "revive", "place", "objective"]


def build_overlay(look):
    os.makedirs(SC, exist_ok=True)
    out = os.path.join(SC, "zzzzzzzzzzzzzz_hdtest_%s.pk3" % look)
    live = zipfile.ZipFile(LIVECODE)
    dp = live.read("coop_mod/devprobe.scr").decode("latin-1")
    k = dp.index("main:{")
    k = dp.index("\n", dp.index("//====", k)) + 1
    dp = dp[:k] + '\tif( getcvar( "coop_hdTest" ) == "1" ){ thread coop_mod/hd_probe.scr::run }\t//TEST OVERLAY ONLY\n' + dp[k:]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("coop_mod/devprobe.scr", dp.encode("latin-1"))
        z.write(os.path.join(OVER, "coop_mod", "hd_probe.scr"), "coop_mod/hd_probe.scr")
        if look == "hd":
            z.write(RAMP, "textures/hud/coop_hd_ramp.tga")
            # TEST ONLY: the live server rules zero the bots; nothing else changed
    return out


def stage_binaries(look):
    os.makedirs(os.path.join(CLIENT, "cgames"), exist_ok=True)
    if look == "old":
        R.EXE = os.path.join(CLIENT, "openmohaa_hdlive.exe")
        shutil.copyfile(os.path.join(LIVE, "openmohaa.exe"), R.EXE)
        shutil.copyfile(OLD_CG, os.path.join(CLIENT, "cgames", "cgame_hdlive.dll"))   # the live release cgame source + only the coop_hdRingTest instrument
        cg = "cgame_hdlive"
    else:
        R.EXE = os.path.join(CLIENT, "openmohaa_hdring.exe")
        shutil.copyfile(ENGINE_EXE, R.EXE)
        shutil.copyfile(ENGINE_CG, os.path.join(CLIENT, "cgames", "cgame_hdring.dll"))
        cg = "cgame_hdring"
    for f in ("game.dll", "renderer_opengl2.dll"):
        shutil.copyfile(os.path.join(LIVE, f), os.path.join(CLIENT, f))
    return cg


def shot(name):
    R.step(["screenshot %s" % name, "wait 40", "echo ^~^~^ HDSHOT %s" % name, "wait 20"], timeout=60)


def wait_free(minutes=40):
    """harness_turn gives us the turn; take the first private copy whose harness_guard slot is free"""
    t_end = time.time() + minutes * 60
    while time.time() < t_end:
        for owner, port in CANDIDATES:
            use_copy(owner, port)
            R.EXE = os.path.join(CLIENT, "openmohaa_hdlive.exe" if CUR_LOOK[0] == "old" else "openmohaa_hdring.exe")
            try:
                R.hg.acquire_slot(owner, R.EXE, R.HOME, [port], 40)
                os.makedirs(R.RUNS, exist_ok=True)
                return
            except Exception as e:   # SlotBusy: try the next copy
                R.log("slot", owner, "busy:", str(e)[:60])
        time.sleep(5)
    raise RuntimeError("no free harness copy")


CUR_LOOK = [""]


def run(a):
    CUR_LOOK[0] = a.look
    wait_free()
    rundir = os.path.join(R.RUNS, a.session)
    if os.path.isdir(rundir):
        shutil.rmtree(rundir)
    os.makedirs(rundir)
    R.MAP = a.map
    if a.spot:
        R.SPOT = tuple(float(v) for v in a.spot.split(","))
    notes = {"session": a.session, "look": a.look, "map": a.map, "w": a.w, "h": a.h}
    cg = stage_binaries(a.look)
    ov = build_overlay(a.look)
    R.seed_home(cg, ov)
    extra = ["set coop_hdTest 1", "seta coop_hardcore 0", "set coop_hdOld %d" % (1 if a.look == "old" else 0), "set ui_gmbox 1", "ui_checkrestart", "ui_hud 1", "set ui_crosshair 1", "set cg_hud 1", "set cg_huddraw_force 1", "set coop_dbno 1",
             "set coop_feed 1", "set r_ppFXAA 0", "set cg_fov 90"] + list(a.set)
    try:
        R.launch(a.w, a.h, extra=extra)
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
        R.step(["dog 1", "wait 200", "notarget 1", "wait 200"] + ([] if a.nogive else R.give("none", a.pitch)) + ["wait 800"], timeout=30)
        R.step(["set coop_hudFade 0", "ui_hud 1", "set cg_hud 1", "wait 300", "echo ^~^~^ HDCV ui_hud", "ui_hud", "echo ^~^~^ HDCV cg_hud", "cg_hud",
                "echo ^~^~^ HDCV force", "cg_huddraw_force", "echo ^~^~^ HDCV fade", "coop_hudFade", "wait 200"], timeout=30)
        R.step(["set coop_hdGo 1", "wait 400"], timeout=30)
        if not R.wait_log(r"\^~\^~\^ HDP host ready", 60):
            raise RuntimeError("probe never armed")
        shot("%s_base" % a.look)
        # the own bleed ring at a chosen remaining fraction (no real DBNO: coop_hdRingTest, a cgame test instrument in both builds)
        R.step(["set coop_hdRingTest 0.70", "wait 900"], timeout=30)
        shot("%s_ringa" % a.look)
        R.step(["set coop_hdRingTest 0.22", "wait 700"], timeout=30)
        shot("%s_ringb" % a.look)
        if a.look == "hd":   # GIF frames: the drain 0.95 -> 0.06, 4 per second
            R.step(sum([["set coop_hdRingTest %.3f" % (0.95 - 0.89 * k / 31.0), "screenshot rf%03d" % k, "wait 250"] for k in range(32)], []), timeout=240)
        R.step(["set coop_hdRingTest 0", "wait 300"], timeout=30)
        for sc in SCENES:
            R.step(["set coop_hdScene %s" % sc, "wait 700"], timeout=30)
            R.wait_log(r"\^~\^~\^ HDP scene %s" % sc, 20)
            R.step(["wait 1800"], timeout=30)
            shot("%s_%s" % (a.look, sc))
        t0 = len(R.read_log())
        R.step(["set coop_hdScene healanim", "wait 20"], timeout=30)
        R.wait_log(r"\^~\^~\^ HDP animstart", 20, t0)
        R.step(sum([["screenshot hf%03d" % k, "wait 100"] for k in range(40)], []), timeout=240)   # ~4 s of the fill at 60 fps
        R.step(["set coop_hdScene off", "wait 600"], timeout=30)
        R.step(["set coop_lootT 500000", "set coop_lootH 4000", "wait 2300"], timeout=30)
        shot("%s_pickup" % a.look)
        R.step(["set coop_lootH 0", "set coop_lootT 0", "wait 600"], timeout=30)
        notes["script_errors"] = len(re.findall(r"Script Error", R.read_log()))
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
        R.log("[%s] done: %d shots %s" % (a.session, n, {k: notes.get(k) for k in ("joined", "spawned", "script_errors", "window")}))
    out = os.path.join(r"G:\mohaa-hdring-out", a.session)       # one fixed place whichever private copy ran it
    os.makedirs(r"G:\mohaa-hdring-out", exist_ok=True)
    if os.path.isdir(out):
        shutil.move(out, out + "_prev_" + time.strftime("%H%M%S"))
    shutil.move(rundir, out)
    R.log("frames in", out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--look", choices=["old", "hd"], required=True)
    ap.add_argument("--map", default="m3l2")
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--spot", default="")
    ap.add_argument("--nogive", action="store_true")
    ap.add_argument("--pitch", type=float, default=0.0)
    ap.add_argument("--set", action="append", default=[])
    run(ap.parse_args())


if __name__ == "__main__":
    main()
