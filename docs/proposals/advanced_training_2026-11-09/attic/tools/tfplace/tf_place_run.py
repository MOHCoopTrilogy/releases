#!/usr/bin/env python3
"""tf_place_run.py - v1.10.72 user report: sandbags fall under the map (Advanced Training). [trainfix 2026-11-10]
For each map x {shipped, fixed}: a dedicated server (cheats on the command line) + one background client; the client runs
the REAL coop_mod/cover.scr::cover_place and ammobox.scr::ammobox_place where it spawns (testthread maps/tf_place.scr place),
then stands inside its own bag and requests cover (tf_place.scr cover). Stills with the HUD off; the server log carries
^~^~^ TFPLACE lines (bag / crate origin vs the feet, coop_incover).
    python tf_place_run.py [map ...]      default: m4l0 m3l2 m2l1
fixed = + an override pk3 with the trainfix cover.scr / ammobox.scr; both variants carry maps/tf_place.scr (test only).
"""
import os, re, shutil, sys, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools"))
import at_test as AT  # noqa: E402

MOD = r"H:\hzm_work\trainfix-mod"
H = os.path.join(AT.A, "home")


def paks(variant):
    for home in (H, AT.SRVHOME):
        mt = os.path.join(home, "maintt")
        os.makedirs(mt, exist_ok=True)
        for fn in os.listdir(mt):
            if fn.lower().endswith(".pk3"):
                os.remove(os.path.join(mt, fn))
        with zipfile.ZipFile(os.path.join(mt, "zzzzzzzzzzzzzzzzzzzzzzzz_tfplace.pk3"), "w", zipfile.ZIP_STORED) as z:
            z.write(os.path.join(HERE, "tf_place.scr"), "maps/tf_place.scr")
            if variant == "fixed":
                for f in ("coop_mod/cover.scr", "coop_mod/ammobox.scr"):
                    z.write(os.path.join(MOD, f), f)


def run(mapname, variant):
    out = os.path.join(AT.RUNS, "tfplace_%s_%s" % (mapname, variant))
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    paks(variant)
    srv = AT.server([("coop_advTraining", "0"), ("coop_dbno", "0"), ("g_inactiveSpectate", "0"), ("g_inactivekick", "0")], mapname)
    SL = AT.lp(AT.SRVHOME)
    res = {"map": mapname, "variant": variant}
    try:
        res["loaded"] = AT.wait_for(SL, r"Spawning Entities Done", 300)
        binds = ['bind F10 "testthread maps/tf_place.scr place"', 'bind F11 "testthread maps/tf_place.scr cover"']
        c = AT.client(AT.A, H, [("cheats", "1")], ["+connect", "127.0.0.1:%d" % AT.PORT], binds, "TF_Alpha")
        with c:
            res["joined"] = AT.join_until(c, SL, "TF_Alpha", 400)
            time.sleep(8)
            n = len(AT.read(SL))
            c.post_key(AT.VK["F10"])
            res["placed"] = AT.wait_for(SL, r"TFPLACE crate|TFPLACE bag NONE", 25, n)
            time.sleep(2)
            c.post_key(AT.VK["F6"]); time.sleep(1)
            AT.shoot(c, out, "placed")
            c.post_key(AT.VK["F7"])
            c.post_key(AT.VK["F11"])
            AT.wait_for(SL, r"TFPLACE cover", 15, n)
            time.sleep(1)
            AT.shoot(c, out, "in_cover")
            AT.guard(c)
    finally:
        if srv.poll() is None:
            srv.kill()
    log = AT.read(SL)
    shutil.copyfile(SL, os.path.join(out, "server_qconsole.log"))
    res["tfplace"] = [l.strip()[30:] for l in log.splitlines() if "TFPLACE" in l]
    res["compile"] = AT.errors(log)["compile"]
    res["tripped"] = AT.TRIPPED
    return res


def main():
    maps = sys.argv[1:] or ["m4l0", "m3l2", "m2l1"]
    for m in maps:
        for v in ("shipped", "fixed"):
            print(m, v, run(m, v), flush=True)
            if AT.TRIPPED:
                print("GUARD TRIPPED - stop")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
