"""run_db2.py - in-game proof of the end-of-mission debrief, take two (branch debrief2).

Reuses the joinflood harness plumbing (docs/proposals/joinflood_2026-10-14/tools/run_joinflood.py): a dedicated server on
127.0.0.1 and ONE fake-identity client (G:\\mohaa-hudfeed5 slot, DISPLAY2 only, never focused, muted). Binaries = the
v1.10.62 candidate set in the GOG root, with the client's cgame.dll swapped for the debrief2 build. The debrief2 mod
worktree is packed as the code pak; a test-only overlay pk3 adds the new textures (they ship in the fixes pak) and the
staging script tools/overlay/coop_mod/coop_selftest_xp.scr.

Per resolution: lobby -> rcon map m1l1 -> join -> god + notarget (+ nodamage from the script) -> rcon set db_go 1, which
earns a finish, an emote, a medal, a challenge, a helmet and 8200 XP (two promotions + their rank unlocks) through the
real paths and then ends the mission through coop_mod/missioncomplete.scr. Stills at fixed moments; the first resolution
also records a frame sequence (PrintWindow of the test window, never a desktop grab) for the video.

    python -I run_db2.py <runname> [--res 1280x720,1024x768,1680x720] [--video] [--skip]
"""
import importlib.util, io, os, re, shutil, subprocess, sys, threading, time, zipfile

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\joinflood_2026-10-14\tools"
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("jf", os.path.join(TOOLS, "run_joinflood.py"))
jf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jf)
jf.MODWT = r"C:\mohaa-coop-dev\hzm-mod-debrief2"
SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\62f7348a-09fe-4e2b-810a-023a3be2b822\scratchpad\db2run"
jf.SCR = SCR
jf.ARCHIVE = os.path.join(SCR, "archive")
log, check, read, wait_for, step = jf.log, jf.check, jf.read, jf.wait_for, jf.step
ST = jf.ST
CGAME = r"H:\hzm_work\debrief2_build\code\client\cgame\Release\cgame.dll"
FIXES = r"C:\hzm-root-debrief2\docs\tools\assets\fixes"
GOG = jf.GOG


def bins():
    d = os.path.join(jf.H, "db2bins")
    os.makedirs(d, exist_ok=True)
    for src, dst in (("openmohaa.exe", "openmohaa_jf.exe"), ("omohaaded.exe", "omohaaded_jf.exe"), ("OpenAL64.dll", None),
                     ("SDL2.dll", None), ("libcurl.dll", None), ("renderer_opengl1.dll", None), ("renderer_opengl2.dll", None),
                     ("game.dll", None)):
        shutil.copyfile(os.path.join(GOG, src), os.path.join(d, dst or src))
    shutil.copyfile(CGAME, os.path.join(d, "cgame.dll"))
    log("bins", d, "cgame", jf.md5f(os.path.join(d, "cgame.dll"))[:8], "game", jf.md5f(os.path.join(d, "game.dll"))[:8])
    return d


def overlay_pak():
    p = os.path.join(SCR, "zzzzzzz_db2_overlay.pk3")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_STORED) as z:
        z.write(os.path.join(HERE, "overlay", "coop_mod", "coop_selftest_xp.scr"), "coop_mod/coop_selftest_xp.scr")
        td = os.path.join(FIXES, "textures", "hud", "coop_db2")
        for f in sorted(os.listdir(td)):
            z.write(os.path.join(td, f), "textures/hud/coop_db2/" + f)
    return p


