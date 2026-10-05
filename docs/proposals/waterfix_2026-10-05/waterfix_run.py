"""waterfix_run.py - ONE batched slot run: before/after stills, a pan for the GIF and GPU ms, water + wet fixes.

    python waterfix_run.py wait-and-run        wait for SCRATCHPAD\\test_slot.txt == "waterfix", run, write "free"
    python waterfix_run.py run [scene ...]     run now (only when the slot is ours)

Reuses the water/wet harness (docs/proposals/water_wetness_2026-09-27/ingame/ww_ingame.py): the private client
G:\\mohaa-wwtest (registered in harness_guard.py, owner "waterwet"), its overlay pk3 camera (coop_ww_cam), the coop
weather held dry (forced r_hzmWetNow / r_hzmPuddleNow), DISPLAY2 via harness_window, engine `screenshot` only.

Binaries: the LIVE v1.10.13 set copied from G:\\mohaa-gl2 (read only): exe d23dd662, cgame d563b759, game 6f68255a,
gl1 f6e4ce71. BEFORE = the live gl2 (sha256 731f1ad5, the flip-gate DLL); AFTER = the waterfix gl2 from
SCRATCHPAD\\waterfix\\bld. The client folder's own v1103d binaries are parked in G:\\mohaa-wwtest\\bin_v1103d and put back.
Per scene: one launch per DLL, identical camera; MSAA 8x (r_msaa 8); one extra AFTER launch of the canal at r_msaa 0.
"""
import hashlib, json, os, re, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\water_wetness_2026-09-27\ingame")
import ww_ingame as ww  # noqa: E402

hg, hw = ww.hg, ww.hw
SCRATCH = ww.SCRATCH
SLOTNAME = "waterfix"
LIVE = r"G:\mohaa-gl2"
NEWDLL = os.path.join(SCRATCH, r"waterfix\bld\code\renderercommon\renderergl2\Release\renderer_opengl2.dll")
PARK = os.path.join(ww.CLIENT, "bin_v1103d")
RUNS = os.path.join(ww.CLIENT, "runs_waterfix")
NEW_ONLY = os.environ.get("WATERFIX_NEW_ONLY") == "1"   # run 2: the AFTER DLL again (the BEFORE captures stand)
BINS = ["cgame.dll", "game.dll", "renderer_opengl1.dll", "renderer_opengl2.dll", "openmohaa_wwtest.exe"]

SCENES = {
    # the look-dev / v1103 poses, kept so the old evidence lines up
    "wet_day": dict(map="m5l1b", kind="coop", eye=(2140, -764, 640), tgt=(3337, -680, 470), type="wet"),
    "wet_night": dict(map="m4l2", kind="coop", eye=(-5056, 3520, 80), tgt=(-4116, 3862, -25), type="wet"),
    "river": dict(map="m5l2b", kind="coop", eye=(3488, -6456, -77.5), tgt=(3822, -7437, -232), type="both"),
    # m3l2 (the map the user played on 2026-10-05): a stone-walled canal (water -136, ground 0), fence posts, fog
    "canal": dict(map="m3l2", kind="coop", eye=(-3680, 2064, 82), tgt=(-4770, 1034, -160), type="both", pan=True),
}


def log(*a):
    ww.log(*a)


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def set_bins(which):
    os.makedirs(PARK, exist_ok=True)
    for b in BINS:
        if not os.path.exists(os.path.join(PARK, b)):
            shutil.copy2(os.path.join(ww.CLIENT, b), os.path.join(PARK, b))
    if which == "park":
        for b in BINS:
            shutil.copy2(os.path.join(PARK, b), os.path.join(ww.CLIENT, b))
        return
    src = {"cgame.dll": os.path.join(LIVE, "cgame.dll"), "game.dll": os.path.join(LIVE, "game.dll"),
           "renderer_opengl1.dll": os.path.join(LIVE, "renderer_opengl1.dll"),
           "openmohaa_wwtest.exe": os.path.join(LIVE, "openmohaa.exe"),
           "renderer_opengl2.dll": os.path.join(LIVE, "renderer_opengl2.dll") if which == "old" else NEWDLL}
    for b, s in src.items():
        shutil.copy2(s, os.path.join(ww.CLIENT, b))


