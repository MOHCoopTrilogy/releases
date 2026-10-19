"""run_armory_capture.py - ONE private-harness batch for the Armory redesign mock-ups (design only, nothing deployed).

    python -I run_armory_capture.py <runname> [--res 1920x1080] [--dry]

Dedicated server on co_lobby1 + ONE fake-identity client in a private harness copy (G:\\mohaa-hudfeed*, never the live install).
The mod tree is the gunfit2-next branch PINNED at REV (read-only `git archive`; the other agent's worktree is never touched),
packed like the release code pak, plus a test-only OVERLAY pk3 that adds four full-screen widgets to ui/coop_loadout.urc:
  coop_loBigK / coop_loBigW   opaque black / white fill      (difference matting: alpha = 1 - (W-K)/255)
  coop_loBigG                 the gun model (same attributes as prevC0 but rect 0 0 640 480)
  coop_loBigC                 the operator (same attributes as charRender but rect 0 0 640 480)
Phase 1: the REAL menu, as a player sees it (screenshots for CRITIQUE.md).
Phase 2: every gun in GUNS (and finishes in FINISHES) on black + white, scale refit so the gun spans ~1500 px, then the operator.
Everything is wall-clock capped (DEADLINE_S) so the turn is released inside the 15-minute fair-queue limit.
Outputs: <archive>\\<run>\\shots\\*.tga + manifest.json (consumed by build_cutouts.py).
"""
import importlib.util, json, os, re, shutil, subprocess, sys, time, zipfile

import numpy as np
from PIL import Image

TOOLS = r"C:\mohaa-coop-dev\docs\proposals\joinflood_2026-10-14\tools"
spec = importlib.util.spec_from_file_location("jf", os.path.join(TOOLS, "run_joinflood.py"))
jf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jf)
log, check, read, wait_for, step = jf.log, jf.check, jf.read, jf.wait_for, jf.step
ST = jf.ST

MODWT = r"C:\mohaa-coop-dev\hzm-mod-gunfit2"
REV = "c12c83bd"
jf.MODWT = MODWT
jf.ARCHIVE = r"G:\claude_scratch_archive\armory_design"
jf.SCR = r"C:\Users\curry\AppData\Local\Temp\claude\C--mohaa-coop-dev\0ef9c092-ae3c-4811-a8c8-d3c6c827d23b\scratchpad\armory"
DEADLINE_S = 13 * 60
T0 = time.time()

UNL = ("models/player/american_army2.tik|models/player/american_army3.tik|models/player/american_army_29id_sgt.tik|"
       "models/weapons/carbine.tik")
GUNS = ["03", "01", "02", "04", "78", "70", "05", "06", "07", "08", "09", "10", "11", "12", "13",
        "24", "25", "26", "28", "29", "33", "34", "36", "37", "43", "42", "48", "50", "53", "55", "57"]
# (output name, gun id, finish button 1..7)  1 gold 2 chrome 3 blued 4 bloody 5 woodland 6 winter 7 desert
FINISHES = [("03_f1", "03", 1), ("03_f2", "03", 2), ("03_f3", "03", 3), ("03_f5", "03", 5), ("03_f7", "03", 7), ("04_f1", "04", 1), ("01_f1", "01", 1), ("24_f1", "24", 1), ("48_f2", "48", 2)]
CHARS = [("char_rifle", "01", 200), ("char_smg", "24", 200), ("char_pistol", "48", 200)]
if "--set2" in sys.argv:       # second batch: assets the first sheet lacked (grenade, more SMGs, operator turned toward the camera)
    GUNS = ["64", "27", "30", "31", "32", "35", "71", "14", "15", "16", "17"]
    FINISHES = []
    CHARS = [("char_rifle_y160", "01", 160), ("char_rifle_y250", "01", 250), ("char_rifle_y120", "01", 120),
             ("char_smg_y160", "24", 160), ("char_smg_y250", "24", 250)]
TABS = {0: "set coop_loNP0 0; set coop_loP1 0; set coop_loP2 0; set coop_loP3 0; set coop_loP4 0; set coop_loP5 0 ; exec ui/loadout/lktab0.cfg",
        1: "set coop_loNP0 1; set coop_loP1 1; set coop_loP2 0; set coop_loP3 0; set coop_loP4 0; set coop_loP5 0 ; exec ui/loadout/lktab1.cfg",
        2: "set coop_loNP0 1; set coop_loP1 0; set coop_loP2 1; set coop_loP3 0; set coop_loP4 0; set coop_loP5 0 ; exec ui/loadout/lktab2.cfg"}


