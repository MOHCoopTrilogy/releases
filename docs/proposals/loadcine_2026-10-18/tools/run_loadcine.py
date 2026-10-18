"""run_loadcine.py - private-harness proof for the loading-screen cinematic (docs/proposals/loadcine_2026-10-18).

Listen-host coop map loads on G:\\mohaa-hudfeed2 (DISPLAY2, background window policy), reusing run_joinflood.py plumbing.
Alternates cl_loadCinematic 0 / 1 for N loads of the same map, reads the ^~^~^ LOADDRAW / LOADCINE / LOADGAP lines the
engine prints (cl_loadProbe 1), and records the first ON load with ffmpeg gdigrab on the harness window (passive).

    python run_loadcine.py <runname> [--map m1l1] [--pairs 3] [--clip CLIP.hzlc] [--exe path\\openmohaa.exe] [--no-video]

Never writes to G:\\mohaa-gl2 or G:\\GOG (the GOG root is only the read-only fs_basepath, as in the other harnesses).
"""
import argparse, importlib.util, os, re, shutil, subprocess, sys, time, zipfile

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\joinflood_2026-10-14\tools"
spec = importlib.util.spec_from_file_location("jf", os.path.join(TOOLS, "run_joinflood.py"))
jf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jf)
hg, hw = jf.hg, jf.hw

ROOT = r"C:\mohaa-coop-dev"
SLOT = ("hudfeed2", r"G:\mohaa-hudfeed2")
SCRATCH = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad\loadcine"
ARCHIVE = os.path.join(SCRATCH, "archive")   # H: is not mounted on every run; the log is also in qconsole of the home
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
WIDGET = """resource
Label
{
name "hzm_loadcine"
rect 0 0 640 481
fgcolor 1.00 1.00 1.00 1.00
bgcolor 0.00 0.00 0.00 0.00
borderstyle "NONE"
enabledcvar "ui_loadCineOn"
}
"""


def build_paks(clip):
    os.makedirs(SCRATCH, exist_ok=True)
    # 1. the mod's scripts/ui/cfg as released at HEAD (no assets) - the same recipe as run_joinflood.fix_codepak
    head = subprocess.run(["git", "-C", MOD, "rev-parse", "HEAD"], capture_output=True, check=True).stdout.decode().strip()
    code = os.path.join(SCRATCH, "code_%s.pk3" % head[:10])
    if not os.path.isfile(code):
        tops = [t for t in subprocess.run(["git", "-C", MOD, "ls-tree", "--name-only", head], capture_output=True,
                                          check=True).stdout.decode().splitlines()
                if t not in ("sound", "textures", "models", "gfx", "env") and not t.lower().endswith(".pk3")
                and not t.startswith(".git")]
        subprocess.run(["git", "-C", MOD, "archive", "--format=zip", "-1", "-o", code, head, "--"] + tops, check=True)
    # 2. the overlay: loadingbar.txt with the hzm_loadcine widget (staged patch, see README) + rules + clip
    lb = subprocess.run(["git", "-C", MOD, "show", "HEAD:ui/loadingbar.txt"], capture_output=True, check=True).stdout.decode("latin-1")
    marker = 'resource\nLabel\n{\nname "hzm_loadhint_bg"'
    nl = "\r\n" if "\r\n" in lb else "\n"
    lbn = lb.replace("\r\n", "\n")
    assert marker in lbn, "loadingbar.txt layout changed"
    lbn = lbn.replace(marker, WIDGET + marker, 1)
    if nl == "\r\n":
        lbn = lbn.replace("\n", "\r\n")
    ov = os.path.join(SCRATCH, "zzzzzzzzzzzz_loadcine_test.pk3")
    name = os.path.splitext(os.path.basename(clip))[0]
    with zipfile.ZipFile(ov, "w", zipfile.ZIP_STORED) as z:
        z.writestr("ui/loadingbar.txt", lbn.encode("latin-1"))
        z.writestr("ui/loadclips.txt", ("map * %s\n" % name).encode())
        z.write(clip, "loadclips/%s.hzlc" % name)
    return code, ov, head


def prep_bins(exe):
    d = os.path.join(SLOT[1], "loadcine")
    os.makedirs(d, exist_ok=True)
    for src, dst in (("OpenAL64.dll", None), ("SDL2.dll", None), ("libcurl.dll", None), ("renderer_opengl1.dll", None),
                     ("renderer_opengl2.dll", None), ("game.dll", None), ("cgame.dll", None)):
        s, t = os.path.join(jf.GOG, src), os.path.join(d, dst or src)
        if not os.path.isfile(t) or jf.md5f(t) != jf.md5f(s):
            shutil.copyfile(s, t)
    shutil.copyfile(exe, os.path.join(d, "openmohaa_lc.exe"))
    return d