def launch(sc, msaa):
    on = ["set rconPassword %s" % ww.RCONPW, "set sv_maxbots 0", "set sv_numbots 0", "set cg_drawviewmodel 0",
          "set r_hzmWater 0", "set r_hzmWet 0", "set coop_wwTestPoll 1", "set coop_wwTestPin 0",
          "set sv_fps 100", "set coop_dev 1", "set coop_weatherPin 0", "set r_gfxProbe 1", "set com_maxfps 60",
          "set cg_drawhud 0", "set cg_hud 0", "set ui_hud 0"]
    sets = [("com_target_game", "2"), ("fs_basepath", ww.GOG), ("fs_homepath", ww.HOME), ("cl_renderer", "opengl2"),
            ("r_msaa", str(msaa)), ("r_uselod", "0"), ("r_lodscale", "28"),
            ("r_mode", "-1"), ("r_customwidth", str(ww.W)), ("r_customheight", str(ww.H)), ("r_fullscreen", "0"),
            ("developer", "1"), ("r_picmip", "0"), ("com_maxfps", "60"),
            ("logfile", "2"), ("net_port", str(ww.PORT))]
    args = [ww.EXE]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+set", "g_gametype", "2", "+exec", "ww_on.cfg", "+set", "ui_dmmap", sc["map"],
             "+exec", "coop_mod/start_server.cfg"]
    args, late = hw.apply_policy(args, width=ww.W, height=ww.H)
    on += late
    with open(os.path.join(ww.MAINTT, "ww_on.cfg"), "w", newline="\n") as f:
        f.write("\n".join(on) + "\n")
    assert sum(1 for a in args if a.startswith("+")) <= 31
    c = hw.launch_background(args[0], args[1:], ww.CLIENT, policy=False, log=log)
    ww.CLIENT_H["c"], ww.CLIENT_H["proc"] = c, c.proc
    hg.set_slot_pid(ww.OWNER, c.proc.pid)


def gpu(tag):
    # GPUTIME over ~8 s at a held camera; the probe ring holds 1024 frames (60 fps cap -> ~480 used)
    return ["gfxresettiming", "wait 8000", "echo ^~^~^ WFGPU %s" % tag, "gfxprobe"]


def captures(tag, sc, after):
    o, p, y = ww.path(dict(sc, path="static"), 1)[0]
    L = ww.place(o, p, y) + ["wait 1500"]
    shot = lambda n: "screenshot %s_%s" % (tag, n)
    L += ["set r_hzmWet 0", "set r_hzmWater 0", "set r_hzmWetNow 1", "set r_hzmPuddleNow 0", "wait 2500", shot("D")]
    L += gpu("off")
    if sc["type"] in ("both",):
        L += ["set r_hzmWater 1", "wait 2500", shot("W")]
    L += ["set r_hzmWet 1", "wait 2500", shot("F"), "set r_hzmPuddleNow 1", "wait 1500", shot("P"), "wait 1000", shot("P2")]
    L += gpu("on")
    if after:
        L += ["set r_hzmWetDebug 1", "wait 400", shot("DBG"), "set r_hzmWetDebug 0", "wait 300"]
    ww.step(L, timeout=300)
    if sc.get("pan"):
        # a slow pan across the fence posts and the canal wall over wet ground + water (the GIF), 48 frames
        yaw0, el = ww.angles(sc["eye"], sc["tgt"])
        L = ww.place(o, -el, yaw0 + 14.0) + ["wait 2000"]
        for k in range(48):
            L += ww.place(o, -el, yaw0 + 14.0 - 28.0 * k / 47.0) + ["wait 1", "wait 1", "wait 1", "wait 1",
                                                                   "screenshot %s_pan_%02d" % (tag, k)]
        ww.step(L + ["wait 100"], timeout=300)


