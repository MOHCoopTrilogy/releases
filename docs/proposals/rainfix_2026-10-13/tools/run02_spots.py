"""run02_spots.py <sess> <map> <x> <y> <z> <yaw> [theme] - scan for rooms / alleys / high spots and take one still of each
candidate (fixed build), as a contact sheet for picking the evidence views."""
import sys, time, os, re, json
import rainlib as L
R = L.R
CG = "C:/mohaa-coop-dev/openmohaa-hzm-rainfix/.cmake/code/client/cgame/Release/cgame.dll"
sess, mp = sys.argv[1], sys.argv[2]
OPT_HERE = sys.argv[3] == "here"
P = (0.0, 0.0, 0.0) if OPT_HERE else tuple(float(v) for v in sys.argv[3:6])
YAW = float(sys.argv[6])
theme = sys.argv[7] if len(sys.argv) > 7 else "rain"
rundir = notes = None
try:
    rundir, notes = L.boot(sess, mp, 1280, 720, CG, "rain_stats",
                           extra=["set coop_weatherPin 4", "set coop_weatherForce %s" % theme])
    if OPT_HERE:
        import re as _re
        m = _re.findall(r"GQ ready origin=\( ([-\d.]+) ([-\d.]+) ([-\d.]+) \)", R.read_log())
        P = tuple(float(v) for v in m[-1])
        L.log("spawn", P)
    L.log(L.tp(P, YAW, 0, ground=1))
    seg = L.cmd("scan", P, wait=180, step=80, half=30) or ""
    cands = []
    for kind, x, y, z, yaw in re.findall(r"GQ (room|alley|high) \d+ at \( ([-\d.]+) ([-\d.]+) ([-\d.]+) \) yaw=([-\d.]+)", seg):
        cands.append((kind, float(x), float(y), float(z), float(yaw)))
    for l in seg.splitlines():
        if "GQ " in l and ("room" in l or "alley" in l or "high" in l or "scan" in l):
            L.log(l.split("^~^~^")[-1].strip())
    L.save(rundir, "cands.json", cands)
    names = []
    labels = []
    for i, (kind, x, y, z, yaw) in enumerate(list(cands)):
        if mp != "m3l2" and kind != "room":
            continue
        pitch = 25 if kind == "high" else 0
        L.log(kind, i, L.tp((x, y, z), yaw, pitch, ground=1))
        time.sleep(1.0)
        names.append(L.shot(rundir, "cand_%02d_%s" % (i, kind)))
        labels.append("%d %s" % (i, kind))
        if kind == "room":
            L.tp((x, y, z), yaw, -60, ground=1)
            time.sleep(0.8)
            labels.append("%d room, looking up" % i)
            names.append(L.shot(rundir, "cand_%02d_roomup" % i))
    from PIL import Image, ImageDraw
    n = len(names)
    if n:
        cols = 4
        rows = (n + cols - 1) // cols
        sh = Image.new("RGB", (cols * 480, rows * 270))
        d = ImageDraw.Draw(sh)
        for i, fn in enumerate(names):
            if not fn:
                continue
            sh.paste(Image.open(fn).resize((480, 270)), ((i % cols) * 480, (i // cols) * 270))
            d.text(((i % cols) * 480 + 6, (i // cols) * 270 + 4), labels[i], fill=(255, 255, 0))
        sh.save(os.path.join(rundir, "sheet_cands.jpg"), quality=85)
finally:
    L.finish(rundir, notes)
    print("RUNDIR", rundir)
