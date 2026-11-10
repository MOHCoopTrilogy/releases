r"""voidprobe.py - "never see out of bounds": find every camera pose in the 3D menus that shows the void past the rooms' edges.

The Scene3D renders with RDF_NOWORLDMODEL and clears nothing: where no surface is drawn, whatever the menu drew BEFORE the scene
shows through (black, or the flat fallback picture - the user's 'white sliver'). So the probe copies the mod's ui files and puts a
full-screen MAGENTA label right before every Scene3D: every magenta pixel in a still is the void.

Poses: every 'scenecam' / 'scenefly <t>' / 'scenepeek' pose in the ui tree (urc, inc, cfg), per scene name, plus the in-between
frames of each fly (the engine's fly is a smoothstep lerp of origin, angles - shortest way round - and fov, cl_uiscene.cpp
UIScene3D::Draw, so lerps at e = 0.25 / 0.5 / 0.75 ARE frames of the real path) from the scene's home and from the side views the
MP room's scripted turns start from. The camera is held by the engine's debug cvar ui_scene_pose (all scenes; no fly).

    python voidprobe.py poses <mod ui dir> <out.json>
    python voidprobe.py run <menus pak> <mod ui dir> <poses.json> <res 1080|219|43> <tag> [scene,scene..] [--first N --count M]
    python voidprobe.py scan <run dir>                    -> <run dir>/void.json + crops of every hit
"""
import json, math, os, re, shutil, sys, zipfile

F7 = r"(-?[\d.]+(?:\s+-?[\d.]+){6})"
MAG_LABEL = ("resource\nLabel\n{\nname \"voidprobe_bg\"\nrect 0 0 640 480\nfgcolor 1 0 1 1\nbgcolor 1 0 1 1\nborderstyle \"NONE\"\n}\n")


def pose(s):
    v = [float(x) for x in s.split()]
    return [round(x, 2) for x in v]


def scenes_in(t):
    """[(scene name, home pose, peeks)] of the Scene3D widgets in a ui file"""
    out = []
    for m in re.finditer(r"(?m)^Scene3D\s*\n\{(.*?)\n\}", t, re.S):
        b = m.group(1)
        nm = re.search(r'(?m)^name "([^"]+)"', b).group(1)
        h = re.search(r"(?m)^scenecam " + F7, b)
        pk = [pose(p.group(1)) for p in re.finditer(r'(?m)^scenepeek "[^"]+" \S+ ' + F7, b)]
        out.append((nm, pose(h.group(1)) if h else None, pk))
    return out


def lerp(a, b, e):
    o = [a[i] + (b[i] - a[i]) * e for i in range(3)]
    for i in (3, 4, 5):
        d = b[i] - a[i]
        d = d - 360.0 * math.floor(d / 360.0 + 0.5)
        o.append(a[i] + d * e)
    o.append(a[6] + (b[6] - a[6]) * e)
    return [round(x, 2) for x in o]


def poses(ui, out):
    files = sorted(f for f in os.listdir(ui) if f.lower().endswith((".urc", ".inc", ".cfg")))
    texts = {f: open(os.path.join(ui, f), encoding="latin-1").read().replace("\r\n", "\n") for f in files}
    S = {}                                   # scene -> dict(host menu, home, targets)
    inc_host = {}
    for f, t in texts.items():
        for inc in re.findall(r'(?m)^include "ui/([^"]+)"', t):
            mm = re.search(r'(?m)^menu "([^"]+)"', t)
            if mm:
                inc_host.setdefault(inc, mm.group(1))
    for f, t in texts.items():
        for nm, home, pk in scenes_in(t):
            mm = re.search(r'(?m)^menu "([^"]+)"', t)
            host = mm.group(1) if mm else inc_host.get(f)
            S.setdefault(nm, dict(file=f, host=host, home=home, targets={}))
            for p in pk:
                S[nm]["targets"].setdefault(json.dumps(p), "peek")
    for f, t in texts.items():
        for m in re.finditer(r"globalwidgetcommand (\w+) scene(?:fly [\d.]+|cam) " + F7, t):
            if m.group(1) in S:
                S[m.group(1)]["targets"].setdefault(json.dumps(pose(m.group(2))), f)
    shots = {}
    for nm, s in S.items():
        L = []
        if s["home"]:
            L.append(("home", s["home"]))
        tg = [json.loads(k) for k in s["targets"]]
        for k, p in enumerate(tg):
            L.append(("t%02d" % k, p))
            if s["home"] and p != s["home"]:
                for e in (0.25, 0.5, 0.75):
                    L.append(("t%02d_h%02d" % (k, int(e * 100)), lerp(s["home"], p, e)))
        shots[nm] = dict(host=s["host"], file=s["file"], poses=L)
    json.dump(shots, open(out, "w"), indent=1)
    for nm, s in shots.items():
        print("%-22s host %-22s %3d poses" % (nm, s["host"], len(s["poses"])))
    return shots


def add_pairs(shots, nm, a, bs, tag):
    """extra in-between frames for the flights that start from a side view (a) to each of bs"""
    for k, b in enumerate(bs):
        for e in (0.25, 0.5, 0.75):
            shots[nm]["poses"].append(("%s%02d_%02d" % (tag, k, int(e * 100)), lerp(a, b, e)))


