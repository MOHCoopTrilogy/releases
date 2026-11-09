"""finishes2 - in-game stills of the BUILT finishes pak on the private client (G:\\mohaa-wpnview only, never the live
install): the staging zzzzzzzzzz_coop_finishes_hd.pk3 plus a throwaway pak whose base tiks are the chosen finishes' variant
tiks with the base name / rank (the normal loadout gives them, the viewer shows them). One boot, three guns: hip, reload,
viewer both sides. Both paks come off the client afterwards.
    python fs2_still.py            (the caller holds the display-queue turn)
"""
import os, re, shutil, sys, zipfile

STAGE = os.path.join("H:" + os.sep, "hzm_work", "finishes2_build")
PAK = "zzzzzzzzzz_coop_finishes_hd.pk3"
OVER = "zzzzzzzzzzzzzzzzzzzzzz_fs2_over.pk3"
# (stem, finish, loadout cfg, weapon name to use, viewer entry)
SHOTS = [("kar98", "splitter", "w03_s1", "Mauser KAR 98K", "e020"),
         ("mp40", "telo", "w26_s1", "MP40", "e264"),
         ("colt45", "whitewash", "w48_s3", "Colt 45", "e486")]


def main():
    sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\wpnviewer_2026-11-04\tools")
    import wpnview_run as W
    W.RES.update({"uw": (3440, 1440, 0)})
    over = os.path.join(STAGE, OVER)
    with zipfile.ZipFile(over, 'w', zipfile.ZIP_DEFLATED) as z:
        for stem, fin, _c, _n, _e in SHOTS:
            t = open(os.path.join(STAGE, 'pak', 'models', 'weapons', '%s_fs2_%s.tik' % (stem, fin)), encoding='latin-1').read()
            # back to the base gun's own name and rank: it IS the base gun for this look test
            t = re.sub(r'(?mi)^(\s*name\s+)"([^"]+) \([^)]*\)"', r'\1"\2"', t, count=1)
            sys.path.insert(0, r"C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools")
            import vfs
            base = vfs.read('models/weapons/%s.tik' % stem).decode('latin-1')
            r = re.search(r'(?mi)^\s*rank\s+(\d+)\s+(\d+)', base)
            t = re.sub(r"(?mi)^(\s*rank\s+)\d+\s+\d+", lambda m: "%s%s %s" % (m.group(1), r.group(1), r.group(2)), t, count=1)
            z.writestr('models/weapons/%s.tik' % stem, t.encode('latin-1'))
    dsts = [os.path.join(W.MAINTT, PAK), os.path.join(W.MAINTT, OVER)]
    shutil.copyfile(os.path.join(STAGE, PAK), dsts[0])
    shutil.copyfile(over, dsts[1])
    try:
        s = W.Script()
        s.cmd("echo ^~^~^ FS boot", 85000)
        s.cmd("+attack", 300)
        s.cmd("-attack", 7000)
        for stem, fin, cfg, name, _e in SHOTS:
            s.cmd("exec ui/loadout/%s.cfg" % cfg, 6000)
            s.cmd('use "%s"' % name, 3000)
            s.cmd("screenshotJPEG fs_%s_hip" % stem, 600)
            s.cmd("reload", 900)
            s.cmd("screenshotJPEG fs_%s_reload" % stem, 500)
        s.cmd("disconnect", 6000)
        s.cmd("exec ui/hzm_attic_go_rack.cfg", 2500)
        for stem, fin, cfg, name, e in SHOTS:
            s.cmd("exec ui/wpnview/%s.cfg" % e, 900)
            s.cmd("screenshotJPEG fs_%s_viewer" % stem, 400)
            s.cmd("set ui_wvSpin 200", 700)
            s.cmd("screenshotJPEG fs_%s_viewer_left" % stem, 400)
            s.cmd("set ui_wvSpin 0", 300)
        s.cmd("quit", 0)
        W.launch("fs2_built", os.environ.get("WV_RES", "uw"), s,
                 lines=['seta coop_lo2 ""', 'seta coop_loA2 ""', 'seta coop_loFA2 ""', "set g_gametype 2",
                        "set coop_dev 1", "set coop_lockLoadout 0", "set ui_dmmap m2l1", "ui_startdmmap 2"], budget=300)
    finally:
        for d in dsts:
            if os.path.exists(d):
                os.remove(d)


if __name__ == '__main__':
    main()