def seed_home(run, code, ov, maps):
    hm = os.path.join(SLOT[1], "home_lc_" + run)       # carries "<slot>\home" -> classified as this harness
    mt = os.path.join(hm, "maintt")
    os.makedirs(os.path.join(mt, "configs"), exist_ok=True)
    pr = os.path.join(SLOT[1], "pristine")
    for f in ("autoexec.cfg", "coop_defaults.cfg"):
        shutil.copyfile(os.path.join(pr, f), os.path.join(mt, f))
    shutil.copyfile(code, os.path.join(mt, jf.CODEPAK))
    shutil.copyfile(ov, os.path.join(mt, os.path.basename(ov)))
    key = os.urandom(2048)
    open(os.path.join(hm, "qkey"), "wb").write(key)
    cfg = jf.read(os.path.join(pr, "omconfig.cfg"))
    cfg = re.sub(r'(?im)^seta name "[^"\r\n]*"', 'seta name "LCTester"', cfg)
    cfg = re.sub(r'(?im)^seta coop_loA([1-4]) "[^"\r\n]*"', r'seta coop_loA\1 ""', cfg)
    open(os.path.join(mt, "configs", "omconfig.cfg"), "wb").write(cfg.encode("latin-1"))
    open(os.path.join(mt, "whatsnew_pending.cfg"), "wb").write(b"// up to date\r\n")
    return hm, mt


def launch(bins, hm, mt, firstmap, fps, vsync=0, W=1280, H=720):
    boot = ['bind F12 "exec isstep.cfg"', "set ui_gmbox 0", "ui_checkrestart", "set coop_idleInspect 0", "set coop_tinnitus 0",
            "set com_maxfps %d" % fps, "set coop_coverAuto 0", "set cl_loadProbe 1", "set cl_loadCinematic 0",
            "seta coop_campaign 1"]
    sets = [("com_target_game", "2"), ("fs_basepath", jf.GOG), ("fs_homepath", hm), ("cl_renderer", "opengl2"),
            ("r_ext_framebuffer_multisample", "0"), ("r_ext_multisample", "0"), ("r_mode", "-1"),
            ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"), ("r_swapInterval", str(vsync)), ("developer", "0"),
            ("logfile", "2"), ("net_enabled", "1"), ("net_ip", "127.0.0.1"), ("net_port", "12722")]
    args = [os.path.join(bins, "openmohaa_lc.exe")]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+set", "g_gametype", "2", "+exec", "lc_on.cfg", "+set", "ui_dmmap", firstmap, "+exec", "coop_mod/start_server.cfg"]
    args, late = hw.apply_policy(args, width=W, height=H, unfocused_fps=fps)
    boot += late
    open(os.path.join(mt, "lc_on.cfg"), "w", newline="\n").write("\n".join(boot) + "\n")
    hg.acquire_slot(SLOT[0], args[0], hm, [12722], 60)
    bg = hw.launch_background(args[0], args[1:], bins, policy=False, log=jf.log)
    try:
        hg.set_slot_pid(SLOT[0], bg.proc.pid)
    except Exception as e:
        jf.log("slot pid note:", e)
    c = {"idx": 1, "owner": SLOT[0], "bg": bg, "hm": hm, "mt": mt, "log": os.path.join(mt, "qconsole.log"), "step": 0}
    jf.ST["clients"].append(c)
    jf.log("client pid", bg.proc.pid)
    return c


def window_rect(bg):
    import ctypes
    from ctypes import wintypes as wt
    h = bg.hwnd()
    rc = wt.RECT()
    pt = wt.POINT(0, 0)
    ctypes.windll.user32.GetClientRect(h, ctypes.byref(rc))
    ctypes.windll.user32.ClientToScreen(h, ctypes.byref(pt))
    return pt.x, pt.y, rc.right, rc.bottom


def start_video(bg, path, fps=60):
    x, y, w, h = window_rect(bg)
    w -= w % 2
    h -= h % 2
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "0",
           "-offset_x", str(x), "-offset_y", str(y), "-video_size", "%dx%d" % (w, h), "-i", "desktop",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", path]
    jf.log("video rect", (x, y, w, h))
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, creationflags=0x08000000)


def stop_video(p):
    try:
        p.stdin.write(b"q")
        p.stdin.flush()
        p.wait(20)
    except Exception:
        p.kill()


