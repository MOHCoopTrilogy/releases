#!/usr/bin/env python3
"""mapclips_test.py - in-game check of the map-zoom loading clips (gen_mapclips.py) on a PRIVATE client.

    python -P -E mapclips_test.py <pak> <run_dir> map [map ...] [--nocap] [--size WxH] [--exe NAME]
        map@0 / map@1  that load with cl_loadCinematic 0 / 1 (default 1); map@1@0 = also cl_loadCineThread 0 (A/B)
        --nocap        no window captures (a load-time bench: PrintWindow during a load costs load time itself)

Client: G:\\mohaa-mapclipshd (MAPCLIPS_SLOT; the release DLLs + the exe under test, --exe; basepath = the GOG tree read-only, home inside the folder,
        so harness_guard classifies it HARNESS). The pak under test is copied into that home under the shipped name, so it
        beats the basepath copy. Own-disc maps need the player's converted paks in that home (local only, never committed).
Started ONLY by harness_window.launch_background (guard + job, never focused), muted (s_volume 0 and the coop tinnitus
cvars 0 after autoexec), in_mouse 0, in_nograb 1, in_gamepad 0, in_joystick 0; keys are posted to OUR window only.
While the user's own game runs the client goes to the 1080p DISPLAY2, otherwise to the harness's test display.
Each load: `set ui_dmmap <map>; exec coop_mod/start_server.cfg` (F7); per load it records the engine's ^~^~^ LOADCINE lines,
the LOADDRAW load time (cl_loadProbe 1) and the client's peak private bytes / working set. Any guard violation stops the run."""
import json, os, re, shutil, sys, time

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg      # noqa: E402
import harness_window as hw     # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
SLOT = os.environ.get("MAPCLIPS_SLOT", r"G:\mohaa-mapclipshd")
HOME = os.path.join(SLOT, "home")
MT = os.path.join(HOME, "maintt")
LOG = os.path.join(MT, "qconsole.log")
F7 = 0x76
BOOT = ["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0",
        "set in_mouse 0", "set in_nograb 1", "set com_maxfps 60", "set coop_joinCard 0", "set cl_loadCinematic 1",
        "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0",
        'set coop_campaignNext ""', "set cl_loadProbe 1", 'bind F7 "exec mc_go.cfg"']


def read():
    try:
        return open(LOG, "rb").read().decode("latin-1")
    except OSError:
        return ""


def mem(pid):
    """(private MB, working set MB) of the client (GetProcessMemoryInfo)"""
    import ctypes
    from ctypes import wintypes as wt

    class PMC(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]
    k = ctypes.WinDLL("kernel32")
    ps = ctypes.WinDLL("psapi")
    k.OpenProcess.restype = wt.HANDLE
    h = k.OpenProcess(0x1000 | 0x0010, False, pid)
    pmc = PMC()
    pmc.cb = ctypes.sizeof(pmc)
    try:
        ps.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
    finally:
        k.CloseHandle(h)
    return pmc.PrivateUsage / 1048576.0, pmc.WorkingSetSize / 1048576.0


