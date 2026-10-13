"""rainlib.py - harness helpers for the rain-to-the-ground runs (docs/proposals/rainfix_2026-10-13).
Private harness G:/mohaa-hudfeed2 (owner hudfeed2, net_port 12721), DISPLAY2, engine screenshots only.
Binaries: the DEPLOYED exe / game / renderer are copied (read only) from the GOG folder into the harness under
their own names; the cgame under test comes from the rainfix worktree."""
import os, re, sys, time, shutil, zipfile, hashlib, json
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
GOG = "G:/GOG/Medal of Honor - Allied Assault War Chest"
R.OWNER = "hudfeed2"
R.CLIENT = "G:/mohaa-hudfeed2"
R.EXE = os.path.join(R.CLIENT, "openmohaa_rain.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-hudfeed2/runs"
R.PORT = 12721
ARCHIVE = "H:/hzm_archive/rainfix"
OV = os.path.join(HERE, "ov_rain.pk3")
LOGF = os.path.join(HERE, "rain.log")
_SEQ = {"n": int(time.time()) % 100000}


def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(s, flush=True)
    open(LOGF, "a").write(s + "\n")


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def build_overlay(extra_files=None):
    """overlay pk3: the test driver, plus {path in pak: file on disk} (a staged mod-side change, a test shader)"""
    with zipfile.ZipFile(OV, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(HERE, "coop_selftest_xp.scr"), "coop_mod/coop_selftest_xp.scr")
        for arc, src in (extra_files or {}).items():
            z.write(src, arc)
    return OV


def install(cgame_dll, tag):
    """deployed exe / game / renderers from GOG (copied, never written), the given cgame as cgames/cgame_<tag>.dll"""
    def put(src, dst):
        if not os.path.exists(dst) or md5(dst) != md5(src):
            shutil.copyfile(src, dst)
    put(os.path.join(GOG, "openmohaa.exe"), R.EXE)
    put(os.path.join(GOG, "game.dll"), os.path.join(R.CLIENT, "games", "game_rain.dll"))
    put(os.path.join(GOG, "renderer_opengl2.dll"), os.path.join(R.CLIENT, "renderers", "gl2_rain.dll"))
    put(os.path.join(GOG, "renderer_opengl1.dll"), os.path.join(R.CLIENT, "renderers", "gl1_rain.dll"))
    put(cgame_dll, os.path.join(R.CLIENT, "cgames", "cgame_%s.dll" % tag))
    shutil.copyfile(os.path.join(R.CLIENT, "games", "game_rain.dll"), os.path.join(R.CLIENT, "game.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", "gl2_rain.dll"), os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", "gl1_rain.dll"), os.path.join(R.CLIENT, "renderer_opengl1.dll"))
    return "cgame_%s" % tag


def restore():
    shutil.copyfile(os.path.join(R.CLIENT, "games", "game_ship.dll"), os.path.join(R.CLIENT, "game.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", "gl2_ship.dll"), os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "renderers", "gl1_ship.dll"), os.path.join(R.CLIENT, "renderer_opengl1.dll"))
    shutil.copyfile(os.path.join(R.CLIENT, "cgames", "cgame_ship.dll"), os.path.join(R.CLIENT, "cgame.dll"))


def boot(sess, mapname, W, H, cgame_dll, tag, extra=(), overlay_files=None, fps=60):
    R.MAP = mapname
    cg = install(cgame_dll, tag)
    ex = ["set g_ai 0", "set coop_st_xp 1", "set developer 1", "set com_maxfpsUnfocused %d" % fps,
          "set com_maxfps %d" % fps, "set coop_rainStats 1", "set cg_drawviewmodel 0"] + list(extra)
    rundir, notes = S.boot_session(sess, cg, W, H, ex, build_overlay(overlay_files))
    notes["cgame_md5"] = md5(os.path.join(R.CLIENT, "cgame.dll"))
    notes["exe_md5"] = md5(R.EXE)
    log("booted", sess, mapname, "%dx%d" % (W, H), "cgame", notes["cgame_md5"][:8])
    return rundir, notes


def finish(rundir, notes):
    try:
        if rundir:
            S.end_session(rundir, notes or {})
        elif R.CL["proc"] is not None and R.CL["proc"].poll() is None:
            R.CL["proc"].kill()          # our own child, by handle
    except Exception as e:
        log("end_session", repr(e))
        try:
            if R.CL["proc"] is not None and R.CL["proc"].poll() is None:
                R.CL["proc"].kill()
        except Exception:
            pass
    restore()
    try:
        R.hg.release_slot(R.OWNER)
    except Exception:
        pass


def archive(rundir):
    """MOVE a finished run folder to the archive disk, with a file-count check"""
    if not rundir or not os.path.isdir(rundir):
        return None
    n0 = sum(len(f) for _, _, f in os.walk(rundir))
    dst = os.path.join(ARCHIVE, os.path.basename(rundir))
    k = 1
    while os.path.exists(dst):
        k += 1
        dst = os.path.join(ARCHIVE, os.path.basename(rundir) + "_%d" % k)
    os.makedirs(ARCHIVE, exist_ok=True)
    shutil.move(rundir, dst)
    n1 = sum(len(f) for _, _, f in os.walk(dst))
    log("archived %s -> %s (%d files, %s)" % (rundir, dst, n1, "count ok" if n0 == n1 else "COUNT MISMATCH %d" % n0))
    return dst


def cmd(c, pos=(0, 0, 0), yaw=0, pitch=0, wait=20, **kv):
    _SEQ["n"] += 1
    seq = _SEQ["n"]
    p0 = len(R.read_log())
    lines = ["set gq_cmd %s" % c, "set gq_x %g" % pos[0], "set gq_y %g" % pos[1], "set gq_z %g" % pos[2],
             "set gq_yaw %g" % yaw, "set gq_pitch %g" % pitch]
    for k, v in kv.items():
        lines.append("set gq_%s %s" % (k, v))
    lines.append("set gq_go %d" % seq)
    R.step(lines, timeout=60)
    m = R.wait_log(r"GQ done %d [^\r\n]*" % seq, wait, p0)
    return R.read_log()[p0:] if m else None


def tp(pos, yaw, pitch=0, ground=0):
    seg = cmd("tp", pos, yaw, pitch, ground=ground)
    m = re.search(r"GQ view [^\r\n]*", seg or "")
    time.sleep(0.5)
    return m.group(0) if m else None


def sets(*lines):
    R.step(list(lines), timeout=30)


def stats(secs=4.0):
    """mean of the RAINSTAT / RAINCOV lines printed over the next secs seconds"""
    time.sleep(1.2)                       # the line in progress covers the previous settings
    p0 = len(R.read_log())
    time.sleep(secs + 0.3)
    seg = R.read_log()[p0:]
    rows = []
    for line in re.findall(r"RAINSTAT [^\r\n]*", seg):
        d = {}
        for k, v in re.findall(r"(\w+)=([-\d.]+)", line):
            d[k] = float(v)
        rows.append(d)
    covs = [[int(x) for x in line.split()] for line in re.findall(r"RAINCOV((?: -?\d+)+)", seg)]
    if not rows:
        return {}, []
    out = {k: sum(r.get(k, 0) for r in rows) / len(rows) for k in rows[0]}
    sec = out["ms"] / 1000.0 if out.get("ms") else 1.0
    out["fps"] = out["frames"] / sec
    out["made_s"] = out["made"] / sec
    out["want_s"] = out["want"] / sec
    cov = [sum(c[i] for c in covs) / len(covs) for i in range(16)] if covs else []
    return out, cov


def fmt(st, cov):
    if not st:
        return "no RAINSTAT"
    s = ("fps %.0f want/s %.0f made/s %.0f alive %d poolfail %d | rain %.0f us beams %.0f us a frame | start %.0f end %.1f "
         "gap %.1f over ground, cos %.2f life %.0f ms | den %.1f len %.0f spd %.0f slant %d dist %.0f wind %.0f,%.0f | "
         "skips dist %d sky %d stub %d life %d flat %d end %d near %d"
         % (st["fps"], st["want_s"], st["made_s"], st["alive"], st["poolfail"], st["rain_us"], st["beams_us"],
            st["hs"], st["he"], st["gap"], st["cosz"], st["life"], st["den"], st["len"], st["spd"], st["slant"],
            st["dist"], st["wind"], 0, st["kDist"], st["kSky"], st["kStub"], st["kLife"], st["kFlat"], st["kEnd"],
            st["kNear"]))
    if cov:
        s += "\n          cover by height over the feet (32 u bands from -64): " + " ".join("%d" % c for c in cov)
    return s


def shot(outdir, name):
    from PIL import Image
    os.makedirs(outdir, exist_ok=True)
    R.step(["screenshot %s" % name, "wait 60"], timeout=30)
    time.sleep(0.5)
    for fn in os.listdir(R.SHOTS):
        if fn.startswith(name):
            dst = os.path.join(outdir, name + ".png")
            Image.open(os.path.join(R.SHOTS, fn)).convert("RGB").save(dst)
            os.remove(os.path.join(R.SHOTS, fn))
            return dst
    return None


def burst(outdir, name, n):
    return [shot(outdir, "%s_%02d" % (name, i)) for i in range(n)]


def wait_tier(want_len, timeout=90):
    """wait until the rain's streak length (a RAINSTAT field) is within 2 of want_len"""
    t0 = time.time()
    last = None
    while time.time() - t0 < timeout:
        m = re.findall(r"RAINSTAT [^\r\n]* len=(\d+)", R.read_log()[-6000:])
        if m:
            last = int(m[-1])
            if abs(last - want_len) <= 2:
                return last
        time.sleep(1.0)
    return last


def save(rundir, name, obj):
    json.dump(obj, open(os.path.join(rundir, name), "w"), indent=1)