def overlay_ui(ui, dst):
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(ui, dst, ignore=shutil.ignore_patterns("*.tga", "*.jpg", "*.png", "*.wav", "*.mp3", "*.ogg", "*.roq"))
    n = 0
    for f in os.listdir(dst):
        p = os.path.join(dst, f)
        if f.lower().endswith((".urc", ".inc")):
            t = open(p, encoding="latin-1", newline="").read()
            nl = "\r\n" if "\r\n" in t else "\n"
            t2 = re.sub(r"(?m)^resource(\r?\n)Scene3D", lambda m: MAG_LABEL.replace("\n", nl) + "resource" + m.group(1) + "Scene3D", t)
            if t2 != t:
                n += 1
                open(p, "w", encoding="latin-1", newline="").write(t2)
    return n


def run(pak, ui, spec, res, tag, only=None, first=0, count=10 ** 6):
    os.environ["HZM_TEST_RES"] = "1920x1080"
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ["MP69_RES"] = res
    import mp69_run as M
    tmp = os.path.join(r"H:\hzm_work\attic62", "voidui")
    print("magenta under", overlay_ui(ui, tmp), "scene files")
    M.setup(pak, tmp, "-")
    shots = json.load(open(spec))
    w, h, center, lay = M.E.RES[res]
    L = ["set developer 0", "set ui_menuRoom 1", "set ui_atticMain 1", "set ui_menuCenter %d" % center, "set ui_camslow 1",
         "set coop_hardcore 0", "set ui_wxHour 12.5", "set ui_wxWeather 1", "wait 12000", "echo ^~^~^ VOID start"]
    idx = []
    i = 0
    for nm, s in shots.items():
        if only and nm not in only:
            continue
        P = [p for p in s["poses"]]
        sel = []
        for pn, p in P:
            if first <= i < first + count:
                sel.append((pn, p))
            i += 1
        if not sel:
            continue
        if s["host"] and s["host"] != "main":
            L += ["pushmenu %s" % s["host"], "wait 2500"]
        for pn, p in sel:
            L += ['set ui_scene_pose "%s"' % " ".join("%.2f" % x for x in p), "wait 350", "screenshotJPEG v_%s_%s" % (nm, pn), "wait 150"]
            idx.append((nm, pn, p))
        L += ['set ui_scene_pose ""', "wait 300"]
        if s["host"] and s["host"] != "main":
            L += ["popmenu 0", "wait 1200"]
    L += ["echo ^~^~^ VOID done", "wait 1000", "quit"]
    args = ["+set", "ui_menuCenter", str(center), "+set", "ui_menuRoom", "1", "+set", "ui_atticMain", "1",
            "+set", "s_volume", "0", "+set", "s_musicvolume", "0", "+set", "s_ambientvolume", "0", "+set", "com_maxfpsUnfocused", "30",
            "+set", "in_mouse", "0", "+set", "in_nograb", "1", "+set", "in_gamepad", "0", "+set", "in_joystick", "0",
            "+set", "coop_tinnitus", "0", "+set", "r_screenshotJpegQuality", "92"]
    if os.path.exists(M.STOP):
        raise SystemExit("guard tripped earlier")
    out = M.A.launch("void_%s" % tag, w, h, L, args)
    if M.TRIPS:
        raise SystemExit("GUARD TRIPPED %s" % (M.TRIPS[:2],))
    json.dump(idx, open(os.path.join(out, "index.json"), "w"))
    print(out, len(idx), "shots")
    return out


def scan(d):
    import numpy as np
    from PIL import Image
    idx = {("v_%s_%s" % (nm, pn)): (nm, pn, p) for nm, pn, p in json.load(open(os.path.join(d, "index.json")))}
    res = []
    os.makedirs(os.path.join(d, "hits"), exist_ok=True)
    for f in sorted(os.listdir(d)):
        if not f.endswith(".jpg") or not f.startswith("v_"):
            continue
        k = f[:-4]
        a = np.asarray(Image.open(os.path.join(d, f)).convert("RGB")).astype(np.int16)
        m = (a[..., 0] > 170) & (a[..., 2] > 170) & (a[..., 1] < 90)
        n = int(m.sum())
        if k in idx:
            nm, pn, p = idx[k]
        else:
            nm, pn, p = k, "", None
        r = dict(shot=k, scene=nm, pose_name=pn, pose=p, void_px=n)
        if n > 30:
            ys, xs = np.nonzero(m)
            r["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
            Image.open(os.path.join(d, f)).convert("RGB").resize((a.shape[1] // 2, a.shape[0] // 2)).save(os.path.join(d, "hits", f), quality=80)
        res.append(r)
    json.dump(res, open(os.path.join(d, "void.json"), "w"), indent=1)
    hits = [r for r in res if r["void_px"] > 30]
    print("%d shots, %d with void" % (len(res), len(hits)))
    for r in hits:
        print("  %-40s %7d px  bbox %s  pose %s" % (r["shot"], r["void_px"], r.get("bbox"), r["pose"]))
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "poses":
        poses(a[1], a[2])
    elif a[0] == "run":
        only = a[6].split(",") if len(a) > 6 and a[6] not in ("-", "") and not a[6].startswith("--") else None
        first = int(a[a.index("--first") + 1]) if "--first" in a else 0
        count = int(a[a.index("--count") + 1]) if "--count" in a else 10 ** 6
        run(a[1], a[2], a[3], a[4], a[5], only, first, count)
    elif a[0] == "scan":
        scan(a[1])
