"""Gun repaint, in-engine before / after. Private harness copy G:/mohaa-hudfeed3 (slot "hudfeed3", port 12741),
DISPLAY2 through the harness, engine `screenshot` only (one per step), net_ip 127.0.0.1.
Binaries: the RELEASED set (exe, game, cgame, gl2 renderer copied read-only from the GOG root - the harness's game
paks are today's deployed build); what stood in the harness root is kept beside it (*.pre_repaint) and put back
after every run.

    python run_rp.py <item> <tag> before|after <map> [--only <regex of staged game paths>] [--quick] [--props] [--guns a,b]

item: sil | grease | shotgun (see ITEMS). Per spot of the map, per gun: hip + aim; at the first spot also third
person; then the guns laid on the ground three at a time, seen from above with the view model hidden. Ends with
`imagelist`; the lines matching the item's texture names go to <rundir>/images.txt - proof of WHICH file was loaded.
Stills land in G:/mohaa-hudfeed3/runs/rp_<item>_<tag>_<mode>_<map>/ as PNG (sheets are made from there, sheet.py).
"""
import os, re, sys, time, shutil, subprocess, hashlib
IS = "C:/mohaa-coop-dev/docs/proposals/ironsights_2026-09-28/tools"
sys.path.insert(0, IS)
import run_sweep as S          # noqa: E402
R = S.R
HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.abspath(os.path.join(HERE, ".."))
GOGROOT = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
R.OWNER = "hudfeed3"
R.CLIENT = "G:/mohaa-hudfeed3"
R.EXE = os.path.join(R.CLIENT, "openmohaa_rel1013.exe")
R.HOME = os.path.join(R.CLIENT, "home")
R.MAINTT = os.path.join(R.HOME, "maintt")
R.LOG = os.path.join(R.MAINTT, "qconsole.log")
R.SHOTS = os.path.join(R.MAINTT, "screenshots")
R.PRISTINE = os.path.join(R.CLIENT, "pristine")
R.RUNS = "G:/mohaa-hudfeed3/runs"
R.PORT = 12741
ROOTF = ("game.dll", "cgame.dll", "renderer_opengl2.dll")
SPOTS = {"m3l2": [("light", (-3608, 2303, 80, 165)), ("dark", (-3608, 2303, 80, 225))],
         "m4l1": [("night", (-3904, -6120, -456, 45))]}
W_ = "models/weapons/"
ITEMS = {
    "sil": dict(
        guns=[("colt", W_ + "colt_silenced.tik"), ("beretta", W_ + "berettasilenced.tik"),
              ("grease", W_ + "greasegun_silenced.tik"), ("garand", W_ + "garand_silenced.tik"),
              ("kar98", W_ + "kar98snipersilenced.tik"), ("mosin", W_ + "nagant_snipersilenced.tik")],
        filt=r"colt45s2"),
    "grease": dict(
        guns=[("grease", W_ + "greasegun.tik"), ("greasesil", W_ + "greasegun_silenced.tik"),
              ("greaseai", W_ + "coop_greasegun_ai.tik")],
        filt=r"greaser|colt45s2"),
    "shotgun": dict(
        guns=[("shotgun", W_ + "shotgun.tik"), ("blued", W_ + "shotgun_blued.tik"), ("chrome", W_ + "shotgun_chrome.tik"),
              ("gold", W_ + "shotgun_gold.tik"), ("bloody", W_ + "shotgun_bloody.tik"),
              ("woodland", W_ + "shotgun_camo_woodland.tik"), ("winter", W_ + "shotgun_camo_winter.tik"),
              ("desert", W_ + "shotgun_camo_desert.tik")],
        filt=r"winchester|coop_sg|shotgun"),
}


SCOPED = ("garand", "kar98", "mosin")      # silenced Garand / Kar98 sniper / Mosin sniper: scoped
HOLD = W_ + "colt45.tik"                   # an unscoped gun in the hand while the props are photographed


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def install():
    """released binaries into the harness under their own names; the root files of before are kept beside."""
    for f in ROOTF:
        keep = os.path.join(R.CLIENT, f + ".pre_repaint")
        if not os.path.exists(keep):
            shutil.copyfile(os.path.join(R.CLIENT, f), keep)
    pairs = [("openmohaa.exe", R.EXE), ("game.dll", os.path.join(R.CLIENT, "games", "game_rel1013.dll")),
             ("cgame.dll", os.path.join(R.CLIENT, "cgames", "cgame_rel1013.dll")),
             ("renderer_opengl2.dll", os.path.join(R.CLIENT, "renderers", "gl2_rel1013.dll"))]
    for src, dst in pairs:
        src = os.path.join(GOGROOT, src)
        if not os.path.exists(dst) or md5(src) != md5(dst):
            shutil.copyfile(src, dst)
    shutil.copyfile(pairs[1][1], os.path.join(R.CLIENT, "game.dll"))
    shutil.copyfile(pairs[3][1], os.path.join(R.CLIENT, "renderer_opengl2.dll"))
    return "cgame_rel1013"


