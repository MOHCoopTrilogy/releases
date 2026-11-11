#!/usr/bin/env python3
"""tf_nade_run.py - v1.10.72 user report: holding G does not cook a grenade. [trainfix 2026-11-10]
Dedicated server (coop_quickNadeCook 0 = shipped / 1 = fixed, set on the command line) + one background client. Real input:
the harness HOLDS the G key on our window (post_key down_ms) through the client's own bind g "+coopnade"; maps/tf_nade.scr
(testthread) times the torso charge and the thrown projectile's life. Cases: tap (0.06 s), hold 2.5 s, hold 6.5 s (overcook).
    python tf_nade_run.py [shipped|fixed] ...
"""
import os, re, shutil, sys, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "tools"))
import at_test as AT  # noqa: E402
H = os.path.join(AT.A, "home")
VK_G = 0x47
CASES = [("tap", 60), ("hold2.5", 2500), ("hold6.5", 6500)]


def paks():
    for home in (H, AT.SRVHOME):
        mt = os.path.join(home, "maintt")
        os.makedirs(mt, exist_ok=True)
        for fn in os.listdir(mt):
            if fn.lower().endswith(".pk3"):
                os.remove(os.path.join(mt, fn))
        with zipfile.ZipFile(os.path.join(mt, "zzzzzzzzzzzzzzzzzzzzzzzz_tfnade.pk3"), "w", zipfile.ZIP_STORED) as z:
            z.write(os.path.join(HERE, "tf_nade.scr"), "maps/tf_nade.scr")


def run(variant):
    out = os.path.join(AT.RUNS, "tfnade_" + variant)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    paks()
    cook = "1" if variant == "fixed" else "0"
    srv = AT.server([("coop_advTraining", "0"), ("coop_dbno", "0"), ("g_inactiveSpectate", "0"), ("g_inactivekick", "0"),
                     ("coop_quickNadeCook", cook)], "m4l0")
    SL = AT.lp(AT.SRVHOME)
    res = {"variant": variant, "coop_quickNadeCook": cook, "cases": {}}
    try:
        res["loaded"] = AT.wait_for(SL, r"Spawning Entities Done", 300)
        binds = ['bind g "+coopnade"', 'bind F10 "testthread maps/tf_nade.scr watch"']
        c = AT.client(AT.A, H, [("cheats", "1")], ["+connect", "127.0.0.1:%d" % AT.PORT], binds, "TF_Alpha")
        with c:
            res["joined"] = AT.join_until(c, SL, "TF_Alpha", 400)
            time.sleep(8)
            for tag, ms in CASES:
                n = len(AT.read(SL))
                c.post_key(AT.VK["F10"])
                time.sleep(1.0)
                c.post_key(VK_G, down_ms=ms)
                AT.wait_for(SL, r"TFNADE (fuse_after_throw|player_dead|timeout)", 20, n)
                res["cases"][tag] = re.findall(r"TFNADE [^\r\n]*", AT.read(SL)[n:])
                if AT.guard(c):
                    break
                time.sleep(6)       # respawn after the overcook / clear the field
                c.post_key(AT.VK["F9"])
                time.sleep(4)
    finally:
        if srv.poll() is None:
            srv.kill()
    shutil.copyfile(SL, os.path.join(out, "server_qconsole.log"))
    res["tripped"] = AT.TRIPPED
    return res


def run_station():
    """[trainfix] the grenade pit itself (course position 9, no self-test): a TAP and a 2.5 s HOLD of G at the real station;
    the station's projectile watch must credit the throw and the cooked row"""
    import at_test as T2
    out = os.path.join(AT.RUNS, "tfnade_station")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    T2.build_pak()
    # a listen host (the course's own launch path; the dedicated single-client boot stalled in waitForPlayer)
    for fn in os.listdir(os.path.join(H, "maintt")):
        if fn.lower().endswith(".pk3") and "advtrain" not in fn:
            os.remove(os.path.join(H, "maintt", fn))
    c = AT.go_listen(H, ["set coop_advTraining 1", "set coop_atStation 9", "set coop_atTimeout 600", "set coop_dbno 0",
                         "set coop_quickNadeCook 1"], "TF_Alpha", binds=['bind g "+coopnade"'])
    SL = AT.lp(H)
    res = {"case": "station"}
    with c:
        res["loaded"] = AT.wait_for(SL, r"Spawning Entities Done", 300)
        res["joined"] = AT.join_until(c, SL, "TF_Alpha", 400)
        res["station"] = AT.wait_for(SL, r"ATRAIN station st=4", 180)
        time.sleep(12)
        for ms in (60, 2500):
            c.post_key(VK_G, down_ms=ms)
            time.sleep(7)
        AT.shoot(c, out, "pit")
        AT.guard(c)
    log = AT.read(SL)
    shutil.copyfile(SL, os.path.join(out, "server_qconsole.log"))
    res["lines"] = [l.strip()[30:] for l in log.splitlines() if "ATRAIN grenade" in l or "ATRAIN row st=4" in l]
    res["tripped"] = AT.TRIPPED
    return res


def main():
    if sys.argv[1:] == ["station"]:
        print(run_station(), flush=True)
        return 1 if AT.TRIPPED else 0
    for v in (sys.argv[1:] or ["shipped", "fixed"]):
        print(v, run(v), flush=True)
        if AT.TRIPPED:
            print("GUARD TRIPPED - stop")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
