"""ice_ingame.py <map> <cam,cam,...> [--tag before]   BEFORE stills of the frozenriver ice, in the real engine (gl2).

Built on docs/proposals/water_wetness_2026-09-27/ingame/ww_ingame.py (same overlay camera, same launch/step/join
code; that module's globals are re-pointed here). Private client G:\\mohaa-hudfeed5\\ice1025 = copy of
G:\\mohaa-hudfeed3\\hz1025 (the v1.10.36 candidate set i136), home G:\\mohaa-hudfeed5\\home_ice1025, net_port 12941.
Nothing under G:\\mohaa-gl2 / the GOG folder / %APPDATA% is written. Run only inside harness_turn wait/release ice1025
and the heavy.lock protocol (the caller does that). Screenshots: the engine's `screenshot`, 1280x720.
"""
import os, sys, re, json, time, shutil, importlib.util, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
WWD = r"C:\mohaa-coop-dev\docs\proposals\water_wetness_2026-09-27\ingame"
sys.path.insert(0, WWD)
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import ww_ingame as W  # noqa: E402
import make_overlay as MO  # noqa: E402

SRC = r"G:\mohaa-hudfeed3"
CLIENT = r"G:\mohaa-hudfeed5\ice1025"
HOME = r"G:\mohaa-hudfeed5\home_ice1025"
PAKDIR = SRC + r"\i136_paks"
PAKS = ["zzzzzz_co-op_hzm_mod_code.pk3", "zzzzzzzzzz_coop_fixes.pk3", "zzzzzzzzzz_coop_loadclips.pk3",
        "zzzzzzzzzz_coop_loadclips_2.pk3", "zzzzzzzzzz_coop_loadclips_3.pk3"]
RUNS = r"G:\mohaa-hudfeed5\runs_ice1025"
GIF = 0
RENDERER = None
SHADER = False
VARIANTS = []
RECHECK = False
GPU = False
EXTGLSL = None
GL1 = False
ASSETS = r"H:\hzm_work\ice1025_assets"
MODSH = r"H:\hzm_work\ice1025_mod\scripts\zz_coop_coldwater.shader"
VIEWS = json.load(open(os.path.join(HERE, "views.json")))
W.CLIENT = CLIENT
W.EXE = CLIENT + r"\openmohaa_i136.exe"
W.HOME = HOME
W.MAINTT = HOME + r"\maintt"
W.LOG = W.MAINTT + r"\qconsole.log"
W.SHOTS = W.MAINTT + r"\screenshots"
W.PRISTINE = CLIENT + r"\pristine"
W.RUNS = RUNS
W.OWNER = "hudfeed5"
W.PORT = 12941
MO.DEPLOYED = PAKDIR + r"\zzzzzz_co-op_hzm_mod_code.pk3"