class Recorder(threading.Thread):
    """window-content frames (harness_window capture path, JPEG) at ~fps, until stop()"""

    def __init__(self, c, out, fps=24):
        super().__init__(daemon=True)
        self.c, self.out, self.dt, self.n, self.go = c, out, 1.0 / fps, 0, True
        os.makedirs(out, exist_ok=True)

    def run(self):
        import ctypes
        from ctypes import wintypes as wt
        from PIL import Image
        u32, gdi = ctypes.WinDLL("user32"), ctypes.WinDLL("gdi32")
        t_next = time.time()
        while self.go:
            h = self.c["bg"].hwnd()
            if h:
                rc = wt.RECT()
                u32.GetClientRect(h, ctypes.byref(rc))
                w, hh = rc.right, rc.bottom
                hdc = u32.GetDC(h)
                mdc = gdi.CreateCompatibleDC(hdc)
                bmp = gdi.CreateCompatibleBitmap(hdc, w, hh)
                gdi.SelectObject(mdc, bmp)
                ok = u32.PrintWindow(h, mdc, 3)
                buf = ctypes.create_string_buffer(w * hh * 4)

                class BIH(ctypes.Structure):
                    _fields_ = [("biSize", wt.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD), ("biCompression", wt.DWORD),
                                ("biSizeImage", wt.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]
                bi = BIH(ctypes.sizeof(BIH), w, -hh, 1, 32, 0, 0, 0, 0, 0, 0)
                gdi.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.byref(bi), 0)
                gdi.DeleteObject(bmp)
                gdi.DeleteDC(mdc)
                u32.ReleaseDC(h, hdc)
                if ok and w > 0:
                    Image.frombuffer("RGBA", (w, hh), buf, "raw", "BGRA", 0, 1).convert("RGB").save(
                        os.path.join(self.out, "f%05d.jpg" % self.n), quality=92)
                    self.n += 1
            t_next += self.dt
            time.sleep(max(0.0, t_next - time.time()))

    def stop(self):
        self.go = False
        self.join(10)


def join(c, tries=2):
    for _ in range(tries):
        step(c, ["popmenu 0", "wait 10", "primarydmweapon smg", "wait 5", "join_team allies", "wait 20",
                 "popmenu 0", "wait 20"])
        time.sleep(3)


