#!/usr/bin/env python3
"""ops_sweep.py - Live Operations Phase 0 (PLAN.md section 6): does each candidate contract map run bots?

One DEDICATED server at a time (quiet testing), headless: harness_window.popen_kwargs() = CREATE_NO_WINDOW, below-normal
priority, no window is ever created or activated. Private install G:\\mohaa-liveops (byte copies of the engine binaries),
basepath = the GOG tree read-only, homepath = H:\\hzm_work\\liveops-test\\srvhome. Only the PID this script started is stopped.

    python ops_sweep.py [--secs 150] [--only dm/mohdm3,...] [--pak <test pk3 to drop into the home>]

Per map: nav built (no "No bots, skipping navigation"), bots in game (MPBOT lines + "entered"), kills (obituary lines),
Script Errors, Couldn't compile. Writes H:\\hzm_work\\liveops-test\\sweep.json (+ each log under runs\\sweep_<map>.log)."""
import json, os, re, shutil, subprocess, sys, time

sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
import harness_window as hw  # noqa: E402

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
INST = r"G:\mohaa-liveops"
HOME = r"H:\hzm_work\liveops-test\srvhome"
RUNS = r"H:\hzm_work\liveops-test\runs"
PORT = 12291
POOL = [("dm/mohdm3", 2), ("dm/mohdm6", 2), ("dm/mohdm7", 2), ("dm/mp_brest_dm", 2), ("dm/mp_malta_dm", 2),
        ("obj/mp_berlin_tow", 2), ("obj/mp_montecassino_tow", 2), ("obj/mp_bologna_obj", 2),
        ("obj/obj_team3", 4), ("obj/mp_bologna_obj", 4), ("obj/mp_palermo_obj", 4), ("obj/mp_bizertefort_obj", 4),
        ("obj/obj_team1", 4), ("obj/obj_team2", 4), ("obj/obj_team4", 4), ("obj/mp_castello_obj", 4)]
KILL = re.compile(r"\] \S+ (was (shot|killed|gunned|blown|machine|sniped|clubbed|bashed|pummeled|torn|perforated|mowed|riddled|"
                  r"cut|knocked|bitten|hit|blasted|caught|shredded|nailed|put)|blew himself|took himself|pumped full|ate |tripped)", re.I)


def opt(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def run(mp, gt, secs, extra):
    mt = os.path.join(HOME, "maintt")
    os.makedirs(mt, exist_ok=True)
    lp = os.path.join(mt, "qconsole.log")
    if os.path.exists(lp):
        os.remove(lp)
    open(os.path.join(mt, "sweep.cfg"), "w", newline="\n").write("\n".join([
        "set developer 1", "set sv_maxbots 12", "set sv_numbots 0", "set coop_mpBotFill 10", "set coop_mpBotMax 12",
        "set coop_mpMode none", "set timelimit 0", "set fraglimit 0", "set g_teamdamage 0", "set sv_minPlayers 0"] + extra +
        ["map " + mp]) + "\n")
    args = [os.path.join(INST, "omohaaded.exe"), "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "fs_homepath", HOME, "+set", "dedicated", "1", "+set", "net_port", str(PORT), "+set", "sv_maxclients", "4",
            "+set", "g_gametype", str(gt), "+set", "logfile", "2", "+set", "com_abnormalExit", "0", "+set", "sv_maxbots", "12",
            "+set", "developer", "1", "+exec", "sweep.cfg"]
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
    tag = mp.replace("/", "_") + "_gt%d" % gt
    open(os.path.join(RUNS, "sweep_%s.log" % tag), "w", encoding="latin-1").write(log)
    r = {"map": mp, "gt": gt, "loaded": "Spawning Entities Done" in log or "CM_LoadMap" in log,
         "nonav": "No bots, skipping navigation" in log, "nav": bool(re.search(r"(?i)navigation|navmesh|recast", log)),
         "bots_target": max([int(x) for x in re.findall(r"desiredBots=(\d+)", log)] or [0]),
         "entered": len(re.findall(r"entered the battle|has joined the", log, re.I)),
         "kills": len([l for l in log.splitlines() if KILL.search(l)]),
         "script_errors": log.count("Script Error"), "compile": log.count("Couldn't compile"),
         "cantfind": "Can't find map" in log, "crash": p.returncode not in (None, 0, 1) and "Server: " not in log[-4000:]}
    return r


def main():
    secs = int(opt("--secs", "150"))
    only = opt("--only", "")
    pool = [x for x in POOL if not only or x[0] in only.split(",")]
    pak = opt("--pak", "")
    mt = os.path.join(HOME, "maintt")
    os.makedirs(mt, exist_ok=True)
    for fn in os.listdir(mt):
        if fn.startswith("zzzzzzzzzzzzzzzzzzzzzz_liveops"):
            os.remove(os.path.join(mt, fn))
    if pak:
        shutil.copyfile(pak, os.path.join(mt, os.path.basename(pak)))
    os.makedirs(RUNS, exist_ok=True)
    out = os.path.join(r"H:\hzm_work\liveops-test", "sweep.json")
    res = json.load(open(out)) if os.path.exists(out) and "--fresh" not in sys.argv else {}
    for mp, gt in pool:
        r = run(mp, gt, secs, [])
        res["%s gt%d" % (mp, gt)] = r
        print(json.dumps(r), flush=True)
        json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
