"""p2_strip.py <label> <model.tik> [scale] - the walk-around of a prop: put it on the lit, level spot of m3l2 and look at
it from 8 directions standing (eye 82u) and from 8 crouched (eye ~50u), plus from right above. Writes
<label>_strip.jpg (4 x 4 crops + the top view) next to this file. Used for the .30 cal sandbag rest (bug-3562):
'Make sure the sandbag isn't invisible on the sides too'."""
import os, re, sys, time
import p2lib as G
from PIL import Image, ImageDraw
R = G.R
LABEL, MODEL = sys.argv[1], sys.argv[2]
SCALE = sys.argv[3] if len(sys.argv) > 3 else "0"
X, Y, Z = -3608, 2303, 84
rundir = notes = None
try:
    rundir, notes = G.boot("p2_strip_" + LABEL, "m3l2")
    G.cmd("tp", x=X - 200, y=Y, z=Z + 8, yaw=0, pitch=0)
    time.sleep(0.6)
    G.cmd("put", x=X, y=Y, z=Z, yaw=0, tag=MODEL, n=SCALE)
    for k in range(8):
        G.cmd("orbit", n=78, yaw=k * 45 + 20, z=8, pitch=82)
        time.sleep(0.5)
        G.still("%s_stand_%d" % (LABEL, k))
    R.step(["+movedown", "wait 200", "-movedown", "wait 900"], timeout=30)
    for k in range(8):
        G.cmd("orbit", n=62, yaw=k * 45 + 20, z=8, pitch=50)
        time.sleep(0.5)
        G.still("%s_low_%d" % (LABEL, k))
    R.step(["+movedown", "wait 200", "-movedown", "wait 900"], timeout=30)
    G.cmd("orbit", n=22, yaw=200, z=6, pitch=82)
    time.sleep(0.5)
    G.still("%s_top" % LABEL)
    G.log("script errors:", G.errors()[:6])
except Exception as e:
    import traceback
    G.log("FAILED", repr(e), traceback.format_exc()[-900:])
finally:
    G.end(rundir, notes)
# the sheet
if rundir:
    cells = []
    for kind, lab in (("stand", "standing"), ("low", "crouched")):
        for k in range(8):
            p = os.path.join(rundir, "%s_%s_%d.jpg" % (LABEL, kind, k))
            if not os.path.exists(p):
                continue
            im = Image.open(p)
            w, h = im.size
            c = im.crop((w // 2 - 260, h // 2 - 150, w // 2 + 260, h // 2 + 240)).resize((320, 240), Image.LANCZOS)
            ImageDraw.Draw(c).text((6, 4), "%s, from %d deg" % (lab, k * 45 + 20), fill=(255, 255, 255))
            cells.append(c)
    p = os.path.join(rundir, "%s_top.jpg" % LABEL)
    top = None
    if os.path.exists(p):
        im = Image.open(p)
        w, h = im.size
        top = im.crop((w // 2 - 260, h // 2 - 195, w // 2 + 260, h // 2 + 195)).resize((320, 240), Image.LANCZOS)
        ImageDraw.Draw(top).text((6, 4), "from above", fill=(255, 255, 255))
    rows = (len(cells) + 3) // 4
    sheet = Image.new("RGB", (4 * 320, rows * 240 + (240 if top else 0)), (20, 20, 20))
    for i, c in enumerate(cells):
        sheet.paste(c, ((i % 4) * 320, (i // 4) * 240))
    if top:
        sheet.paste(top, (0, rows * 240))
    out = os.path.join(G.HERE, "%s_strip.jpg" % LABEL)
    sheet.save(out, quality=88)
    print("wrote", out, len(cells), "views")
