#!/usr/bin/env python3
"""mapclips_test.py - in-game check of the map-zoom loading clips (gen_mapclips.py) on a PRIVATE client.

    python -P -E mapclips_test.py <pak> <run_dir> map [map ...]

Client: G:\\mohaa-mapclips70 (byte copies of the byo70-eng build; basepath = the GOG tree read-only, home inside the folder,
        so harness_guard classifies it HARNESS). The pak under test is copied into that home under the shipped name, so it
        beats the basepath copy. Own-disc maps need the player's converted paks in that home (local only, never committed).
Started ONLY by harness_window.launch_background (guard + job, never focused), muted (s_volume 0 and the coop tinnitus
cvars 0 after autoexec), in_mouse 0, in_nograb 1, in_gamepad 0, in_joystick 0; keys are posted to OUR window only.
While the user's own game runs the client goes to the 1080p DISPLAY2, otherwise to the harness's test display.
Each map: `set ui_dmmap <map>; exec coop_mod/start_server.cfg` (F7), window captures through the load, and the engine's
^~^~^ LOADCINE lines from qconsole.log. Any guard violation stops the run."""
import json, os, re, shutil, sys, time

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_guard as hg      # noqa: E402
import harness_window as hw     # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
SLOT = r"G:\mohaa-mapclips70"
HOME = os.path.join(SLOT, "home")
MT = os.path.join(HOME, "maintt")
LOG = os.path.join(MT, "qconsole.log")
F7 = 0x76
BOOT = ["set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0", "set in_gamepad 0", "set in_joystick 0",
        "set in_mouse 0", "set in_nograb 1", "set com_maxfps 60", "set coop_joinCard 0", "set cl_loadCinematic 1",
        "set coop_tinnitusBaseVol 0", "set coop_tinnitusMuffle 0", "set coop_woundMuffleVol 0",
        "set coop_campaignNext \"\"", 'bind F7 "exec mc_go.cfg"']


def read():
    try:
        return open(LOG, "rb").read().decode("latin-1")
    except OSError:
        return ""


def main():
    pak, run, maps = sys.argv[1], sys.argv[2], sys.argv[3:]
    os.makedirs(run, exist_ok=True)
    if hg.slot_holder("mapclips70"):
        raise SystemExit("slot busy")
    disp = hw.test_display(r"\\.\DISPLAY2") if hg.user_game_running_raw() else hw.test_display()
    print("test display", disp["device"], disp["rect"], flush=True)
    shutil.copyfile(pak, os.path.join(MT, "zzzzzzzzzz_coop_mapclips.pk3"))
    if os.path.exists(LOG):
        os.remove(LOG)
    W, H = 1280, 720
    sets = [("com_target_game", "2"), ("fs_basepath", GOG), ("fs_homepath", HOME), ("cl_renderer", "opengl2"),
            ("r_mode", "-1"), ("r_customwidth", str(W)), ("r_customheight", str(H)), ("r_fullscreen", "0"),
            ("developer", "0"), ("logfile", "2"), ("in_gamepad", "0"), ("in_joystick", "0"), ("in_mouse", "0"),
            ("in_nograb", "1"), ("s_volume", "0"), ("g_gametype", "2"), ("net_port", "12793"), ("name", "MapClipQA")]
    args = [os.path.join(SLOT, "openmohaa.exe")]
    for k, v in sets:
        args += ["+set", k, v]
    args += ["+exec", "mc_on.cfg"]
    args, late = hw.apply_policy(args, width=W, height=H, display=disp)
    open(os.path.join(MT, "mc_on.cfg"), "w", newline="\n").write("\n".join(BOOT + late) + "\n")
    res = {"display": disp["device"], "maps": {}}
    c = hw.launch_background(args[0], args[1:], SLOT, policy=False, display=disp, below_normal=True, watch_audio=True,
                             log=lambda *a: None)
    with c:
        t0 = time.time()
        while time.time() - t0 < 120 and not c.hwnd():
            time.sleep(1)
        time.sleep(15)                                   # the main menu up
        for m in maps:
            if c.watcher.violations:
                break
            open(os.path.join(MT, "mc_go.cfg"), "w", newline="\n").write(
                "set coop_tinnitusBaseVol 0\nset coop_tinnitusMuffle 0\nset coop_woundMuffleVol 0\n"
                "set ui_dmmap %s\nexec coop_mod/start_server.cfg\n" % m)
            n = len(read())
            c.post_key(F7)
            out = os.path.join(run, m)
            os.makedirs(out, exist_ok=True)
            ts = time.time()
            shots = 0
            while time.time() - ts < 90:                 # captures through the load (the clip is 4.6 s, then held)
                if c.watcher.violations:
                    break
                tail = read()[n:]
                c.capture_png(os.path.join(out, "g%03d_%05.2f.png" % (shots, time.time() - ts)))
                shots += 1
                if "Spawning Entities Done" in tail or re.search(r"LOADDRAW[^\n]*end=end", tail):
                    break
                time.sleep(0.25)
            time.sleep(6)
            tail = read()[n:]
            res["maps"][m] = {"loadcine": re.findall(r"\^~\^~\^ (LOADCINE[^\r\n]*)", tail)[:6], "shots": shots,
                              "spawned": "Spawning Entities Done" in tail,
                              "script_errors": len(re.findall("Script Error", tail))}
            print(m, json.dumps(res["maps"][m]), flush=True)
        res["violations"] = c.watcher.violations
    shutil.copyfile(LOG, os.path.join(run, "qconsole.log"))
    json.dump(res, open(os.path.join(run, "result.json"), "w"), indent=1, default=str)
    print("violations", res["violations"])


if __name__ == "__main__":
    main()
