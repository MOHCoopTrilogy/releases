"""run_hudfeed.py - ONE batched in-engine before/after run for the HUD declutter (queue slot "hudfeed").

    python run_hudfeed.py build      # pack the two overlay pk3s (before = driver only; after = working-tree scripts + driver)
    python run_hudfeed.py run        # wait for slot == hudfeed, run BEFORE then AFTER on m3l2, release the slot
    python run_hudfeed.py gifs       # left-side GIFs + contact sheets from both runs
    python run_hudfeed.py analyze    # FEED lines / gmbox prints per phase from both logs

Harness G:\\mohaa-hudfeed: byte copies of the LIVE G:\\mohaa-gl2 exe/cgame/game/renderers (via the voicefix copies) plus the
test cgame/game built in openmohaa-hzm-hudfeed, fresh home from the adsanim pristine (no qkey/saves), basepath = GOG read-only,
net_ip 127.0.0.1, com_maxfps 60, DISPLAY2 via harness_window.launch_background (the ironsights harness modules).
The test-only driver (overlay/coop_mod/coop_selftest_xp.scr, started by main.scr when coop_st_xp 1) plays the same busy
sequence in both runs; this script screenshots every 0.5 s and takes the player out of god mode for the DBNO phase.
"""
import os, re, sys, time, zipfile, subprocess, shutil
IS = r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
SCR = R.SCRATCH
R.OWNER = "hudfeed"
R.CLIENT = r"G:\mohaa-hudfeed"
R.EXE = os.path.join(R.CLIENT, "openmohaa_ironsight.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-hudfeed/runs"
R.PORT = 12701
R.MAP = "m3l2"
R.OVERLAY = "zzzzzzzzzzzzzzz_hudfeedtest.pk3"
QNAME = "hudfeed"
SLOT = os.path.join(SCR, "test_slot.txt")
HF = os.path.join(SCR, "hudfeed")
HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
DRIVER = os.path.join(HERE, "overlay", "coop_mod", "coop_selftest_xp.scr")
OV = {"before": os.path.join(HF, "ov_before.pk3"), "after": os.path.join(HF, "ov_after.pk3")}
LOGF = os.path.join(HF, "run.log")
DIRS = ("coop_mod/", "global/", "maps/", "ui/", "ubersound/", "scripts/")
EXTS = (".scr", ".urc", ".cfg", ".shader", ".txt")


def log(*a):
    s = time.strftime("%H:%M:%S") + " " + " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOGF, "a") as f:
        f.write(s + "\n")


def changed_files():
    out = subprocess.run(["git", "-C", MOD, "status", "--porcelain", "-uall"], capture_output=True, text=True).stdout
    res = []
    for ln in out.splitlines():
        p = ln[3:].strip().strip('"')
        if p.startswith(DIRS) and p.endswith(EXTS) and "coop_selftest_xp.scr" not in p and os.path.isfile(os.path.join(MOD, p)):
            res.append(p)
    return sorted(set(res))


def build():
    os.makedirs(HF, exist_ok=True)
    with zipfile.ZipFile(OV["before"], "w", zipfile.ZIP_DEFLATED) as z:
        z.write(DRIVER, "coop_mod/coop_selftest_xp.scr")
    files = changed_files()
    with zipfile.ZipFile(OV["after"], "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(MOD, f), f)
        z.write(DRIVER, "coop_mod/coop_selftest_xp.scr")
    log("overlays: before 1 file, after", len(files) + 1, "files")
    for f in files:
        log("   ", f)


def has(pat, start=0):
    return re.search(pat, R.read_log()[start:]) is not None


def sequence(mode, t0log):
    """screenshot every 0.5 s in 10 s chunks; react to the driver's phases between chunks"""
    n, downed, dead_at, done_at, t0 = 0, False, None, None, time.time()
    R.step(["set hf_go 1"], timeout=30)
    while time.time() - t0 < 260:
        pre = []
        if not downed and has(r"\^~\^~\^ HF phase down", t0log):
            pre += ["dog 0", "wait 100", "set hf_downok 1"]
            downed = True
        if dead_at is None and has(r"\^~\^~\^ HF phase dead", t0log):
            dead_at = time.time()
        lines = list(pre)
        for k in range(20):
            n += 1
            lines += ["screenshot hf%04d" % n, "wait 500"]
            if dead_at and time.time() - dead_at > 4 and k % 5 == 0:
                lines += ["+attackprimary", "wait 120", "-attackprimary"]
        R.step(lines, timeout=60)
        if done_at is None and has(r"\^~\^~\^ HF done", t0log):
            done_at = time.time()
        if done_at and time.time() - done_at > 6:
            break
    if mode == "after":
        R.step(["pushmenu coop_lastmission", "wait 800", "screenshot hf_lastmission", "wait 300", "popmenu 0", "wait 200"], timeout=30)
    log(mode, "screenshots", n)


def run():
    os.makedirs(HF, exist_ok=True)
    log("waiting for slot ==", QNAME)
    while open(SLOT).read().strip() != QNAME:
        time.sleep(5)
    log("slot is ours")
    t0 = time.time()
    try:
        modes = [m for m in ("before", "after") if m in sys.argv[2:]] or ["before", "after"]
        for mode in modes:
            rundir = notes = None
            try:
                game = "game_live.dll" if mode == "before" else "game_hudfeed.dll"
                shutil.copyfile(os.path.join(R.CLIENT, "games", game), os.path.join(R.CLIENT, "game.dll"))
                cg = "cgame_live" if mode == "before" else "cgame_hudfeed"
                extra = ["set g_ai 1", "set coop_st_xp 1", "set hf_go 0", "set hf_downok 0", "set ui_gmbox 1", "ui_checkrestart", "ui_hud 1",
                         "set ui_crosshair 1", "set coop_dbno 1", "seta coop_hardcore 0", "set coop_feedDebug 1", "seta coop_hintSeen \"\"",
                         "seta coop_hintSeen2 \"\"", "seta coop_feed 1", "seta coop_hints 1"]
                rundir, notes = S.boot_session("hf_" + mode, cg, 1280, 720, extra, OV[mode])
                log(mode, "booted", notes)
                t0log = len(R.read_log())
                if not R.wait_log(r"\^~\^~\^ HF driver armed", 5):
                    log(mode, "driver not armed yet (continuing)")
                sequence(mode, t0log)
            except Exception as e:
                import traceback
                log(mode, "FAILED", repr(e), traceback.format_exc())
            finally:
                try:
                    if rundir:
                        S.end_session(rundir, notes or {})
                    elif R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                        R.CL["proc"].kill()
                except Exception as e:
                    log("end_session", repr(e))
                time.sleep(3)
    finally:
        shutil.copyfile(os.path.join(R.CLIENT, "games", "game_live.dll"), os.path.join(R.CLIENT, "game.dll"))
        open(SLOT, "w").write("free")
        log("slot released (free) after %.1f min" % ((time.time() - t0) / 60))


# ---------------------------------------------------------------- outputs
def gifs():
    from PIL import Image, ImageDraw
    out = os.path.join(PROP, "media")
    os.makedirs(out, exist_ok=True)
    for mode in ("before", "after"):
        d = os.path.join(R.RUNS, "hf_" + mode)
        files = sorted(f for f in os.listdir(d) if re.match(r"hf\d{4}\.(png|jpg)$", f))
        if not files:
            log("no frames for", mode)
            continue
        frames = []
        for f in files:
            im = Image.open(os.path.join(d, f)).convert("RGB")
            W, H = im.size
            crop = im.crop((0, 0, int(W * 0.5), H))           # the left half: where the old text lived + the feed
            frames.append(crop)
        w, h = frames[0].size
        scale = 0.75
        while True:
            fr = [f.resize((int(w * scale), int(h * scale)), Image.LANCZOS) for f in frames]
            lab = []
            for i, f in enumerate(fr):
                g = f.copy()
                ImageDraw.Draw(g).text((6, 6), "%s  t=%.1fs" % (mode.upper(), i * 0.5), fill=(255, 255, 0))
                lab.append(g)
            p = os.path.join(out, "hud_%s.gif" % mode)
            lab[0].save(p, save_all=True, append_images=lab[1:], duration=250, loop=0, optimize=True)
            if os.path.getsize(p) < 19 * 1024 * 1024 or scale < 0.35:
                break
            scale *= 0.8
        log("gif", p, len(fr), os.path.getsize(p))
        # contact sheet: every 4th frame, 6 columns
        pick = frames[::4]
        tw, th = 320, int(320 * h / w)
        cols = 6
        rows = (len(pick) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw, rows * (th + 14)), (20, 20, 20))
        for i, f in enumerate(pick):
            t = f.resize((tw, th), Image.LANCZOS)
            x, y = (i % cols) * tw, (i // cols) * (th + 14)
            sheet.paste(t, (x, y + 14))
            ImageDraw.Draw(sheet).text((x + 4, y + 1), "%s t=%.1fs" % (mode, i * 2.0), fill=(255, 255, 0))
        sp = os.path.join(out, "sheet_%s.jpg" % mode)
        sheet.save(sp, quality=82)
        log("sheet", sp, sheet.size)
    lm = os.path.join(R.RUNS, "hf_after", "hf_lastmission.png")
    if os.path.exists(lm):
        Image.open(lm).convert("RGB").save(os.path.join(out, "last_mission_page.jpg"), quality=88)


def analyze():
    res = []
    for mode in ("before", "after"):
        p = os.path.join(R.RUNS, "hf_" + mode, "qconsole.log")
        if not os.path.exists(p):
            res.append("%s: no log" % mode)
            continue
        L = open(p, "rb").read().decode("latin-1").splitlines()
        phase, feed, errs = "boot", {}, []
        for ln in L:
            m = re.search(r"\^~\^~\^ HF (phase \w+|done|driver armed)", ln)
            if m:
                phase = m.group(1)
                continue
            if "^~^~^ FEED" in ln:
                feed.setdefault(phase, []).append(ln.split("^~^~^ FEED", 1)[1].strip())
            if re.search(r"Script Error|\^~\^~\^ SCRIPT|unknown command|label .* not found|Couldn't find label|overflow|dropped", ln, re.I):
                errs.append(ln.strip())
        res.append("==== %s: %d feed lines, %d script-error lines" % (mode, sum(len(v) for v in feed.values()), len(errs)))
        for ph, v in feed.items():
            res.append("  [%s]" % ph)
            res += ["     " + x for x in v]
        res += ["  ERR " + e for e in errs[:40]]
    txt = "\n".join(res)
    print(txt)
    open(os.path.join(HF, "analysis.txt"), "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    {"build": build, "run": run, "gifs": gifs, "analyze": analyze}[sys.argv[1]]()