def late():
    return time.time() - T0 > DEADLINE_S


# ------------------------------------------------------------------ packs
def code_pak():
    """the pinned gunfit2 rev packed like the release code pak (read-only git archive)"""
    os.makedirs(jf.SCR, exist_ok=True)
    full = subprocess.run(["git", "-C", MODWT, "rev-parse", REV], capture_output=True, check=True).stdout.decode().strip()
    code = os.path.join(jf.SCR, "code_armory_%s.pk3" % full[:10])
    if not os.path.isfile(code):
        tops = [t for t in subprocess.run(["git", "-C", MODWT, "ls-tree", "--name-only", full], capture_output=True,
                                          check=True).stdout.decode().splitlines()
                if t not in ("sound", "textures", "models", "gfx", "env") and not t.lower().endswith(".pk3")
                and not t.startswith(".git")]
        subprocess.run(["git", "-C", MODWT, "archive", "--format=zip", "-1", "-o", code, full, "--"] + tops, check=True)
    return code, full


FILL = """
resource
Label
{
name "%(n)s"
rect 0 0 640 480
fgcolor 1.00 1.00 1.00 1.00
bgcolor %(c)s
borderstyle "NONE"
enabledcvar "%(cv)s"
}
"""
GUNW = """
resource
Label
{
ordernumber 20
name "bigGun"
rect 0 0 640 480
fgcolor 1.00 1.00 1.00 1.00
bgcolor 0.00 0.00 0.00 0.00
borderstyle "NONE"
enabledcvar "coop_loBigG"
linkcvar "coop_loPrev"
modelxformcvar "coop_loXfmW"
rendermodel 1
rendermodelfit 1
modeloffset "0 0 0"
modelrotateoffset "0 0 0"
modelangles "0 90 180"
modelscale 1.00
modelanim idle
}
"""
CHARW = """
resource
Label
{
ordernumber 20
name "bigChar"
rect 0 0 640 480
fgcolor 1.00 1.00 1.00 1.00
bgcolor 0.00 0.00 0.00 0.00
borderstyle "NONE"
enabledcvar "coop_loBigC"
linkcvar "coop_loChar"
modelxformcvar "coop_loXfmC"
rendermodel 1
modelattachcvar "coop_loHelm"
modelattachtag "Bip01 Head"
modelattachcvar2 "coop_loPrev"
modelattachtag2 "tag_weapon_right"
modelspincvar "coop_loCharSpin"
modelanimcvar "coop_loCharAnim"
modeloffset "78 0 -18"
modelrotateoffset "0 0 0"
modelangles "0 200 0"
modelscale 1.0
modelanim coop_loadout_idle
}
"""


def overlay_pak(full):
    urc = subprocess.run(["git", "-C", MODWT, "show", "%s:ui/coop_loadout.urc" % full], capture_output=True, check=True).stdout.decode("latin-1")
    body = urc.rstrip()
    assert body.endswith("end."), "urc tail changed"
    body = body[:-4]
    add = (FILL % {"n": "bigK", "c": "0.00 0.00 0.00 1.00", "cv": "coop_loBigK"} + FILL % {"n": "bigW", "c": "1.00 1.00 1.00 1.00", "cv": "coop_loBigW"}
           + GUNW + CHARW + "\nend.\n")
    p = os.path.join(jf.SCR, "zzzzzzz_armory_overlay.pk3")
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("ui/coop_loadout.urc", body + add)
    return p


def pick_slot():
    for _try in range(60):
        for owner, d in (("hudfeed5", r"G:\mohaa-hudfeed5"), ("hudfeed4", r"G:\mohaa-hudfeed4"), ("hudfeed2", r"G:\mohaa-hudfeed2")):
            try:
                jf.hg.acquire_slot(owner, os.path.join(d, "x.exe"), os.path.join(d, "home_probe"), [12872], 1)
                jf.hg.release_slot(owner)
            except Exception as e:
                log("slot", owner, "busy:", str(e)[:80])
                continue
            jf.SLOTS[:] = [(owner, d)]
            jf.H = d
            jf.PRISTINE = os.path.join(d, "pristine")
            jf.SPORT, jf.CPORTS[:] = 12871, [12872, 12873]
            log("using slot", owner)
            return
        time.sleep(15)
    raise RuntimeError("no free harness slot")