def run_one(name, which, msaa=8):
    sc = SCENES[name]
    tag = "%s_%s%s" % (name, which, "" if msaa == 8 else "_msaa%d" % msaa)
    rundir = os.path.join(RUNS, tag)
    os.makedirs(rundir, exist_ok=True)
    set_bins(which)
    notes = {"scene": name, "tag": tag, "map": sc["map"], "eye": sc["eye"], "target": sc["tgt"], "msaa": msaa,
             "renderer_md5": md5(os.path.join(ww.CLIENT, "renderer_opengl2.dll")), "exe_md5": md5(ww.EXE)}
    ww.seed_home()
    os.makedirs(ww.SHOTS, exist_ok=True)
    for fn in os.listdir(ww.SHOTS):
        os.remove(os.path.join(ww.SHOTS, fn))
    try:
        launch(sc, msaa)
        if not ww.wait_log(r"Detected Coop for", 600):
            raise RuntimeError("map never became ready")
        time.sleep(4)
        mw = ww.wait_log(r"\^~\^~\^ WEATHER coop=(\w+)", 60)
        mp = ww.wait_log(r"\^~\^~\^ WWTEST pattern=", 30)
        notes["coop_weather"] = mw.group(1) if mw else None
        if not mw or mw.group(1) != "rain" or not mp:
            raise RuntimeError("coop weather did not start (%r) - not capturing" % notes["coop_weather"])
        time.sleep(8)
        notes["joined"] = ww.join(sc)
        time.sleep(4)
        o, p, y = ww.path(dict(sc, path="static"), 1)[0]
        start = len(ww.read_log())
        ww.step(ww.place(o, p, y) + ["wait 1500", "coord"])
        cam = re.findall(r"\^~\^~\^ WWCAM (\d+)", ww.read_log()[start:])
        m = re.findall(r"location: (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)", ww.read_log()[start:])
        if not cam or not m or max(abs(float(m[-1][i]) - o[i]) for i in range(3)) > 2.0:
            raise RuntimeError("the camera did not land: cam=%s coord=%s vs %s" % (cam, m[-1] if m else None, o))
        captures(tag, sc, which == "new")
        lg = ww.read_log()
        notes["msaa_line"] = re.findall(r"\^~\^~\^ MSAA path=[^\r\n]*", lg)[-1:]
        notes["gpu"] = re.findall(r"\^~\^~\^ (?:WFGPU \w+|GPUTIME[^\r\n]*)", lg)
        notes["markers"] = re.findall(r"\^~\^~\^ (?:HZMWET|HZMWATER|GFXBUILD)[^\r\n]*", lg)
        notes["glsl_errors"] = re.findall(r"[^\r\n]*(?:Could not load|failed to compile|GLSL[^\r\n]*error)[^\r\n]*", lg, re.I)
        notes["script_errors"] = len(re.findall(r"Script Error", lg))
    except ww.Aborted:
        raise
    except Exception as e:
        notes["error"] = repr(e)
        log("[%s] FAILED: %r" % (tag, e))
    finally:
        proc = ww.CLIENT_H["proc"]
        if proc is not None and proc.poll() is None:
            try:
                ww.rcon("quit")
                proc.wait(40)
            except Exception:
                pass
            if proc.poll() is None:
                proc.kill()
        c = ww.CLIENT_H["c"]
        if c is not None:
            c.close()
            wrep = c.report()
            notes["window"] = {"clean": wrep["clean"], "violations": wrep["violations"]}
        ww.CLIENT_H["c"] = ww.CLIENT_H["proc"] = None
        shots = []
        if os.path.isdir(ww.SHOTS):
            for fn in sorted(os.listdir(ww.SHOTS)):
                shutil.move(os.path.join(ww.SHOTS, fn), os.path.join(rundir, fn))
                shots.append(fn)
        notes["shots"] = len(shots)
        if os.path.exists(ww.LOG):
            shutil.copyfile(ww.LOG, os.path.join(rundir, "qconsole.log"))
        json.dump(notes, open(os.path.join(rundir, "notes.json"), "w"), indent=1)
        log("[%s] done: %d shots %s" % (tag, len(shots), notes.get("error", "")))
    return notes