def main():
    argv = sys.argv[1:]
    nocap = "--nocap" in argv
    W, H = 1280, 720
    if "--size" in argv:
        i = argv.index("--size")
        W, H = (int(v) for v in argv[i + 1].split("x"))
        del argv[i:i + 2]
    exe = "openmohaa.exe"
    if "--exe" in argv:
        i = argv.index("--exe")
        exe = argv[i + 1]
        del argv[i:i + 2]
    argv = [a for a in argv if a != "--nocap"]
    pak, run, maps = argv[0], argv[1], argv[2:]
    os.makedirs(run, exist_ok=True)
    disp = hw.test_display(r"\\.\DISPLAY2") if hg.user_game_running_raw() else hw.test_display()
    print("test display", disp["device"], disp["rect"], "window", W, H, flush=True)
    shutil.copyfile(pak, os.path.join(MT, "zzzzzzzzzz_coop_mapclips.pk3"))
    if os.path.exists(LOG):
        os.remove(LOG)
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"),
            ("developer", "0"), ("logfile", "2"), ("in_gamepad", "0"), ("in_joystick", "0"), ("in_mouse", "0"),
            ("in_nograb", "1"), ("s_volume", "0"), ("g_gametype", "2"), ("net_port", "12793"), ("name", "MapClipQA")]
    args = [os.path.join(SLOT, exe)]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "mc_on.cfg"]
    args, late = hw.apply_policy(args, width=W, height=H, display=disp)
    open(os.path.join(MT, "mc_on.cfg"), "w", newline="\n").write("\n".join(BOOT + late) + "\n")
    res = {"display": disp["device"], "window": [W, H], "pak": pak, "loads": {}}
    c = hw.launch_background(args[0], args[1:], SLOT, policy=False, display=disp, below_normal=True, watch_audio=True,
                             log=lambda *a: None)
    with c:
        t0 = time.time()
        while time.time() - t0 < 120 and not c.hwnd():
            time.sleep(1)
        time.sleep(15)                                   # the main menu up
        for li, mm in enumerate(maps):
            if c.watcher.violations:
                break
            m, on, thr = (mm.split("@") + ["1", "1"])[:3]       # map[@cinematic[@decode thread]]
            key = "%02d_%s_%s%s" % (li, m, on, "" if mm.count("@") < 2 else "_t" + thr)
            open(os.path.join(MT, "mc_go.cfg"), "w", newline="\n").write(
                "set coop_tinnitusBaseVol 0\nset coop_tinnitusMuffle 0\nset coop_woundMuffleVol 0\nset cl_loadCineThread %s\n"
                "set cl_loadCinematic %s\nset ui_dmmap %s\nexec coop_mod/start_server.cfg\n" % (thr, on, m))
            n = len(read())
            c.post_key(F7)
            t_k = time.time()
            while time.time() - t_k < 30 and m not in read()[n:]:   # the menu may not take the first key (still loading)
                time.sleep(1)
            if m not in read()[n:]:
                c.post_key(F7)
            out = os.path.join(run, key)
            if not nocap:
                os.makedirs(out, exist_ok=True)
            ts = time.time()
            shots = 0
            pk = [0.0, 0.0]
            while time.time() - ts < 120:                # through the load (the clip is 4.6 s, then held)
                if c.watcher.violations:
                    break
                tail = read()[n:]
                try:
                    pv, ws = mem(c.proc.pid)
                    pk = [max(pk[0], pv), max(pk[1], ws)]
                except Exception:
                    pass
                if not nocap:
                    c.capture_png(os.path.join(out, "g%03d_%05.2f.png" % (shots, time.time() - ts)))
                shots += 1
                if re.search(r"LOADDRAW[^\n]*end=end", tail):
                    break
                time.sleep(0.25)
            time.sleep(8)
            tail = read()[n:]
            ld = re.search(r"\^~\^~\^ LOADDRAW map=\S+ path=\S+ end=\S+ ms=(\d+)", tail)
            res["loads"][key] = {"loadcine": re.findall(r"\^~\^~\^ (LOADCINE[^\r\n]*)", tail)[:6], "shots": shots,
                                 "load_ms": int(ld.group(1)) if ld else None, "peak_private_mb": round(pk[0]),
                                 "peak_ws_mb": round(pk[1]), "script_errors": len(re.findall("Script Error", tail))}
            print(key, json.dumps(res["loads"][key]), flush=True)
        res["violations"] = c.watcher.violations
    shutil.copyfile(LOG, os.path.join(run, "qconsole.log"))
    json.dump(res, open(os.path.join(run, "result.json"), "w"), indent=1, default=str)
    print("violations", res["violations"])


if __name__ == "__main__":
    main()