# ------------------------------------------------------------------ image helpers
def newest(sd, name):
    for ext in (".tga", ".jpg", ".png"):
        p = os.path.join(sd, name + ext)
        if os.path.isfile(p):
            return p
    return None


def grab(c, sd, name, settle=0.5):
    step(c, ["screenshot " + name], timeout=30)
    for _ in range(40):
        p = newest(sd, name)
        if p:
            s = os.path.getsize(p)
            time.sleep(0.25)
            if os.path.getsize(p) == s and s > 1000:
                return p
        time.sleep(0.25)
    log("screenshot missing", name)
    return None


def bbox(p, thr=40):
    a = np.asarray(Image.open(p).convert("RGB")).astype(int).max(axis=2)
    ys, xs = np.nonzero(a > thr)
    if len(xs) < 50:
        return None
    return xs.min(), ys.min(), xs.max(), ys.max(), a.shape[1], a.shape[0]


def parse_xfm(txt):
    v = txt.split()
    return [float(x) for x in v[:7]]


def p_xfm(gid):
    """the (pinned) generated p<id>.cfg transform"""
    t = subprocess.run(["git", "-C", MODWT, "show", "%s:ui/loadout/p%s.cfg" % (REV, gid)], capture_output=True, check=True).stdout.decode("latin-1")
    return parse_xfm(re.search(r'set coop_loXfmW "([^"]+)"', t).group(1))


def fmt(x):
    return " ".join(("%.3f" % v).rstrip("0").rstrip(".") if v != int(v) else str(int(v)) for v in x)