def run(names):
    if hg.user_game_running():
        raise ww.Aborted("the user's game is running - not starting")
    hg.acquire_slot(ww.OWNER, ww.EXE, ww.HOME, [ww.PORT], minutes=150)
    res = []
    try:
        for n in names:
            for which in (("new",) if NEW_ONLY else ("old", "new")):
                res.append(run_one(n, which))
        if "canal" in names:
            res.append(run_one("canal", "new", msaa=0))
    finally:
        hg.release_slot(ww.OWNER)
        set_bins("park")
        ww.seed_home()
        ov = os.path.join(ww.MAINTT, ww.OVERLAY)
        if os.path.exists(ov):
            os.remove(ov)
    json.dump(res, open(os.path.join(RUNS, "summary%s.json" % ("_run2" if NEW_ONLY else "")), "w"), indent=1)
    return res



# ---------------------------------------------------------------- run 3: 360-degree sweeps at many spots
SWEEP_POSES = json.load(open(os.path.join(HERE, "poses.json")))
SWEEP_POSES.setdefault("m5l1b", []).insert(0, [2140, -764, 640])          # the v1103 wet_day eye
SWEEP_POSES.setdefault("m4l2", []).insert(0, [-5056, 3520, 80])           # the v1103 wet_night eye
SWEEP_POSES.setdefault("m3l2", []).insert(0, [-3680, 2064, 82])           # the canal eye
SWEEP_POSES["m5l2b"] = [[3488, -6456, -77.5]]                              # the river bank (outside teleportMaster)
SWEEP_MAPS = ["m3l2", "m5l1b", "m4l2", "t1l2", "m5l1a", "m5l2b"]


def sweep_run_one(mp, which):
    tag = "sw_%s_%s" % (mp, which)
    rundir = os.path.join(RUNS, tag)
    os.makedirs(rundir, exist_ok=True)
    set_bins(which)
    sc = dict(map=mp, kind="coop", eye=tuple(SWEEP_POSES[mp][0]), tgt=(0, 0, 0))
    notes = {"tag": tag, "map": mp, "renderer_md5": md5(os.path.join(ww.CLIENT, "renderer_opengl2.dll")), "poses": []}
    ww.seed_home()
    os.makedirs(ww.SHOTS, exist_ok=True)
    for fn in os.listdir(ww.SHOTS):
        os.remove(os.path.join(ww.SHOTS, fn))
    try:
        launch(sc, 8)
        if not ww.wait_log(r"Detected Coop for", 600):
            raise RuntimeError("map never became ready")
        time.sleep(4)
        mw = ww.wait_log(r"\^~\^~\^ WEATHER coop=(\w+)", 60)
        ww.wait_log(r"\^~\^~\^ WWTEST pattern=", 30)
        notes["coop_weather"] = mw.group(1) if mw else None
        time.sleep(8)
        notes["joined"] = ww.join(sc)
        time.sleep(4)
        ww.step(["set r_hzmWet 1", "set r_hzmWater 1", "set r_hzmWetNow 1", "set r_hzmPuddleNow 1"])
        for k, eye in enumerate(SWEEP_POSES[mp]):
            o = (eye[0], eye[1], eye[2] - ww.VIEWH)
            start = len(ww.read_log())
            ww.step(ww.place(o, 12.0, 0.0) + ["wait 1500", "coord"])
            m = re.findall(r"location: (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)", ww.read_log()[start:])
            landed = bool(m) and max(abs(float(m[-1][i]) - o[i]) for i in range(3)) <= 2.0
            notes["poses"].append({"k": k, "eye": eye, "landed": landed, "coord": m[-1] if m else None})
            if not landed:
                continue
            L = ["wait 2500"]
            for f in range(60):
                L += ww.place(o, 12.0, 6.0 * f) + ["wait 1", "wait 1", "wait 1", "wait 1",
                                                   "screenshot %s_p%d_%02d" % (tag, k, f)]
            ww.step(L + ["wait 100"], timeout=400)
        notes["glsl_errors"] = re.findall(r"[^\r\n]*(?:Could not load|failed to compile)[^\r\n]*", ww.read_log(), re.I)
    except ww.Aborted:
        raise
    except Exception as e:
        notes["error"] = repr(e)
        log("[%s] FAILED: %r" % (tag, e))
    finally:
        proc = ww.CLIENT_H["proc"]
        if proc is not None and proc.poll() is None:
            try:
                ww.rcon("quit")
                proc.wait(40)
            except Exception:
                pass
            if proc.poll() is None:
                proc.kill()
        c = ww.CLIENT_H["c"]
        if c is not None:
            c.close()
            notes["window"] = c.report()["clean"]
        ww.CLIENT_H["c"] = ww.CLIENT_H["proc"] = None
        n = 0
        if os.path.isdir(ww.SHOTS):
            from PIL import Image
            for fn in sorted(os.listdir(ww.SHOTS)):
                src = os.path.join(ww.SHOTS, fn)
                try:
                    Image.open(src).convert("RGB").save(os.path.join(rundir, os.path.splitext(fn)[0] + ".jpg"), quality=93)
                    os.remove(src)
                except Exception:
                    shutil.move(src, os.path.join(rundir, fn))
                n += 1
        notes["shots"] = n
        if os.path.exists(ww.LOG):
            shutil.copyfile(ww.LOG, os.path.join(rundir, "qconsole.log"))
        json.dump(notes, open(os.path.join(rundir, "notes.json"), "w"), indent=1)
        log("[%s] done: %d shots %s" % (tag, n, notes.get("error", "")))
    return notes


