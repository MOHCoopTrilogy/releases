"""In-game stills of a new gun on the PRIVATE client G:\\mohaa-newguns (never the live install): the wpnviewer harness
(wpnview_run.launch: muted, background window policy, pad script) pointed at this client, with an overlay pk3 in its homepath:
this worktree's new wpnfix files (mkov.py) + the mod worktree's changed script files. Coop on m2l1 by ui_startdmmap 2.
    python run_gun.py <tag> --gun <tik>=<gun name> [--gun ...] [--res uw|1080|720]
Frames: hip, hip fire, ADS, ADS fire, reload x3, ADS reload, third person -> H:\\hzm_work\\newguns\\runs\\<tag>
"""
import os, sys, zipfile, argparse, subprocess
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
import wpnview_run as W  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MODWT = r"H:\hzm_work\newguns-mod"
SCRIPTS = ["coop_mod/player_torso.st", "coop_mod/loadoutroster.scr", "coop_mod/challenges.scr", "coop_mod/itemhandler.scr", "global/giveall.scr", "ubermode/get_player_weaponclass.scr", "coop_mod/player_legs.st", "coop_mod/weaponstate.scr", "coop_mod/panzerfaust.scr", "coop_mod/keyitems.scr"]          # mod-worktree files the test needs (changed on the newguns branch)
W.CLIENT = r"G:\mohaa-newguns"
W.HOME = os.path.join(W.CLIENT, "home")
W.MAINTT = os.path.join(W.HOME, "maintt")
W.LOG = os.path.join(W.MAINTT, "qconsole.log")
W.SHOTS = os.path.join(W.MAINTT, "screenshots")
W.RUNS = r"H:\hzm_work\newguns\runs"
W.RES.update({"uw": (3440, 1440, 0)})
OV = "zzzzzzzzzzzzzzzzzzzz_newguns_test.pk3"
_ap = W.hw.apply_policy


def _cheats(args, *a, **k):
    """`give` needs cheats set on the COMMAND LINE (a cfg `set cheats 1` only applies after a restart - fg42hd README)"""
    args2, late = _ap(args, *a, **k)
    return list(args2[:-2]) + ["+set", "cheats", "1"] + list(args2[-2:]) if args2[-2] == "+exec" else list(args2) + ["+set", "cheats", "1"], late


W.hw.apply_policy = _cheats


def overlay():
    tmp = os.path.join(W.MAINTT, OV)
    subprocess.check_call([sys.executable, os.path.join(HERE, "mkov.py"), tmp + ".tmp"])
    with zipfile.ZipFile(tmp + ".tmp") as a, zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:
        for n in a.namelist():
            z.writestr(n, a.read(n))
        # every file the newguns mod branch changed or added (state files, scripts, the Armory / viewer pages)
        # [ng5] committed changes too: everything that differs from the branch point (git status alone went empty after a commit)
        st = subprocess.run(["git", "-C", MODWT, "diff", "--name-only", "hotfix-1.10.53"], capture_output=True, text=True).stdout
        st += subprocess.run(["git", "-C", MODWT, "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True).stdout
        for ln in st.splitlines():
            rel = ln.strip().strip('"')
            p = os.path.join(MODWT, *rel.split("/"))
            if os.path.isfile(p) and not rel.lower().endswith(".pk3"):
                z.write(p, rel)
    os.remove(tmp + ".tmp")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag"); ap.add_argument("--gun", action="append", required=True, help="armoryid=name, repeatable")
    ap.add_argument("--res", default="1080"); ap.add_argument("--adsvar", action="append", default=[])
    a = ap.parse_args()
    os.makedirs(os.path.join(W.MAINTT, "configs"), exist_ok=True)
    overlay()
    s = W.Script()
    s.cmd("echo ^~^~^ NG boot", int(os.environ.get("NG_BOOT", "40000")))
    s.cmd("+attack", 300)
    s.cmd("-attack", 7000)
    turn = int(os.environ.get("NG_TURN_MS", "600"))          # m2l1's spawn view is backlit: turn toward the light for the stills
    if turn:
        s.cmd("+right" if turn > 0 else "+left", abs(turn))
        s.cmd("-right" if turn > 0 else "-left", 900)
    for gi, g in enumerate(a.gun):
        gid, name = g.split("=", 1)
        k = "g%d" % gi
        # the Armory route (run_fg42.py): commit the gun to slot 1, the loadout applies live; `give` needs server cheats
        s.cmd("exec ui/loadout/w%s_s1.cfg" % gid, 5000)
        s.cmd('use "%s"' % name, 3000)
        s.cmd("screenshotJPEG %s_01_hip" % k, 400)
        if "panzerfaust" in name.lower() or gid == "84":      # single shot: aim BEFORE the one round is spent
            s.cmd("+button13", 1500)
            s.cmd("screenshotJPEG %s_03_ads_prefire" % k, 400)
            s.cmd("-button13", 1200)
        s.cmd("+attack", 600)
        s.cmd("screenshotJPEG %s_02_hipfire" % k, 100)
        s.cmd("-attack", 1500)
        s.cmd("+button13", 1500)
        s.cmd("screenshotJPEG %s_03_ads" % k, 400)
        for vi, v in enumerate(a.adsvar if gi == 0 else []):     # live ADS variants on the first gun (cvar commands)
            s.cmd(v, 900)
            s.cmd("screenshotJPEG %s_03_ads_v%d" % (k, vi), 300)
        s.cmd("+attack", 500)
        s.cmd("screenshotJPEG %s_04_adsfire" % k, 100)
        s.cmd("-attack", 800)
        s.cmd("-button13", 1200)
        s.cmd("reload", 700)
        for i in range(6):
            s.cmd("screenshotJPEG %s_05_reload_%d" % (k, i), 450)
        s.cmd("wait 1", 2500)
        s.cmd("+button13", 1500)
        s.cmd("reload", 700)
        for i in range(4):
            s.cmd("screenshotJPEG %s_06_adsreload_%d" % (k, i), 500)
        s.cmd("-button13", 2500)
        s.cmd("cg_3rd_person 1", 1500)
        s.cmd("screenshotJPEG %s_07_third" % k, 400)
        s.cmd("cg_3rd_person 0", 600)
        s.cmd("wait 1", 1500)
        s.cmd("screenshotJPEG %s_08_after" % k, 300)
    s.cmd("quit", 0)
    W.launch(a.tag, a.res, s, lines=['seta coop_lo2 ""', 'seta coop_loA2 ""', "set g_gametype 2", "set cheats 1", "set coop_dev 1",
                                     "set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0",
                                     "set coop_lockLoadout 0", "set cg_adsSightDebug 1", "set coop_fireDebug 1", "set ui_dmmap %s" % os.environ.get("NG_MAP", "m2l1"), "ui_startdmmap 2"], budget=120 + 45 * len(a.gun))


if __name__ == "__main__":
    main()