def main():
    name = sys.argv[1]
    ST["run"] = name
    ST.update({"usercfg": False, "netdebug": False, "clprobe": False, "clprobe2": False, "listen": False, "mx": {}, "ufps": 60})
    os.makedirs(SCR, exist_ok=True)
    res = [(1280, 720), (1024, 768), (1680, 720)]
    if "--res" in sys.argv:
        res = [tuple(int(v) for v in r.split("x")) for r in sys.argv[sys.argv.index("--res") + 1].split(",")]
    video = "--video" in sys.argv
    skip = "--skip" in sys.argv
    opts = {"srv": "rel", "cl": "rel", "lobby": "fix", "delay": 0, "parkbytes": None, "mx": {}, "ufps": 60,
            "listen": False, "clprobe": False, "usercfg": False}
    code, rev = jf.fix_codepak()
    b = bins()
    ov = overlay_pak()
    shm, smt = jf.seed_server(opts, code)
    shutil.copyfile(ov, os.path.join(smt, os.path.basename(ov)))
    pc = jf.seed_client(1, jf.SLOTS[0][1], code, jf.veteran_record(1000))
    shutil.copyfile(ov, os.path.join(pc[1], os.path.basename(ov)))
    cfgp = os.path.join(smt, "jf_start.cfg")
    txt = jf.read(cfgp).replace("map co_lobby1", "seta coop_st_xp 1\nset db_go x\nset sv_cheats 1\nset cheats 1\nmap co_lobby1")
    txt = txt.replace("seta developer 0", "seta developer 1").replace("seta coop_dev 0", "seta coop_dev 1")
    if "--old" in sys.argv:   # the BEFORE: every client gets the old script card
        txt = txt.replace("map co_lobby1", "set coop_debrief2 0\nmap co_lobby1")
    open(cfgp, "w", newline="\n").write(txt)
    out = os.path.join(SCR, "shots_" + name)
    os.makedirs(out, exist_ok=True)
    c = None
    slog = None
    try:
        for ri, (W, HH) in enumerate(res):
            tag = "%dx%d" % (W, HH)
            slog = jf.start_server(b, shm, smt)
            c = jf.launch_client(1, b, pc[0], fps=60, W=W, Hh=HH)
            st = len(read(slog))
            m = wait_for(slog, r"JFTester1[^\r\n]*entered the battle", 240, st)
            check("%s client entered the lobby" % tag, m)
            step(c, ["set ui_gmbox 1", "set coop_hudFadeTime 999", "set coop_debrief2Debug 1"])
            time.sleep(8)
            cl0 = len(read(c["log"]))
            step(c, ["set rconPassword " + jf.RCON, "rcon map m1l1"])
            m = wait_for(c["log"], r"Server: m1l1", 150, cl0)
            check("%s moved into m1l1" % tag, m)
            time.sleep(15)
            join(c)
            time.sleep(4)
            step(c, ["god", "notarget", "set coop_hudFadeTime 999", "set cg_drawviewmodel 1"])
            time.sleep(2)
            st = len(read(slog))
            cst = len(read(c["log"]))
            rec = None
            step(c, ["set rconPassword " + jf.RCON, "rcon set db_go " + ("2" if "--big" in sys.argv else "1")])
            # click into the battle until the staging script reports a live player (an intro cinematic can eat the first join)
            for _ in range(30):
                if re.search(r"DB2T active", read(slog)[st:]):
                    break
                step(c, ["popmenu 0", "join_team allies", "wait 10", "+attackprimary", "wait 20", "-attackprimary"])
                time.sleep(3)
            check("%s player active" % tag, re.search(r"DB2T active", read(slog)[st:]))
            # the staging takes a few seconds (real unlock + award paths), then xp_summary waits 0.5 s before the card
            m = wait_for(slog, r"DB2 sent[^\r\n]*" if "--old" not in sys.argv else r"DB2 capable[^\r\n]*", 90, st)
            check("%s debrief sent: %s" % (tag, m.group(0)[:200] if m else "-"), m)
            if video and ri == 0:
                rec = Recorder(c, os.path.join(out, "frames_" + tag))
                rec.start()
            if "--old" in sys.argv:
                time.sleep(3)
            else:
                m = wait_for(c["log"], r"DB2 phase 2 ", 20, cst)
                check("%s client started the sequence" % tag, m)
            t0 = time.time()
            marks = [(2.0, "a_bar"), (4.2, "b_rankup"), (9.0, "c_tally"), (11.6, "d_card1"), (14.6, "e_card2"), (23.6, "f_card5"), (33.5, "g_summary")]
            if skip:
                marks = [(1.2, "a_bar"), (1.6, "SKIP_SPACE"), (2.6, "b_skipped_bar"), (4.0, "SKIP_USE"), (4.8, "c_skipped_tally"), (6.0, "SKIP_USE"), (6.8, "d_next_card")]
            for at, nm in marks:
                time.sleep(max(0.0, at - (time.time() - t0)))
                if nm.startswith("SKIP"):
                    c["bg"].post_key(0x20 if nm == "SKIP_SPACE" else 0x46)   # SPACE = +moveup, F = +use (pristine binds)
                    log("posted", nm)
                    continue
                if rec is not None:
                    continue    # the frame sequence covers it; engine screenshots would stall the recording
                p = os.path.join(out, "%s_%s.jpg" % (tag, nm))
                c["bg"].capture_png(p.replace(".jpg", ".png"))
                log("still", p)
            if rec is not None:
                time.sleep(max(0.0, 38.0 - (time.time() - t0)))
                rec.stop()
                log("frames", rec.n)
            time.sleep(4)
            jf.stop_client(c)
            c = None
            jf.stop_server()
            time.sleep(4)
        errs = re.findall(r"[^\r\n]*(?:Script Error|Couldn't compile|parse error)[^\r\n]*", read(slog))
        check("0 script errors in the server log", not errs, "; ".join(errs[:4]))
        for l in re.findall(r"[^\r\n]*\^~\^~\^ DB2[^\r\n]*", read(slog)):
            log("SRV", l[:400])
    except Exception as e:
        check("harness ran to the end", False, repr(e))
    finally:
        try:
            if c is not None:
                jf.stop_client(c)
        except Exception as e:
            log("client stop note", e)
        jf.stop_server()
    log("DONE ->", out, "rev", rev[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
