#!/usr/bin/env python3
"""lib_sweep.py - the LIBERATION map pool: which installed MP maps can hold a solo hunt against bots?

One DEDICATED server at a time, headless (harness_window.popen_kwargs(): CREATE_NO_WINDOW, below-normal priority; no window
is ever created or activated). Private install G:\\mohaa-lib (byte copies of the LIVE binaries), basepath = the GOG tree
read-only, homepath G:\\mohaa-lib\\home_ded (logs copied to H:\\hzm_work\\liberacion\\runs). Only the PID started here is stopped.

    python lib_sweep.py fight  [--secs 150] [--only a,b] [--fresh]     phase A: TEAM MATCH, 10 bots - nav built, bots move + kill
    python lib_sweep.py place  [--secs 100] [--only a,b] [--pak P]      phase B: the Liberation script in its dedicated test mode
                                                                          (ui_opsLibTest 1): Germans placed against a stand-in
                                                                          player spot, grounded / unseen / pathed, then tracked
Results: H:\\hzm_work\\liberacion\\sweep_fight.json, sweep_place.json."""
import json, os, re, shutil, subprocess, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "tools"))   # this worktree's docs/tools
import harness_window as hw  # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
INST = r"G:\mohaa-lib"
HOME = r"G:\mohaa-lib\home_ded"
OUT = r"H:\hzm_work\liberacion"
RUNS = os.path.join(OUT, "runs")
PORT = 12951
MAPS = ["dm/mohdm1", "dm/mohdm2", "dm/mohdm3", "dm/mohdm4", "dm/mohdm5", "dm/mohdm6", "dm/mohdm7",
        "dm/mp_bahnhof_dm", "dm/mp_bazaar_dm", "dm/mp_brest_dm", "dm/mp_gewitter_dm", "dm/mp_holland_dm", "dm/mp_malta_dm",
        "dm/mp_stadt_dm", "dm/mp_unterseite_dm", "dm/mp_verschneit_dm",
        "obj/obj_team1", "obj/obj_team2", "obj/obj_team3", "obj/obj_team4",
        "obj/mp_ardennes_tow", "obj/mp_berlin_tow", "obj/mp_druckkammern_tow", "obj/mp_flughafen_tow", "obj/mp_kasserine_tow",
        "obj/mp_montebattaglia_tow", "obj/mp_montecassino_tow",
        "obj/mp_bologna_obj", "obj/mp_castello_obj", "obj/mp_palermo_obj", "obj/mp_bizertefort_obj",
        "lib/mp_anzio_lib", "lib/mp_bizerteharbor_lib", "lib/mp_ship_lib", "lib/mp_tunisia_lib"]
KILL = re.compile(r"\] \S+ (was (shot|killed|gunned|blown|machine|sniped|clubbed|bashed|pummeled|torn|perforated|mowed|riddled|"
                  r"cut|knocked|bitten|hit|blasted|caught|shredded|nailed|put)|blew himself|took himself|pumped full|ate |tripped)", re.I)
KILL2 = re.compile(r"(was (shot|killed|gunned|blown|machine-gunned|sniped|clubbed|bashed|pummeled|torn|perforated|mowed|riddled|"
                   r"cut|knocked|hit|blasted|caught|shredded|nailed|put)|blew himself|took himself|pumped full)", re.I)


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


HOLD_FILE = os.path.join(OUT, "HOLD")       # touch it (or any lane-wide hold the coordinator calls) and the sweep stops


def hold_reason():
    """checked before EVERY launch: a user game, a release / build script running, or the lane's HOLD file"""
    import harness_guard as hg
    if hg.user_game_running() or hg.user_game_running_raw():
        return "a user MOHAA client is running"
    if os.path.exists(HOLD_FILE):
        return "HOLD file present (%s)" % HOLD_FILE
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              r"Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'build\.ps1|publish_release\.ps1' }"
                              " | Measure-Object | Select-Object -ExpandProperty Count"],
                             capture_output=True, text=True, timeout=60, creationflags=0x08000000).stdout.strip()
        if out and out != "0":
            return "build.ps1 / publish_release.ps1 is running"
    except Exception as e:  # noqa: BLE001
        return "hold check failed: %r" % e
    return ""


