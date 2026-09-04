#!/usr/bin/env python
"""
check_map_compiles.py - boot a headless server and prove the map's scripts actually COMPILE.

WHY THIS EXISTS
    [2026-09-02, bug-2335] A bazooka team was added to m3l1a using `vectortoangles`. The real command
    is `vector_toangles`. An unknown command is a COMPILE error in Morpheus, and a compile error takes
    down the WHOLE FILE - so coopified.scr did not load at all and every coop system on Omaha silently
    vanished. The map still booted, still played, and looked like the mod had simply stopped working.

    Every static gate passed it:
        depthscan2.py       - braces balanced, so OK
        scrlint.py          - no BOM, no em-dash, no bad quote, so OK
        check_map_anims.py  - every anim and sound resolves, so OK
    None of them knows the command vocabulary, and none of them ever can without reimplementing the
    engine's parser. Only the engine can answer "does this compile", and it answers in one line:

        Script Error : Script 'maps/m3l1a/coopified.scr' was not properly loaded

    This runs a dedicated server for a few seconds and looks for exactly that. It is the cheapest
    possible test for the most expensive possible failure - a map that ships with no script.

    It also checks for a POSITIVE marker, because "no error" is not the same as "it ran": a file that
    fails to load prints the error once per call site, but a file that loads and then early-outs prints
    nothing at all. coopified.scr prints `^~^~^ OBSTACLES loaded=` from its init, so its absence is
    just as damning as the error's presence.

USAGE
    python docs/tools/check_map_compiles.py [--map m3l1a] [--seconds 60]
Exit 1 if the script did not compile, or if the map never booted.
"""
import os, re, subprocess, sys, time

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
HOME = r"C:\mohaa-coop-dev\server_home"
EXE = os.path.join(GOG, "omohaaded.exe")
LOG = os.path.join(HOME, "maintt", "qconsole.log")

# a marker each map's coop script prints from its own init, proving the file both loaded AND ran
MARKERS = {
    "m3l1a": "OBSTACLES loaded",
}


def main():
    mapname = sys.argv[sys.argv.index("--map") + 1] if "--map" in sys.argv else "m3l1a"
    secs = int(sys.argv[sys.argv.index("--seconds") + 1]) if "--seconds" in sys.argv else 60

    if not os.path.exists(EXE):
        print("  omohaaded.exe not found - skipping the compile check")
        return 0

    try:
        open(LOG, "w").close()
    except Exception:
        pass

    args = [EXE,
            "+set", "com_target_game", "2", "+set", "fs_basepath", GOG,
            "+set", "dedicated", "1", "+set", "fs_homepath", HOME,
            "+set", "net_port", "12203", "+set", "sv_maxclients", "8",
            "+set", "g_gametype", "2", "+set", "logfile", "2",
            "+set", "developer", "1", "+set", "com_abnormalExit", "0",
            "+map", mapname]
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(secs)
    crashed = p.poll()
    try:
        p.kill()
    except Exception:
        pass

    txt = ""
    try:
        txt = open(LOG, encoding="latin-1", errors="replace").read()
    except Exception:
        pass

    bad = len(re.findall(r"was not properly loaded", txt))
    errs = len(re.findall(r"Script Error", txt))
    marker = MARKERS.get(mapname)
    ran = (marker in txt) if marker else True

    print("  %s: compile errors %d, script errors %d, init marker %s"
          % (mapname, bad, errs, "present" if ran else "MISSING"))

    if crashed is not None and crashed != 0:
        print("  *** the server EXITED with code %s - this is a crash, not a script problem" % crashed)
        return 1
    if bad:
        print("  *** THE SCRIPT DID NOT COMPILE. The map would ship with no coop script at all.")
        print("  *** Static gates cannot see this: look for an unknown command or a bad expression.")
        for ln in [l for l in txt.splitlines() if "not properly loaded" in l][:2]:
            print("      " + ln.strip()[:150])
        return 1
    if not ran:
        print("  *** the script compiled but its init marker never printed - it loaded and did nothing.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