def wait_free(minutes=180):
    """one game at a time: block while ANY other openmohaa / omohaaded process is up (harness, user or server)"""
    t0 = time.time()
    while time.time() - t0 < minutes * 60:
        busy = [p for p in hg.classify() if p.get("cls") in ("HARNESS", "USER", "SERVER")]
        if not busy:
            return
        time.sleep(10)
    raise SystemExit("gave up waiting for the other games to finish")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--map", default="m1l1")
    ap.add_argument("--pairs", type=int, default=3)
    ap.add_argument("--clip", default=os.path.join(SCRATCH, "..", "clips", "test_placeholder.hzlc"))
    ap.add_argument("--exe", default=os.path.join(ROOT, "openmohaa-hzm-loadcine", ".cmake", "Release", "openmohaa.exe"))
    ap.add_argument("--fps", type=int, default=120)
    ap.add_argument("--vsync", type=int, default=0, help="r_swapInterval of the harness client (the user plays with 1)")
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--fpslist", default="30", help="cl_loadCineFps values, each measured with its own ON/OFF pairs")
    ap.add_argument("--classic", action="store_true", help="ui_loadClassic 1: the stock progress bar over the clip")
    ap.add_argument("--video-only", action="store_true", help="record every ON load (timings then carry the recorder's load)")
    a = ap.parse_args()
    wait_free()
    jf.ST.update({"run": a.run, "usercfg": False, "listen": True, "mx": {}, "ufps": a.fps})
    jf.SCR = SCRATCH
    code, ov, head = build_paks(os.path.abspath(a.clip))
    bins = prep_bins(a.exe)
    jf.log("exe md5", jf.md5f(os.path.join(bins, "openmohaa_lc.exe")), "mod head", head[:10])
    hm, mt = seed_home(a.run, code, ov, a.map)
    c = launch(bins, hm, mt, a.map, a.fps, a.vsync)
    results = []
    vid = None
    try:
        # the launch itself loads the map once with the cinematic OFF (cold cache - discarded)
        m = jf.wait_for(c["log"], r"\^~\^~\^ LOADDRAW [^\r\n]*end=end", 300)
        jf.check("first (cold) load finished", m, m.group(0)[:160] if m else "")
        time.sleep(12)
        order = []
        for f in [int(x) for x in a.fpslist.split(",")]:
            for i in range(a.pairs):
                order += [(1, f), (0, f)]
        if not a.no_video:
            order.append((1, int(a.fpslist.split(",")[0]), "video"))   # the recorded load is NOT in the timings
        for n, item in enumerate(order):
            on, cfps = item[0], item[1]
            st = len(jf.read(c["log"]))
            lines = ["set cl_loadCinematic %d" % on, "set cl_loadCineFps %d" % cfps, "set ui_loadClassic %d" % (1 if a.classic else 0),
                     "set ui_dmmap " + a.map,
                     "exec coop_mod/start_server.cfg"]
            record = len(item) > 2
            if record:
                vid = start_video(c["bg"], os.path.join(SCRATCH, a.run + "_load.mp4"))
                time.sleep(1.0)
            jf.step(c, lines, timeout=20)
            m = jf.wait_for(c["log"], r"\^~\^~\^ LOADDRAW [^\r\n]*end=end", 300, st)
            txt = jf.read(c["log"])[st:]
            if record and vid:
                time.sleep(2.0)
                stop_video(vid)
                vid = "done"
            jf.check("load %d cine=%d finished" % (n, on), m)
            draw = re.search(r"\^~\^~\^ LOADDRAW[^\r\n]*", txt)
            cine = re.findall(r"\^~\^~\^ LOADCINE[^\r\n]*", txt)
            gaps = re.findall(r"\^~\^~\^ LOADGAP[^\r\n]*", txt)
            if not record:
                results.append((on, draw.group(0) if draw else "", cine, gaps, cfps))
            jf.log("LOAD", n, "cine", on, "|", draw.group(0) if draw else "-")
            for l in cine:
                jf.log("   ", l)
            for l in gaps[:3]:
                jf.log("   ", l)
            time.sleep(12)
        errs = re.findall(r"[^\r\n]*(?:Script Error|LOADCINE bad|LOADCINE decode failed)[^\r\n]*", jf.read(c["log"]))
        jf.check("no Script Error / bad clip lines", not errs, "; ".join(errs[:3]))
    except Exception as e:
        jf.check("harness ran to the end", False, repr(e))
    finally:
        if vid and vid != "done":
            stop_video(vid)
        for cc in jf.ST["clients"]:
            try:
                jf.stop_client(cc)
            except Exception as e:
                jf.log("stop note", e)
        time.sleep(2)
    ms = lambda d: int(re.search(r" ms=(\d+)", d).group(1)) if re.search(r" ms=(\d+)", d) else None
    off_ms = [ms(r[1]) for r in results if not r[0] and r[1]]
    for f in sorted(set(r[4] for r in results)):
        on_ms = [ms(r[1]) for r in results if r[0] and r[1] and r[4] == f]
        off_f = [ms(r[1]) for r in results if not r[0] and r[1] and r[4] == f]
        jf.log("fps", f, "ON ms", on_ms, "OFF ms", off_f)
        if on_ms and off_f:
            jf.log("fps %d: mean ON %.0f OFF %.0f  overhead %.1f%%" % (f, sum(on_ms) / len(on_ms), sum(off_f) / len(off_f),
                   100.0 * (sum(on_ms) / len(on_ms) / (sum(off_f) / len(off_f)) - 1)))
    dst = os.path.join(ARCHIVE, a.run)
    os.makedirs(dst, exist_ok=True)
    shutil.copyfile(c["log"], os.path.join(dst, "qconsole.log"))
    jf.log("log archived to", dst)


if __name__ == "__main__":
    main()