def sweep_run():
    if hg.user_game_running():
        raise ww.Aborted("the user's game is running - not starting")
    hg.acquire_slot(ww.OWNER, ww.EXE, ww.HOME, [ww.PORT], minutes=150)
    res = []
    try:
        for mp in SWEEP_MAPS:
            for which in ("old", "new"):
                res.append(sweep_run_one(mp, which))
    finally:
        hg.release_slot(ww.OWNER)
        set_bins("park")
        ww.seed_home()
        ov = os.path.join(ww.MAINTT, ww.OVERLAY)
        if os.path.exists(ov):
            os.remove(ov)
    json.dump(res, open(os.path.join(RUNS, "summary_sweep.json"), "w"), indent=1)
    return res

def slot_value():
    try:
        return open(ww.SLOTFILE).read().strip()
    except OSError:
        return ""


if __name__ == "__main__":
    a = sys.argv[1:]
    names = [x for x in a[1:]] or list(SCENES)
    if not a:
        print(__doc__)
    elif a[0] == "final-wait":
        # run 4: the final DLL - sweeps at the defect spots (m3l2, m4l2, m5l2b) + stills / GPU / canal pan
        while slot_value() != SLOTNAME:
            time.sleep(15)
        try:
            SWEEP_MAPS[:] = ["m3l2", "m4l2", "m5l2b"]
            for mp in SWEEP_MAPS:
                SWEEP_POSES[mp] = SWEEP_POSES[mp][:1]
            sweep_run()
            run(["wet_day", "canal", "wet_night"])
        finally:
            if slot_value() == SLOTNAME:
                open(ww.SLOTFILE, "w").write("free")
                log("test slot released: free")
    elif a[0] == "sweep-wait":
        while slot_value() != SLOTNAME:
            time.sleep(15)
        try:
            sweep_run()
        finally:
            if slot_value() == SLOTNAME:
                open(ww.SLOTFILE, "w").write("free")
                log("test slot released: free")
    elif a[0] in ("run", "wait-and-run"):
        if a[0] == "wait-and-run":
            while slot_value() != SLOTNAME:
                time.sleep(15)
        try:
            out = run(names)
            print(json.dumps([{k: v for k, v in r.items() if k not in ("markers",)} for r in out], indent=1)[:8000])
        finally:
            if slot_value() == SLOTNAME:
                open(ww.SLOTFILE, "w").write("free")
                log("test slot released: free")
