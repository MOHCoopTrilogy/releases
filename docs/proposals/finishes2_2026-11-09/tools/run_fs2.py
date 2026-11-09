"""finishes2 wiring: in-game stills on the PRIVATE client G:\\mohaa-finishes (never the live install). The wpnviewer harness
(wpnview_run.launch: muted, background window policy, pad script) pointed at this client; its homepath carries the v1.10.67 release
paks (hardlinks of G:\\mohaa-rc67c's read-only copies), the staging finishes pak, and an overlay with every file the finishes2 mod
branch changed. Coop on m2l1 by ui_startdmmap 2. Both test paks come off the client afterwards.
    python run_fs2.py <tag> [--res uw|1080] [--parts armory,hip,viewer,locks]
Frames -> H:\\hzm_work\\finishes2\\runs\\<tag>
"""
import argparse, os, shutil, subprocess, sys, zipfile
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
import wpnview_run as W  # noqa: E402

MODWT = r"H:\hzm_work\finishes2-mod"
FS2PAK = os.environ.get("HZM_FS2_PAK", r"H:\hzm_work\finishes2_build\zzzzzzzzzz_coop_finishes_hd.pk3")
W.CLIENT = r"G:\mohaa-finishes"
W.HOME = os.path.join(W.CLIENT, "home")
W.MAINTT = os.path.join(W.HOME, "maintt")
W.LOG = os.path.join(W.MAINTT, "qconsole.log")
W.SHOTS = os.path.join(W.MAINTT, "screenshots")
W.RUNS = r"H:\hzm_work\finishes2\runs"
W.RES.update({"uw": (3440, 1440, 0), "1080": (1920, 1080, 0)})
OV = "zzzzzzzzzzzzzzzzzzzzz_fs2_code.pk3"
_ap = W.hw.apply_policy


def _cheats(args, *a, **k):
    args2, late = _ap(args, *a, **k)
    return list(args2[:-2]) + ["+set", "cheats", "1"] + list(args2[-2:]) if args2[-2] == "+exec" else list(args2) + ["+set", "cheats", "1"], late


W.hw.apply_policy = _cheats


