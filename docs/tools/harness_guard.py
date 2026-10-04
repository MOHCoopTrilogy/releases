#!/usr/bin/env python3
"""harness_guard.py - shared guard for every agent harness that launches a private game client on this machine.

Why (renderer_reinit vet H4/H7, bug-3062): harnesses told "the user's game is running" apart from their own client by
IMAGE NAME (openmohaa.exe = the user). A private copy that must be named openmohaa.exe (the NVIDIA driver treats the
name specially, bug-3062) would then kill itself, and would stop every other harness. So processes are classified by
EXECUTABLE PATH + command line, and the one shared private-client slot is a lock file.

  USER      an openmohaa*.exe whose path is the live install (G:\\mohaa-gl2) or the GOG root, or any openmohaa*.exe
            that no registered harness owns (unknown = assume the user, never touch it)
  HARNESS   an openmohaa*.exe under a registered harness folder whose command line carries that harness's homepath
  SERVER    omohaaded*.exe (soak / test dedicated servers)

Library use:
    import harness_guard as hg
    hg.classify()                      -> list of dicts {pid, name, path, cls, owner, created}
    hg.user_game_running()             -> [pids] (USER class only)
    hg.acquire_slot("rkeep", exe, home, ports, minutes)   atomic; raises SlotBusy
    hg.release_slot("rkeep")
    hg.window                          -> the harness_window module (background test-window policy, below)
    hg.launch_background(exe, args, cwd, env=None, log=print)   -> BackgroundClient (context manager)

BACKGROUND WINDOW POLICY (docs/proposals/test_window_policy_2026-09-27/README.md): every private client is launched
through harness_window.launch_background ONLY (there is no attach-after-launch path; hold() was removed): on DISPLAY2,
never activated (SDL_WINDOW_NO_ACTIVATION_WHEN_SHOWN=1 + the in-process WH_CBT guard harness_cbt/hzm_cbt.dll that
creates the window on DISPLAY2 and refuses every activation, bug-3147), no console window, muted, mouse off, in a job
object, with a watchdog that KILLS the client on any foreground/placement/mouse-capture violation and hands the
foreground back. No SendInput / ClipCursor / desktop grabs; the only SetForegroundWindow is that hand-back.
CLI:
    python harness_guard.py status     prints every client/server process with its class, and the slot holder
    python harness_guard.py window     prints the displays and the chosen test display
"""
import json, os, subprocess, sys, time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import harness_window as window  # noqa: E402
from harness_window import launch_background, apply_policy, popen_kwargs, test_display  # noqa: E402,F401