def setup():
    os.makedirs(CLIENT, exist_ok=True)
    for fn in ("OpenAL64.dll", "SDL2.dll", "libcurl.dll", "game.dll", "cgame.dll", "renderer_opengl1.dll", "renderer_opengl2.dll"):
        shutil.copyfile(SRC + "\\i136\\" + fn, CLIENT + "\\" + fn)
    shutil.copyfile(SRC + r"\i136\openmohaa_i136.exe", W.EXE)
    os.makedirs(CLIENT + r"\cgames", exist_ok=True)
    shutil.copyfile(SRC + r"\i136\cgame.dll", CLIENT + r"\cgames\cgame_hz.dll")
    if RENDERER:
        shutil.copyfile(RENDERER, CLIENT + r"\renderer_opengl2.dll")
    if not os.path.isdir(W.PRISTINE):
        shutil.copytree(SRC + r"\i136\pristine", W.PRISTINE)
    os.makedirs(W.MAINTT, exist_ok=True)
    W.seed_home()
    for p in PAKS:
        dst = os.path.join(W.MAINTT, p)
        if os.path.exists(dst):
            os.remove(dst)
        os.link(PAKDIR + "\\" + p, dst)
    import zipfile
    ovp = os.path.join(W.MAINTT, "zzzzzzzzzzzzz_ice1025_test.pk3")
    with zipfile.ZipFile(ovp, "w", zipfile.ZIP_STORED) as z:
        for fn in ("ice_pack.tga", "ice_gl1.tga", "coldwater.tga", "coldwater_add.tga"):
            z.write(os.path.join(ASSETS, "textures", "hzm", fn), "textures/hzm/" + fn)
        if SHADER:
            z.write(MODSH, "scripts/zz_coop_coldwater.shader")
        if EXTGLSL:
            z.write(EXTGLSL, "glsl/hzmwater_fp.glsl")
    if EXTGLSL:
        with open(os.path.join(W.MAINTT, "configs", "omconfig.cfg"), "a", newline=chr(10)) as fh:
            fh.write("seta r_externalGLSL 1" + chr(10))
    for f in ("autoexec.cfg", "coop_defaults.cfg"):
        shutil.copyfile(r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\\" + f, os.path.join(W.MAINTT, f))


def run(mapname, cams, tag):
    os.makedirs(RUNS, exist_ok=True)
    sc0 = dict(map=mapname, kind=("mp" if "/" in mapname else "coop"), type="water", path="static")
    first = VIEWS[cams[0]]
    sc0["eye"], sc0["tgt"] = first[1], first[2]
    setup()
    for fn in os.listdir(W.SHOTS) if os.path.isdir(W.SHOTS) else []:
        os.remove(os.path.join(W.SHOTS, fn))
    os.makedirs(W.SHOTS, exist_ok=True)
    W.hg.acquire_slot(W.OWNER, W.EXE, W.HOME, [W.PORT], minutes=40)
    notes = {"map": mapname, "cams": cams}
    try:
        c, cmd, nplus = W.launch(sc0)
        if not W.wait_log(r"Detected Coop for" if sc0["kind"] == "coop" else r"MPPROG init subscribed|MPWEATHER", 600):
            raise RuntimeError("map never became ready")
        time.sleep(4)
        notes["weather"] = (W.wait_log(r"\^~\^~\^ WEATHER coop=(\w+)", 60) or [None]) and re.findall(r"WEATHER coop=(\w+)", W.read_log())[-1:]
        time.sleep(8)
        notes["joined"] = W.join(sc0)
        time.sleep(4)
        for cn in cams:
            _, eye, tgt = VIEWS[cn]
            sc = dict(eye=eye, tgt=tgt, path="static")
            o, p, y = W.path(sc, 1)[0]
            start = len(W.read_log())
            W.step(W.place(o, p, y) + ["wait 1500", "coord"])
            m = re.findall(r"location: (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)", W.read_log()[start:])
            if not m or max(abs(float(m[-1][i]) - o[i]) for i in range(3)) > 14.0:
                print("camera %s did not land (%s vs %s): skipped" % (cn, m[-1] if m else None, o), flush=True)
                notes.setdefault("skipped", []).append(cn)
                continue
            hud = ["set coop_cineHud 5", "set r_hzmWater 1"]
            # A/B in ONE session on the same camera: the water preset off (today's look) then on, 2.5 s settle each
            for pv, lab in ((0, "B"), (1, "A")):
                W.step(hud + ["set r_hzmWaterPreset %d" % pv, "wait 2500"] + hud + ["screenshot ice_%s_%s_%s_%s" % (tag, mapname.replace("/", "_"), cn, lab)])
            if RECHECK:
                # state-leak check: preset off again after the preset was on, then on again
                for pv, lab in ((0, "B2"), (1, "A2")):
                    W.step(hud + ["set r_hzmWaterPreset %d" % pv, "wait 2500"] + hud + ["screenshot ice_%s_%s_%s_%s" % (tag, mapname.replace("/", "_"), cn, lab)])
            for vi, dv in enumerate(VARIANTS):
                sets = ["set " + x.strip() for x in dv.split(";") if x.strip()]
                W.step(hud + ["set r_hzmWaterPreset 1"] + sets + ["wait 2000"] + hud +
                       ["screenshot ice_%s_%s_%s_v%d" % (tag, mapname.replace("/", "_"), cn, vi)])
            if VARIANTS:
                W.step(["set r_hzmWaterPlanar 0", "set r_hzmWaterPlanarDbg 0", "set r_hzmWaterBody 2", "set r_hzmWaterFloe 1"])
            if GPU:
                cfgs = [("preset0", "r_hzmWaterPreset 0;r_hzmWaterPlanar 0"), ("preset1", "r_hzmWaterPreset 1;r_hzmWaterPlanar 0"),
                        ("preset1_planar", "r_hzmWaterPreset 1;r_hzmWaterPlanar 1")]
                W.step(["set r_gfxProbe 1"])
                for nm, sets in cfgs:
                    L = hud + ["set " + x for x in sets.split(";")] + ["wait 1500", "gfxresettiming", "wait 6000", "gfxprobe", "echo ^~^~^ GPUCFG " + nm + " " + cn]
                    W.step(L, timeout=120)
                W.step(["set r_gfxProbe 0", "set r_hzmWaterPreset 1", "set r_hzmWaterPlanar 0"])
            if GIF:
                # swell/ripple motion: game time runs 0.2 s per rendered frame, two frames per capture = 0.4 s per GIF frame
                for pv, lab in ((0, "B"), (1, "A")):
                    L = hud + ["set r_hzmWaterPreset %d" % pv, "wait 1500", "set fixedtime 200"]
                    for k in range(GIF):
                        L += hud + ["wait 1", "wait 1", "screenshot ice_%s_%s_%s_%s_mo%02d" % (tag, mapname.replace("/", "_"), cn, lab, k)]
                    L += ["set fixedtime 0", "wait 300"]
                    W.step(L, timeout=400)
        notes["script_errors"] = len(re.findall(r"Script Error", W.read_log()))
    finally:
        proc = W.CLIENT_H["proc"]
        if proc is not None and proc.poll() is None:
            try:
                W.rcon("quit")
                proc.wait(40)
            except Exception:
                pass
        cc = W.CLIENT_H["c"]
        if cc is not None:
            cc.close()
            rep = cc.report()
            notes["window"] = {"clean": rep["clean"], "violations": rep["violations"]}
        W.CLIENT_H["c"] = W.CLIENT_H["proc"] = None
        out = os.path.join(RUNS, tag + "_" + mapname.replace("/", "_"))
        os.makedirs(out, exist_ok=True)
        if os.path.isdir(W.SHOTS):
            for fn in sorted(os.listdir(W.SHOTS)):
                shutil.move(os.path.join(W.SHOTS, fn), os.path.join(out, fn))
        if os.path.exists(W.LOG):
            shutil.copyfile(W.LOG, os.path.join(out, "qconsole.log"))
        json.dump(notes, open(os.path.join(out, "notes.json"), "w"), indent=1)
        W.hg.release_slot(W.OWNER)
        ov = os.path.join(W.MAINTT, W.OVERLAY)
        if os.path.exists(ov):
            os.remove(ov)
        print(json.dumps(notes))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("map"); ap.add_argument("cams"); ap.add_argument("--tag", default="ice")
    ap.add_argument("--renderer", default=None); ap.add_argument("--gif", type=int, default=0)
    ap.add_argument("--shader", action="store_true"); ap.add_argument("--gl1", action="store_true"); ap.add_argument("--extglsl", default=None); ap.add_argument("--variants", default=""); ap.add_argument("--gpu", action="store_true"); ap.add_argument("--recheck", action="store_true")
    a = ap.parse_args()
    RENDERER = a.renderer; GIF = a.gif; SHADER = a.shader; GL1 = a.gl1
    EXTGLSL = a.extglsl
    GPU = a.gpu
    RECHECK = a.recheck
    VARIANTS = [x for x in a.variants.split('|') if x]
    _orig = W.hw.apply_policy
    def _pol(args, **kw):
        r, late = _orig(args, **kw)
        if GL1:
            r = ["opengl1" if x == "opengl2" else x for x in r]
        if EXTGLSL:
            pass
        return r, late
    W.hw.apply_policy = _pol
    run(a.map, a.cams.split(","), a.tag)
