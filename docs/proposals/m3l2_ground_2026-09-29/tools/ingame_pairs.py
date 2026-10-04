"""ingame_pairs.py RUNDIR OUTDIR - stack BEFORE over AFTER for every view of an m3l2g_ingame.py run (JPEG q88).
Pairs: gl2_before/gl2_after (m3l2), m3l3_gl2_before/m3l3_gl2_after (shared-texture control, must be identical),
gl1_after alone (fallback renderer). Prints the mean abs pixel difference of each pair."""
import os, re, sys
import numpy as np
from PIL import Image, ImageDraw

run, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)


def shots(setname):
    d = os.path.join(run, setname)
    res = {}
    if not os.path.isdir(d):
        return res
    for fn in os.listdir(d):
        m = re.match(r"mg_%s_(.+)\.(jpg|tga|png)$" % re.escape(setname), fn, re.I)
        if m and "_walk" not in m.group(1):
            res[m.group(1)] = os.path.join(d, fn)
    return res


def label(im, text):
    im = im.convert("RGB")
    ImageDraw.Draw(im).text((8, 6), text, fill=(255, 255, 0))
    return im


for before, after, tag in (("gl2_before", "gl2_after", "m3l2"), ("m3l3_gl2_before", "m3l3_gl2_after", "m3l3")):
    A, B = shots(before), shots(after)
    for view in sorted(set(A) & set(B)):
        a, b = Image.open(A[view]).convert("RGB"), Image.open(B[view]).convert("RGB")
        diff = float(np.abs(np.asarray(a, np.int16) - np.asarray(b, np.int16)).mean())
        w, h = a.size
        sheet = Image.new("RGB", (w, h * 2 + 4), (0, 0, 0))
        sheet.paste(label(a, "%s BEFORE (%s, live stack)" % (view, before)), (0, 0))
        sheet.paste(label(b, "%s AFTER (%s, + zzzzzzzzzz_coop_m3l2ground.pk3)" % (view, after)), (0, h + 4))
        p = os.path.join(out, "%s_%s.jpg" % (view, "pair" if tag == "m3l2" else "control"))
        sheet.save(p, quality=88)
        print("%-28s mean|diff| %.2f  %s" % (view, diff, p))
for view, p in sorted(shots("gl1_after").items()):
    q = os.path.join(out, "%s_gl1_after.jpg" % view)
    label(Image.open(p), "%s AFTER, opengl1 fallback" % view).save(q, quality=88)
    print("%-28s gl1 %s" % (view, q))