USER_EXES = [r"G:\mohaa-gl2\openmohaa.exe", r"G:\GOG\Medal of Honor - Allied Assault War Chest\openmohaa.exe"]
# registered harness folders -> owner name and the homepath marker its launches carry on the command line
HARNESSES = {
    r"G:\mohaa-gfxtest": {"owner": "gfx/shared", "home": r"G:\mohaa-gl2\home_test"},
    r"G:\mohaa-keeptest": {"owner": "rkeep", "home": r"G:\mohaa-gl2\home_keep"},
    # bug-3076 rank-bar promotion capture: a copy of the LIVE exe + DLLs (the user's exact build set)
    r"G:\mohaa-rankbar": {"owner": "rankbar", "home": r"G:\mohaa-rankbar\home"},
    # fog/LOD in-engine gates (docs/proposals/fog_lod_pop_2026-09-27): v1.10.3 candidate set + a live-set copy in \live
    r"G:\mohaa-fogtest": {"owner": "fog", "home": r"G:\mohaa-fogtest\home"},
    # defect-sweep runtime checks on the v1.10.3 candidate set (scratchpad v1103\bin), queue slot "sweep"
    r"G:\mohaa-sweep": {"owner": "sweep", "home": r"G:\mohaa-sweep\home"},
    # ragdoll Phase 0.5+1 in-engine A/B on the v1.10.3 candidate set (scratchpad v1103\bin), queue slot "ragdoll"
    r"G:\mohaa-ragtest": {"owner": "ragdoll", "home": r"G:\mohaa-ragtest\home"},
    # water + wet surfaces in-engine comparison on the v1.10.3 candidate set (docs/proposals/water_wetness_2026-09-27),
    # queue slot "waterwet"
    r"G:\mohaa-wwtest": {"owner": "waterwet", "home": r"G:\mohaa-wwtest\home"},
    # volumetric clouds P1/P2 in-engine gates (docs/proposals/volumetric_clouds_2026-09-26, docs/tools/vcl/vcl_run.py):
    # a copy of the LIVE exe + DLLs plus the test renderer_opengl2vcl*.dll, queue slot "clouds"
    r"G:\mohaa-vcltest": {"owner": "clouds", "home": r"G:\mohaa-vcltest\home"},
    # README media: loading-screen medal morph + hint strip captured with the engine `screenshot` (v1.10.2 live set
    # copied from G:\mohaa-rc1102), queue slot "medal"
    r"G:\mohaa-medal": {"owner": "medal", "home": r"G:\mohaa-medal\home"},
    # storm darkness in-engine gates + GIFs (docs/proposals/storm_darkness_2026-09-28): v1103d set + the storm cgame/gl2
    # built in openmohaa-hzm-storm, queue slot "storm"
    r"G:\mohaa-stormtest": {"owner": "storm", "home": r"G:\mohaa-stormtest\home"},
    # dust storm frequency + moonlit night storms (docs/proposals/duststorm_2026-09-28): a copy of the LIVE v1.10.2 set
    # (exe 2fdfbc36, cgame a6139549, game d7843cab, gl2 5f2ead5f) + a test overlay pk3 in the home, queue slot "dust".
    # Its headless omohaaded (scratchpad dust\ded, port 12497, home C:\mohaa-coop-dev\server_home_dust2) classifies as SERVER.
    r"G:\mohaa-dusttest": {"owner": "dust", "home": r"G:\mohaa-dusttest\home"},
    # loadout double-give + slow-server icon (docs/proposals/loadout_slowserver_2026-09-28): HEADLESS - a private
    # omohaaded copied from the LIVE set (omohaaded c7195698, game d7843cab) in scratchpad loadout\ded, net_port 12641,
    # sv_gamespy 0, homes scratchpad loadout\home_*, below-normal priority, CREATE_NO_WINDOW. Classifies as SERVER.
    # A client capture, if the coordinator grants it, uses this folder and queue slot "loadout".
    r"G:\mohaa-lotest": {"owner": "loadout", "home": r"G:\mohaa-lotest\home"},
    # defect sweep #2 (docs/proposals/defect_sweep2_2026-09-28): HEADLESS ONLY - a private omohaaded copied from the
    # LIVE set (game d7843cab) in scratchpad sweep2\ded, net_port 12611, sv_gamespy 0, homes scratchpad sweep2\home_*,
    # below-normal priority, CREATE_NO_WINDOW. Classifies as SERVER; no client folder, no slot.
    # square foliage shadows (docs/proposals/foliage_shadows_2026-09-28): a copy of the LIVE set (gl2 5f2ead5f) + a
    # camera-only test overlay pk3 in the home, queue slot "fshadow"
    r"G:\mohaa-fshadow": {"owner": "fshadow", "home": r"G:\mohaa-fshadow\home"},
    # StG 44 viewmodel pop before/after (docs/proposals/stg44_viewmodel_2026-09-28, bug-3207): the v1.10.3 RC set from
    # G:\mohaa-rc1103 + two TEST cgames (probe only / probe + fix) built in openmohaa-hzm-stg44; basepath = the GOG
    # root (read only) + a test overlay pk3 in the home, queue slot "stg44"
    r"G:\mohaa-stg44": {"owner": "stg44", "home": r"G:\mohaa-stg44\home"},
    # Breakthrough loading-screen art (docs/proposals/bt_loadscreens_2026-09-28): a copy of the LIVE set (exe 2fdfbc36,
    # gl2 5f2ead5f) + a staging/camera test overlay pk3 in the home, queue slot "loadart"
    r"G:\mohaa-loadart": {"owner": "loadart", "home": r"G:\mohaa-loadart\home"},
    # m3l3 rock clips (docs/proposals/m3l3_rocks_2026-09-28): HEADLESS ONLY - private omohaaded copies of the LIVE set
    # (scratchpad m3l3rocks\ded: omohaaded c7195698 + game d7843cab), net_port 12531-12533, homes
    # C:\mohaa-coop-dev\server_home_m3l3rocks_<variant>, below-normal priority, CREATE_NO_WINDOW. Classifies as SERVER;
    # a client capture, if ever needed, would use this folder and queue slot "m3l3rocks".
    r"G:\mohaa-m3l3rocks": {"owner": "m3l3rocks", "home": r"G:\mohaa-m3l3rocks\home"},
    # remastered main-menu room (docs/proposals/menu_redesign_2026-09-28/remaster_test/ingame/mr_client.py): a copy of
    # the LIVE set + the staged room overlay pk3 in the home, main menu only (no map, no server), queue slot "menuroom"
    r"G:\mohaa-menuroom": {"owner": "menuroom", "home": r"G:\mohaa-menuroom\home"},
    # menu-system remaster Phase 3 (docs/proposals/menu_system_remaster_2026-09-29/phase3/ingame/ms_client.py): a copy of
    # the LIVE DLL set + the E1-E4 test exe (openmohaa.exe, built in openmohaa-hzm-menusys) and the live exe
    # (openmohaa_live.exe, the baseline) + test overlay pk3s in the home; main menu only (no map, no server), slot "menusys"
    r"G:\mohaa-menusys": {"owner": "menusys", "home": r"G:\mohaa-menusys\home"},
    # briefing slides for joiners (docs/proposals/briefing_joiners_2026-09-28/tools/brtest.py): a copy of the LIVE set
    # (exe 2fdfbc36, cgame a6139549, game d7843cab, gl2 5f2ead5f); its headless omohaaded (scratchpad briefing\ded,
    # port 12651, homes scratchpad briefing\home_*) classifies as SERVER; the client joins it, queue slot "briefing"
    r"G:\mohaa-brieftest": {"owner": "briefing", "home": r"G:\mohaa-brieftest\home"},
    # coop mission-tile art (docs/proposals/mission_tile_art_2026-09-29/staging/tileart_run.py): a copy of the LIVE
    # binaries (exe 90e47187, cgame 0a0bb3b4), fresh home (no qkey/saves copied), basepath = the GOG tree read-only,
    # the loadart staging overlay + a localization test file in the home, net_port 12530, queue slot "tileart"
    r"G:\mohaa-tileart": {"owner": "tileart", "home": r"G:\mohaa-tileart\home"},
    # ground variety prototype (docs/proposals/ground_variety_2026-09-29/tools/gv_ingame.py): a copy of the LIVE
    # binaries (exe 90e47187, cgame 0a0bb3b4, gl2 11df592f) + the test renderer_opengl2gv.dll built in
    # openmohaa-hzm-antitile, fresh home (no qkey/saves copied), basepath = the GOG tree read-only, a camera/list
    # overlay pk3 in the home, net_port 12545, queue slot "groundvar"
    r"G:\mohaa-groundvar": {"owner": "groundvar", "home": r"G:\mohaa-groundvar\home"},
    # coop start screen DEDICATED option (docs/proposals/dedicated_launch_2026-10-04/tools/ded_test.py): the exe built in
    # openmohaa-hzm-dedicated + byte copies of the LIVE DLLs and omohaaded.exe (read from G:\mohaa-gl2, never written),
    # fresh home (no qkey/saves copied), basepath = the GOG tree read-only, a mod overlay pk3 in the home, net_ip
    # 127.0.0.1, client net_port 12203; the omohaaded.exe the CLIENT launches runs from this folder with this home
    # (ports 12204-12212), so it classifies as HARNESS. Queue slot "dedicated"
    r"G:\mohaa-dedtest": {"owner": "dedicated", "home": r"G:\mohaa-dedtest\home"},
    # reload variety prototype (docs/proposals/reload_variety_2026-09-29/tools/run_reloadvar.py): byte copies of the
    # LIVE exe/game/renderers (read from G:\mohaa-gl2, never written) + the test cgame built in
    # openmohaa-hzm-reloadvar, fresh home (no qkey/saves copied), basepath = the GOG tree read-only, a harness-hook
    # overlay pk3 in the home, net_ip 127.0.0.1, net_port 12547, queue slot "reloadvar"
    r"G:\mohaa-reloadvar": {"owner": "reloadvar", "home": r"G:\mohaa-reloadvar\home"},
    # m3l2 ground before/after (docs/proposals/m3l2_ground_2026-09-29/tools/m3l2g_ingame.py): byte copies of the LIVE
    # exe/cgame/game/renderers (read from G:\mohaa-gl2, never written), fresh home (no qkey/saves copied), basepath = the
    # GOG tree read-only, the staged zzzzzzzzzz_coop_m3l2ground.pk3 + a camera overlay pk3 in the home, net_ip
    # 127.0.0.1, net_port 12549, queue slot "m3l2ground"
    r"G:\mohaa-m3l2ground": {"owner": "m3l2ground", "home": r"G:\mohaa-m3l2ground\home"},
    # anti-tank supply points (scratchpad atsupply/atsupply_ingame.py): byte copies of the LIVE exe/cgame/game/renderers
    # (read from G:\mohaa-gl2, never written), fresh home (no qkey/saves copied), basepath = the GOG tree read-only, the
    # working-tree code pk3 in the home, net_ip 127.0.0.1, net_port 12293, queue slot "atsupply"
    r"G:\mohaa-atsupply": {"owner": "atsupply", "home": r"G:\mohaa-atsupply\home"},
    # paratrooper squad brain + .30 cal (docs/proposals/smart_paratroopers_2026-10-04, scratchpad paras/paras_ingame.py):
    # byte copies of the G:\mohaa-atsupply binaries (game 54b10f3b = LIVE), fresh home, basepath = the GOG tree read
    # only, the working-tree code pk3 + a probe overlay in the home, net_ip 127.0.0.1, net_port 12371, queue slot "paras"
    r"G:\mohaa-paras": {"owner": "paras", "home": r"G:\mohaa-paras\home"},
    # server frame time on m1l1 (docs/proposals/server_perf_m1l1_2026-09-29/tools/srvperf.py): HEADLESS - private
    # omohaaded copies of the LIVE v1.10.3 set (scratchpad srvperf\ded_ship: game b044385b; srvperf\ded_prof: the
    # instrumented game.dll built in the isolated copy openmohaa-hzm-srvperf), bots as players, net_ip 127.0.0.1,
    # net_port 12661, sv_gamespy 0, homes scratchpad srvperf\home_*, below-normal priority, CREATE_NO_WINDOW. Classifies
    # as SERVER. A listen-host client check, if run, uses this folder and queue slot "srvperf".
    r"G:\mohaa-srvperf": {"owner": "srvperf", "home": r"G:\mohaa-srvperf\home"},
    # menu-system remaster Phase 3 (docs/proposals/menu_system_remaster_2026-09-29/ingame/ms_client.py): byte copies of
    # the LIVE DLLs (read from G:\mohaa-gl2, never written) + the E1/E2 test openmohaa.exe built in
    # openmohaa-hzm-menusys, fresh home (no qkey/saves copied), basepath = the GOG tree read-only, the staged theme
    # overlay pk3 in the home, menus only (no map, no server), net_ip 127.0.0.1, queue slot "menusys"
    r"G:\mohaa-menusys": {"owner": "menusys", "home": r"G:\mohaa-menusys\home"},
    # green crosshair / numpad binds (docs/proposals/crosshair_toggle_2026-09-29/tools/xh_test.py, bug-3298): byte
    # copies of the LIVE v1.10.3 binaries (read from G:\mohaa-gl2, never written), fresh home seeded from the repo's
    # installer/omconfig_default.cfg (no qkey/saves/user config copied), basepath = the GOG tree read-only, the staged
    # cfg/menu overlay pk3 in the home, listen host on m1l2a, net_ip 127.0.0.1, net_port 12573, queue slot "crosshair"
    r"G:\mohaa-crosshair": {"owner": "crosshair", "home": r"G:\mohaa-crosshair\home"},
    # in-game Report a Bug parity (docs/proposals/bugreport_parity_2026-09-29/tools/br_ingame_test.py, bug-3278): the
    # isolated openmohaa-hzm-bugreport exe + byte copies of the LIVE cgame/game/renderers (read from G:\mohaa-gl2, never
    # written), fresh home seeded from installer/omconfig_default.cfg (no qkey/saves/user config), basepath = the GOG tree
    # read-only, overlay pk3 with the new report menus in the home, listen host on m1l1, net_ip 127.0.0.1, net_port 12591,
    # DRY RUN / loopback sink only (never Discord), queue slot "bugreport"
    r"G:\mohaa-bugreport": {"owner": "bugreport", "home": r"G:\mohaa-bugreport\home"},
    # weapon view: ironsights close-out + pistol ADS kick + hands during ADS (docs/proposals/weaponview_2026-10-04/tools/
    # run_wv.py, reusing the ironsights harness): byte copies of the LIVE v1.10.9 exe/game/renderers (read from
    # G:\mohaa-gl2, never written) + the test cgame built in the isolated copy openmohaa-hzm-weaponview, own home
    # (self-generated qkey, coop_loA* blanked), basepath = the GOG tree read-only, test overlay pk3 in the home,
    # net_ip 127.0.0.1, net_port 12534, queue slot "weaponview"
    r"G:\mohaa-ironsight": {"owner": "weaponview", "home": r"G:\mohaa-ironsight\home"},
    # aimed reload/bolt clips pilot (docs/proposals/ads_anims_2026-10-04/tools/run_adsanim.py, reusing the ironsights
    # harness): byte copies of the G:\mohaa-ironsight exe/game/renderers (themselves copies of the LIVE v1.10.9 set) + the
    # test cgame built in the isolated copy openmohaa-hzm-adsanim, own fresh home (no qkey/saves copied), basepath = the
    # GOG tree read-only, test overlay pk3 in the home, net_ip 127.0.0.1, net_port 12538, queue slot "adsanim"
    r"G:\mohaa-adsanim": {"owner": "adsanim", "home": r"G:\mohaa-adsanim\home"},
    # bugsweep 2026-10-04 (prone eye ease bug-3317, AI tik identity gear, deaths while physics_off): byte copies of
    # the LIVE v1.10.11 exe/renderers (read from G:\mohaa-gl2, never written) + game.dll/cgame built in the isolated
    # copy openmohaa-hzm-bugsweep, fresh home from G:\mohaa-adsanim\pristine (no qkey/saves), basepath = the GOG tree
    # read-only, test overlay pk3 in the home, net_ip 127.0.0.1, net_port 12542, queue slot "bugsweep"
    r"G:\mohaa-bugsweep": {"owner": "bugsweep", "home": r"G:\mohaa-bugsweep\home"},
}
SLOT = os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\Public"), "hzm_harness", "client_slot.json")