def overlay():
    p = os.path.join(W.MAINTT, OV)
    st = subprocess.run(["git", "-C", MODWT, "diff", "--name-only", "hotfix-1.10.53"], capture_output=True, text=True).stdout
    st += subprocess.run(["git", "-C", MODWT, "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True).stdout
    n = 0
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        for ln in sorted(set(st.splitlines())):
            rel = ln.strip().strip('"')
            f = os.path.join(MODWT, *rel.split("/"))
            if os.path.isfile(f) and not rel.lower().endswith(".pk3"):
                z.write(f, rel)
                n += 1
    shutil.copyfile(FS2PAK, os.path.join(W.MAINTT, os.path.basename(FS2PAK)))
    W.log("overlay %d files, finishes pak %.0f MB" % (n, os.path.getsize(FS2PAK) / 1e6))
    return [p, os.path.join(W.MAINTT, os.path.basename(FS2PAK))]


VIEWER = [("e061", "kar98_splitter"), ("e634", "mp40_telo"), ("e1177", "colt_whitewash"), ("e589", "thompson_battleworn"),
          ("e068", "kar98_parade")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--res", default="1080")
    ap.add_argument("--parts", default="armory,hip,viewer")
    ap.add_argument("--viewer", default="")
    a = ap.parse_args()
    parts = a.parts.split(",")
    os.makedirs(os.path.join(W.MAINTT, "configs"), exist_ok=True)
    made = overlay()
    s = W.Script()
    sh = lambda nm, dt=500: s.cmd("screenshotJPEG %s" % nm, dt)  # noqa: E731
    try:
        s.cmd("echo ^~^~^ FS2 boot", int(os.environ.get("FS_BOOT", "45000")))
        s.cmd("+attack", 300)
        s.cmd("-attack", 7000)
        s.cmd("+right", 600)
        s.cmd("-right", 900)
        s.cmd("exec ui/loadout/w03_s1.cfg", 4000)
        s.cmd("exec ui/loadout/w26_s2.cfg", 4000)
        s.cmd("exec ui/loadout/w48_s3.cfg", 5000)
        if "armory" in parts:
            s.cmd("exec ui/loadout/open.cfg", 3500)
            s.cmd("exec ui/loadout/s1sel.cfg", 3000)
            sh("arm_01_slot1")
            for f, nm in ((44, "splinter"), (51, "parade"), (49, "battleworn"), (50, "trenchart"), (42, "kriegsmarine")):
                s.cmd("exec ui/loadout/fin%d_s1.cfg" % f, 3000)
                sh("arm_02_%s" % nm)
            s.cmd("exec ui/loadout/s2sel.cfg", 3000)
            s.cmd("exec ui/loadout/fin47_s2.cfg", 3000)
            sh("arm_03_mp40_amoeba")
            s.cmd("exec ui/loadout/s4sel.cfg", 2500)
            sh("arm_04_nade_slot")
            s.cmd("exec ui/loadout/done.cfg", 3000)
        if "hip" in parts:
            for slot, f, name, nm in ((1, 44, "Mauser KAR 98K (Splinter)", "kar98_splitter"), (2, 47, "MP40 (Amoeba)", "mp40_amoeba"),
                                      (3, 40, "Colt 45 (Whitewash)", "colt_whitewash"), (1, 50, "Mauser KAR 98K (Trench Art)", "kar98_trench"),
                                      (2, 52, "MP40 (Captured)", "mp40_captured"), (1, 49, "Mauser KAR 98K (Battle-worn)", "kar98_bw")):
                s.cmd("exec ui/loadout/fin%d_s%d.cfg" % (f, slot), 5500)
                s.cmd('use "%s"' % name, 2500)
                sh("hip_%s" % nm, 400)
                s.cmd("+left", 150)
                s.cmd("-left", 700)
                sh("hip_%s_turn" % nm, 400)
                s.cmd("+right", 150)
                s.cmd("-right", 500)
            s.cmd("echo ^~^~^ FS2 weapons", 100)
        if "locks" in parts:
            s.cmd("set coop_lockLoadout 1", 300)
            s.cmd("exec ui/loadout/w05_s1.cfg", 5000)
            s.cmd("exec ui/loadout/open.cfg", 3500)
            s.cmd("exec ui/loadout/s1sel.cfg", 3000)
            sh("lock_01_slot1")
            s.cmd("exec ui/loadout/fdeny44.cfg", 1500)
            sh("lock_02_deny_splinter")
            s.cmd("exec ui/loadout/done.cfg", 1500)
        if "viewer" in parts:
            s.cmd("disconnect", 6000)
            s.cmd("exec ui/hzm_attic_go_rack.cfg", 3000)
            vl = [v.split(":") for v in a.viewer.split(",") if v] or VIEWER
            for e, nm in vl:
                s.cmd("exec ui/wpnview/%s.cfg" % e, 1200)
                sh("view_%s" % nm, 400)
                s.cmd("set ui_wvSpin 200", 900)
                sh("view_%s_left" % nm, 400)
                s.cmd("set ui_wvSpin 0", 300)
        s.cmd("quit", 0)
        W.launch(a.tag, a.res, s, lines=['seta coop_lo2 ""', 'seta coop_loA2 ""', 'seta coop_loFA1 ""', 'seta coop_loFA2 ""', 'seta coop_loFA3 ""',
                                         "set g_gametype 2", "set cheats 1", "set coop_dev 1",
                                         "set s_volume 0", "set s_musicvolume 0", "set s_ambientvolume 0",
                                         "set coop_lockLoadout 0", "set ui_dmmap %s" % os.environ.get("FS_MAP", "m2l1"), "ui_startdmmap 2"],
                 budget=int(os.environ.get("FS_BUDGET", "420")))
    finally:
        for p in made:
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    main()