def restore():
    for f in ROOTF:
        keep = os.path.join(R.CLIENT, f + ".pre_repaint")
        if os.path.exists(keep):
            shutil.copyfile(keep, os.path.join(R.CLIENT, f))


def snap(name):
    R.step(["screenshot " + name, "wait 300"], timeout=30)


def main():
    item, tag, mode, mp = sys.argv[1:5]
    quick = "--quick" in sys.argv
    props_only = "--props" in sys.argv
    it = ITEMS[item]
    guns = it["guns"]
    if "--guns" in sys.argv:
        keep = sys.argv[sys.argv.index("--guns") + 1].split(",")
        guns = [g for g in guns if g[0] in keep]
    W, H = 1920, 1080
    os.makedirs(os.path.join(PROP, "work"), exist_ok=True)
    ov = os.path.join(PROP, "work", "ov_%s_%s.pk3" % (item, mode))
    cmd = [sys.executable, os.path.join(HERE, "mkov.py"), ov]
    if mode == "before":
        cmd.append("--base")
    elif "--only" in sys.argv:
        cmd += ["--only", sys.argv[sys.argv.index("--only") + 1]]
    subprocess.check_call(cmd)
    cg = install()
    R.MAP = mp
    R.SPOT = SPOTS[mp][0][1]
    sess = "rp_%s_%s_%s_%s" % (item, tag, mode, mp)
    rundir = notes = None
    try:
        extra = ["set g_ai 0", "set coop_st_xp 0", "set developer 1", "set com_maxfpsUnfocused 60", "set s_volume 0"]
        rundir, notes = S.boot_session(sess, cg, W, H, extra, ov)
        print("booted", notes.get("md5"), flush=True)
        n = 0
        for si, (sname, spot) in enumerate(SPOTS[mp]):
            R.SPOT = spot
            for gname, tik in ([] if props_only else guns):
                R.step(S.RELEASE + S.TO_STAND + S.give(tik), timeout=90)
                snap("%s_%s_hip" % (sname, gname))
                if gname in SCOPED:        # the aim is the scope picture (and it latches): nothing of the gun to see
                    continue
                R.step(["+button13", "wait 1900"], timeout=30)
                snap("%s_%s_ads" % (sname, gname))
                R.step(["-button13", "wait 700"], timeout=30)
            if quick:
                continue
            # world model (same skd and shader as in the hand): three guns floating side-on at 70 u = what another
            # player's gun looks like at conversation distance (the engine's own third-person camera sits behind the
            # shoulder and hides the gun - run r1), both sides; then the same three laid on the ground, from above.
            R.step(S.RELEASE + S.TO_STAND + S.give(HOLD), timeout=90)
            for gi in range(0, len(guns), 3):
                grp = guns[gi:gi + 3]
                sets = ["set coop_isP%d %s" % (k + 1, grp[k][1] if k < len(grp) else "none") for k in range(3)]
                for view, pmode, flip, pitch in (("side", "float", 0, 24.0), ("side2", "float", 1, 24.0), ("ground", "ground", 0, 62.0)):
                    n += 1
                    R.step(S.RELEASE + R.give("none", 0.0) + ["wait 800"] + sets
                           + ["set coop_isPmode %s" % pmode, "set coop_isPflip %d" % flip, "set coop_isProp %d" % n, "wait 1200"], timeout=60)
                    R.step(R.give("none", pitch) + ["wait 800", "set cg_drawviewmodel 0", "wait 400"], timeout=60)
                    snap("%s_%s%d" % (sname, view, gi // 3 + 1))
                    R.step(["set cg_drawviewmodel 1", "wait 200"] + R.give("none", 0.0) + ["wait 500"], timeout=60)
            n += 1
            R.step(["set coop_isP1 none", "set coop_isP2 none", "set coop_isP3 none", "set coop_isProp %d" % n, "wait 600"], timeout=60)
        st = R.step(["imagelist", "wait 300"], timeout=60)
        t = R.read_log()
        rx = re.compile(it["filt"], re.I)
        lines = [l for l in t[st:].splitlines() if rx.search(l)]
        open(os.path.join(rundir, "images.txt"), "w").write("\n".join(lines) + "\n")
        print("\n".join(lines))
        print("props:", len(re.findall(r"ISTEST props[^\r\n]*", t)))
        errs = sorted(set(l[-160:] for l in t.splitlines() if "Script Error" in l or "Couldn't compile" in l
                          or "parse error" in l or "not properly loaded" in l))
        print("script errors:", len(errs), errs[:6])
    except Exception as e:
        import traceback
        print("FAILED", repr(e), traceback.format_exc()[-900:])
    finally:
        try:
            if rundir:
                S.end_session(rundir, notes or {})
        except Exception as e:
            print("end_session", repr(e))
        restore()
    if rundir:
        print("rundir", rundir, len(os.listdir(rundir)), "files")


if __name__ == "__main__":
    main()