class SlotBusy(Exception):
    pass


def _norm(p):
    return os.path.normcase(os.path.normpath(p or ""))


def processes():
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'openmohaa*.exe' -or $_.Name -like 'omohaaded*.exe' }"
          " | Select-Object ProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Compress")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.strip()
    if not out:
        return []
    j = json.loads(out)
    return j if isinstance(j, list) else [j]


def classify():
    res = []
    users = {_norm(p) for p in USER_EXES}
    for p in processes():
        path = _norm(p.get("ExecutablePath"))
        cmd = p.get("CommandLine") or ""
        name = (p.get("Name") or "").lower()
        rec = {"pid": p["ProcessId"], "name": name, "path": p.get("ExecutablePath"), "created": str(p.get("CreationDate")),
               "cls": "USER", "owner": None}
        if name.startswith("omohaaded"):
            rec["cls"] = "SERVER"
        elif path in users:
            rec["cls"] = "USER"
        else:
            for folder, h in HARNESSES.items():
                if path.startswith(_norm(folder) + os.sep) and _norm(h["home"]) in _norm(cmd.replace('"', "")):
                    rec["cls"], rec["owner"] = "HARNESS", h["owner"]
                    break
        res.append(rec)
    return res


def user_game_running():
    return [r["pid"] for r in classify() if r["cls"] == "USER"]


