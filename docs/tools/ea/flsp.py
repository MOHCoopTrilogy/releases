#!/usr/bin/env python3
"""Single-player (g_gametype 0) real-input run of a converted Frontline level. Our own code.

The private client loads the map with +map under g_gametype 0. coop_fltest 3 parks the player a few
steps short of each objective, facing it; this script then holds W (forward) and taps F (use) through
PostMessage to OUR window only - the player walks in and presses use himself. Passes when all five
objectives are done and global/missioncomplete runs its single-player branch (next map loads).
Muted, controller off, test display, only our own PID is stopped.
usage: flsp.py <map> <outdir>"""
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flharness as fh          # noqa: E402

T = {"fl": "FL", "ea": "EA"}[os.environ.get("HZM_GAME", "fl")]      # HZM_GAME=ea: the EA pilot
TAGS = tuple(T + x for x in ("ASSIST", "USE trigger", "OBJ", "CUE", "SET", "MISSION", "TANK", "CHARGE", "MUSIC")) + ("Script Error",)


def main(mapname, out):
    os.makedirs(out, exist_ok=True)
    fh.hg.acquire_slot(fh.OWNER, fh.EXE, fh.HOME, [fh.PORT], minutes=30)
    try:
        c = fh.launch(mapname, "opengl2", False, 1100, 620, gametype="0",
                      extra_sets=["set coop_%stest 3" % T.lower(), "set coop_%stestPlayers 1" % T.lower()])
        with c:
            if not fh.wait_log(r"Spawning Entities Done|" + T + "AI", 300):
                raise RuntimeError("map never loaded")
            n0 = 0
            # close any start-up menu (a first-run card on a fresh home sat on top of the map: bug-10681)
            time.sleep(8)
            fh.step(["popmenu 0", "wait 5", "popmenu 0", "wait 5", "popmenu 0"], timeout=60)
            # god only once the player is really in (the map's kit line); sent earlier it did not stick (SP death)
            fh.wait_log(T + "KIT given|" + T + "AI", 120)
            time.sleep(3)
            fh.step(["god", "wait 5", "god"] if False else ["god"], timeout=60)   # god: the flow test parks the player beside live squads; SP death = mission failed (2026-11-09)
            t0, k = time.time(), 0
            while time.time() - t0 < 900:
                if c.proc.poll() is not None:      # the client is gone: stop instead of posting keys for 15 min
                    break
                log = fh.read_log()
                if (T + "MISSION complete") in log:
                    n0 = len(log)
                    break
                c.post_key(0x57, down_ms=700)
                c.post_key(0x46, down_ms=80)
                if k % 4 == 0:
                    try:
                        c.capture_png(os.path.join(out, "sp_%03d.png" % k))
                    except Exception:
                        pass
                k += 1
                time.sleep(5)
            # missioncomplete SP branch: give it time to fade and load the next level
            t1 = time.time()
            while n0 and time.time() - t1 < 90:
                tail = fh.read_log()[n0:]
                if re.search(r"Spawning Entities Done|-+ Server Initialization|------ Server Shutdown", tail):
                    break
                time.sleep(3)
            time.sleep(5)
            try:
                c.capture_png(os.path.join(out, "sp_end.png"))
            except Exception:
                pass
            shutil.copyfile(fh.LOG, os.path.join(out, "qconsole.log"))
    finally:
        fh.hg.release_slot(fh.OWNER)
    log = open(os.path.join(out, "qconsole.log"), "rb").read().decode("latin-1")
    for tag in TAGS:
        hits = re.findall(r"\^~\^~\^ " + tag + r"[^\n]*", log)
        print(tag, len(hits), [h.strip() for h in hits[-6:]])
    i = log.find(T + "MISSION complete")
    after = log[i:] if i >= 0 else ""
    print("after-mission:", [ln.strip() for ln in after.splitlines()
                             if re.search(r"Server Shutdown|Server Initialization|Spawning Entities Done|missioncomplete|map ", ln)][:8])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