def main():
    name = sys.argv[1]
    a = sys.argv[2:]
    W, HH = [int(x) for x in (a[a.index("--res") + 1] if "--res" in a else "1920x1080").split("x")]
    ST["run"] = name
    manifest = {"rev": REV, "res": [W, HH], "real": [], "gun": {}, "char": {}}
    out = os.path.join(jf.ARCHIVE, name)
    os.makedirs(out, exist_ok=True)
    code, full = code_pak()
    ov = overlay_pak(full)
    log("code pak", full[:10], "overlay", ov)
    if "--dry" in a:
        for g in GUNS[:3]:
            log("xfm", g, p_xfm(g))
        return 0
    pick_slot()
    ST.update({"usercfg": False, "netdebug": False, "clprobe": False, "clprobe2": False, "listen": False, "mx": {}, "ufps": 30})
    opts = {"srv": "rel", "cl": "rel", "lobby": "fix", "delay": 0, "parkbytes": None, "mx": {}, "ufps": 30,
            "listen": False, "clprobe": False, "usercfg": False}
    sbins = jf.prep_bins("rel", jf.H)
    cbin = jf.prep_bins("rel", jf.SLOTS[0][1])
    shm, smt = jf.seed_server(opts, code)
    rec = jf.veteran_record(1001)
    rec["unlocks"], rec["chal"], rec["pend"] = UNL, "wpn_garand:50", ""
    pc = jf.seed_client(1, jf.SLOTS[0][1], code, rec)
    shutil.copyfile(ov, os.path.join(pc[1], "zzzzzzz_armory_overlay.pk3"))
    sd = None
    c = None
    try:
        slog = jf.start_server(sbins, shm, smt)
        c = jf.launch_client(1, cbin, pc[0], fps=30, W=W, Hh=HH)
        sd = os.path.join(c["mt"], "screenshots")
        m = wait_for(slog, r"JFTester1[^\r\n]*entered the battle", 240)
        check("client entered the lobby", m)
        time.sleep(35)
        # ---------------- phase 1: the REAL menu
        step(c, ["exec ui/loadout/open.cfg", "wait 120"])
        time.sleep(3)
        for nm, lines in (("real_open", []),
                          ("real_tab_sniper", [TABS[1]]),
                          ("real_tab_smg", [TABS[2]]),
                          ("real_locked_click", [TABS[0], "exec ui/loadout/lkw05.cfg"]),
                          ("real_finish_gold", [TABS[0], "exec ui/loadout/eq01.cfg", "exec ui/loadout/finp01_1.cfg"])):
            if lines:
                step(c, lines)
                time.sleep(1.2)
            p = grab(c, sd, nm)
            manifest["real"].append([nm, bool(p)])
        step(c, [TABS[0], "exec ui/loadout/eq01.cfg"])
        time.sleep(1)
        # ---------------- phase 2: big renders on black / white
        def show(gun, char=False):
            step(c, ["set coop_loBigG %d" % (0 if char else 1), "set coop_loBigC %d" % (1 if char else 0)])

        def render(tag, gid, finish=None, char=False, yaw=200):
            """returns True when both K and W frames exist"""
            base = p_xfm(gid)
            lines = ["exec ui/loadout/p%s.cfg" % gid]
            if finish:
                lines.append("exec ui/loadout/finp%s_%d.cfg" % (gid, finish))
            lines += ["set coop_loBigK 1", "set coop_loBigW 0", "set coop_loBigG %d" % (0 if char else 1), "set coop_loBigC %d" % (1 if char else 0)]
            if char:
                x = [57, 1, 4, 0.55, 0, yaw, 0]
                lines.append('set coop_loXfmC "%s"' % fmt(x))
            step(c, lines)
            time.sleep(1.0)
            s = base[3] if not char else 0.55
            x = list(base) if not char else [57, 1, 4, 0.55, 0, yaw, 0]
            key = "coop_loXfmC" if char else "coop_loXfmW"
            for it in range(2):
                p = grab(c, sd, "%s_p%d" % (tag, it))
                bb = bbox(p) if p else None
                if not bb:
                    log("no bbox", tag, it)
                    return False
                x0, y0, x1, y1, fw, fh = bb
                w, h = x1 - x0 + 1, y1 - y0 + 1
                if char:
                    want = 0.86 * fh
                    ratio = h / want
                else:
                    ratio = max(w / (0.78 * fw), h / (0.84 * fh))
                touching = x0 <= 2 or y0 <= 2 or x1 >= fw - 3 or y1 >= fh - 3
                log("fit", tag, it, "bbox", w, h, "ratio %.3f" % ratio, "touch" if touching else "")
                if abs(ratio - 1) < 0.04 and not touching:
                    break
                x[3] = round(x[3] * (ratio if not touching else max(ratio, 1.25)), 4)
                step(c, ['set %s "%s"' % (key, fmt(x))])
                time.sleep(0.9)
            pk = grab(c, sd, "%s_K" % tag)
            step(c, ["set coop_loBigK 0", "set coop_loBigW 1"])
            time.sleep(0.6)
            pw = grab(c, sd, "%s_W" % tag)
            (manifest["char"] if char else manifest["gun"])[tag] = {"gid": gid, "finish": finish, "xfm": fmt(x), "ok": bool(pk and pw)}
            return bool(pk and pw)

        for tag, gid, yaw in CHARS:
            if late():
                break
            render(tag, gid, None, True, yaw)
        for tag, gid, fin in FINISHES:
            if late():
                break
            render("g" + tag, gid, fin)
        for gid in GUNS:
            if late():
                log("deadline: stopping guns at", gid)
                break
            render("g" + gid, gid)
        step(c, ["set coop_loBigK 0", "set coop_loBigW 0", "set coop_loBigG 0", "set coop_loBigC 0"])
        log("elapsed %.0fs" % (time.time() - T0))
    except Exception as e:
        check("harness ran to the end", False, repr(e))
    finally:
        if c:
            try:
                jf.stop_client(c)
            except Exception as e:
                log("stop note", e)
        jf.stop_server()
        time.sleep(2)
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    if sd and os.path.isdir(sd):
        os.makedirs(os.path.join(out, "shots"), exist_ok=True)
        for f in os.listdir(sd):
            shutil.copyfile(os.path.join(sd, f), os.path.join(out, "shots", f))
    for tag, hm in (("srv", jf.home(jf.H, "srv")), ("pc1", pc[0])):
        if os.path.isdir(hm):
            shutil.move(hm, os.path.join(out, tag))
    lf = os.path.join(jf.SCR, name + ".log")
    if os.path.isfile(lf):
        shutil.copyfile(lf, os.path.join(out, "harness.log"))
    log("DONE ->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