def slot_holder():
    try:
        s = json.load(open(SLOT))
    except (OSError, ValueError):
        return None
    alive = s.get("pid") is None or any(r["pid"] == s.get("pid") for r in classify())
    if time.time() > s.get("expires", 0) or (s.get("pid") is not None and not alive):
        return None
    return s


def acquire_slot(owner, exe, home, ports, minutes=60):
    os.makedirs(os.path.dirname(SLOT), exist_ok=True)
    cur = slot_holder()
    if cur and cur.get("owner") != owner:
        raise SlotBusy("client slot held by %s until %s" % (cur.get("owner"), time.ctime(cur.get("expires", 0))))
    rec = {"owner": owner, "exe": exe, "home": home, "ports": ports, "pid": None, "since": time.time(),
           "expires": time.time() + minutes * 60}
    tmp = SLOT + ".%d.tmp" % os.getpid()
    json.dump(rec, open(tmp, "w"), indent=1)
    os.replace(tmp, SLOT)
    return rec


def set_slot_pid(owner, pid):
    s = json.load(open(SLOT))
    if s.get("owner") != owner:
        raise SlotBusy("slot is not ours")
    s["pid"] = pid
    json.dump(s, open(SLOT, "w"), indent=1)


def release_slot(owner):
    try:
        s = json.load(open(SLOT))
    except (OSError, ValueError):
        return
    if s.get("owner") == owner:
        os.remove(SLOT)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        for r in classify():
            print("%-7s %-8s pid=%-6s %s owner=%s" % (r["cls"], r["name"], r["pid"], r["path"], r["owner"]))
        print("slot:", slot_holder())
    elif len(sys.argv) > 1 and sys.argv[1] == "window":
        for m in window.monitors():
            print(m)
        print("test display:", test_display()["device"])
    else:
        print(__doc__)