def run(mp, gt, secs, lines, tag):
    mt = os.path.join(HOME, "maintt")
    os.makedirs(mt, exist_ok=True)
    lp = os.path.join(mt, "qconsole.log")
    if os.path.exists(lp):
        os.remove(lp)
    open(os.path.join(mt, "libsweep.cfg"), "w", newline="\n").write("\n".join(lines + ["map " + mp]) + "\n")
    args = [os.path.join(INST, "omohaaded.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", HOME, "+set", "dedicated", "1", "+set", "net_ip", "127.0.0.1", "+set", "net_port", str(PORT),
            "+set", "sv_maxclients", "4", "+set", "g_gametype", str(gt), "+set", "logfile", "2", "+set", "com_abnormalExit", "0",
            "+set", "sv_maxbots", "26", "+set", "developer", "1", "+set", "sv_gamespy", "0", "+exec", "libsweep.cfg"]
    p = subprocess.Popen(args, cwd=INST, **hw.popen_kwargs())
    t0 = time.time()
    try:
        while time.time() - t0 < secs and p.poll() is None:
            time.sleep(5)
    finally:
        if p.poll() is None:
            p.kill()
            p.wait(20)
    log = open(lp, "rb").read().decode("latin-1") if os.path.exists(lp) else ""
    os.makedirs(RUNS, exist_ok=True)
    open(os.path.join(RUNS, "%s_%s.log" % (tag, mp.replace("/", "_"))), "w", encoding="latin-1").write(log)
    return log, p.returncode


def base(log, mp, gt, rc):
    return {"map": mp, "gt": gt, "loaded": "Spawning Entities Done" in log or "CM_LoadMap" in log,
            "nonav": "No bots, skipping navigation" in log, "script_errors": log.count("Script Error"),
            "compile": log.count("Couldn't compile"), "cantfind": "Can't find map" in log,
            "crash": rc not in (None, 0, 1) and "Server: " not in log[-4000:]}


def fight(mp, secs):
    log, rc = run(mp, 2, secs, ["set developer 1", "set sv_numbots 0", "set coop_mpBotFill 10", "set coop_mpBotMax 12",
                                "set coop_mpMode none", "set timelimit 0", "set fraglimit 0", "set g_teamdamage 0",
                                "set sv_minPlayers 0", "set ui_opsLive 0"], "fight")
    r = base(log, mp, 2, rc)
    r["entered"] = len(re.findall(r"entered the battle|has joined the", log, re.I))
    r["kills"] = len([l for l in log.splitlines() if KILL.search(l)])
    return r


def place(mp, secs, n):
    # the Liberation contract as DEPLOY hands it over (ui_opsGo*), in the dedicated test mode: no human is waited for
    log, rc = run(mp, 3, secs, ["set developer 1", "set sv_numbots 0", "set coop_mpBotMax 26", "set coop_mpMode none",
                                "set timelimit 0", "set fraglimit 0", "set sv_minPlayers 0", "set ui_opsLive 1",
                                "set ui_opsPhase \"\"", "set ui_opsResult \"\"", "set ui_opsGoMap " + mp, "set ui_opsGoGt 3",
                                "set ui_opsGoMode LIB", "set ui_opsGoFill %d" % (n + 1), "set ui_opsGoSkill REGULAR",
                                "set ui_opsGoMod \"\"", "set ui_opsGoSide allies", "set ui_opsGoName \"TEST SWEEP\"",
                                "set ui_opsGoXp 250", "set ui_opsGoLimit 0", "set ui_opsLibTest 1"], "place")
    r = base(log, mp, 3, rc)
    pl = re.findall(r"\^~\^~\^ LIB place e(\d+) at \(([^)]*)\) d=(\d+) vis=(\d) ground=(\d) try=(\d+)", log)
    r["placed"] = len(pl)
    r["visible"] = sum(1 for x in pl if x[3] == "1")
    r["floating"] = sum(1 for x in pl if x[4] == "0")
    r["min_d"] = min([int(x[2]) for x in pl] or [0])
    mv = re.findall(r"\^~\^~\^ LIB track t=(\d+) alive=(\d+) moved=(\d+) mean=(\d+)", log)
    r["track"] = [(int(a), int(b), int(c), int(d)) for a, b, c, d in mv]
    m = re.search(r"\^~\^~\^ LIB ready germans=(\d+) of (\d+)", log)
    r["germans"] = (int(m.group(1)), int(m.group(2))) if m else None
    r["fail"] = re.findall(r"\^~\^~\^ LIB (?:refused|failed)[^\r\n]*", log)
    return r


def main():
    phase = sys.argv[1]
    only = opt("--only", "")
    maps = [m for m in MAPS if not only or m in only.split(",")]
    hm = os.path.join(HOME, "maintt")
    os.makedirs(hm, exist_ok=True)
    for fn in os.listdir(hm):
        if fn.endswith(".pk3"):
            os.remove(os.path.join(hm, fn))
    pak = opt("--pak", "")
    if pak:
        shutil.copyfile(pak, os.path.join(hm, os.path.basename(pak)))
    out = os.path.join(OUT, "sweep_%s.json" % phase)
    res = json.load(open(out)) if os.path.exists(out) and "--fresh" not in sys.argv else {}
    for mp in maps:
        why = hold_reason()
        if why:
            print("HOLD - not launching %s: %s" % (mp, why), flush=True)
            break
        if phase == "fight":
            r = fight(mp, int(opt("--secs", "150")))
        else:
            r = place(mp, int(opt("--secs", "100")), int(opt("--n", "16")))
        res[mp] = r
        print(json.dumps(r), flush=True)
        json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
