"""g2_media.py - bug-3562 media from the run folders: before/after stills per place, one GIF (set-up, firing, pack-up).
Night-map stills (m4l1) are brightened and say so in the file name."""
import os, re, sys
from PIL import Image, ImageEnhance, ImageDraw
RUNS = "G:/mohaa-hudfeed5/runs/"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "C:/mohaa-coop-dev/docs/proposals/para_30cal_2026-10-12/media/"
os.makedirs(OUT, exist_ok=True)


def load(run, name, bright=1.0, crop=None, size=(960, 540)):
    p = os.path.join(RUNS, "g2_para_" + run, name)
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGB")
    if crop:
        im = im.crop(crop)
    if bright != 1.0:
        im = ImageEnhance.Brightness(im).enhance(bright)
    return im.resize(size, Image.LANCZOS)


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 9 + 7 * len(text), 22), fill=(0, 0, 0))
    d.text((6, 5), text, fill=(255, 255, 255))
    return im


def pair(out, before, after, tb, ta):
    ims = [label(x, t) for x, t in ((before, tb), (after, ta)) if x is not None]
    if not ims:
        print("missing", out)
        return
    sh = Image.new("RGB", (960 * len(ims), 540))
    for i, im in enumerate(ims):
        sh.paste(im, (i * 960, 0))
    sh.save(OUT + out, quality=90)
    print(out, len(ims))


C = (260, 120, 1020, 548)   # the middle of the frame: the camera looks at the gun
pair("ground_tripod_before_after.jpg", load("old_ground", "old_ground_ground_still_4.jpg", crop=C), load("fin_ground", "fin_ground_ground_still_4.jpg", crop=C),
     "BEFORE (m3l2, open ground)", "AFTER: on the tripod (m3l2)")
pair("ground_tripod_before_after_wide.jpg", load("old_ground", "old_ground_ground_still_0.jpg"), load("fin_ground", "fin_ground_ground_still_0.jpg"),
     "BEFORE (m3l2, open ground)", "AFTER: on the tripod (m3l2)")
pair("object_bipod_before_after_brightened.jpg", load("old_obj", "old_obj_obj_still_1.jpg", 2.2, C), load("fin_obj", "fin_obj_obj_still_1.jpg", 2.2, C),
     "BEFORE (m4l1 at night, brightened x2.2)", "AFTER: bipod on the bank (m4l1, brightened x2.2)")
pair("sandbag_rest_after.jpg", load("fin_bag", "fin_bag_bag_still_4.jpg", crop=C), load("fin_bag", "fin_bag_bag_still_1.jpg", crop=C),
     "AFTER: sandbag rest, side (m3l2)", "AFTER: sandbag rest, three-quarter (m3l2)")
for run, site in (("fin_ground", "ground"), ("fin_bag", "bag"), ("fin_obj", "obj")):
    for k in range(5):
        im = load(run, "%s_%s_still_%d.jpg" % (run, site, k), 2.2 if site == "obj" else 1.0, size=(1280, 720))
        if im is not None:
            im.save(OUT + "after_%s_%d%s.jpg" % (site, k, "_brightened" if site == "obj" else ""), quality=88)

# ---- the GIF: set-up, firing, pack-up on the tripod
run, site = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("fin_ground", "ground")
d = os.path.join(RUNS, "g2_para_" + run)
log = open(os.path.join(HERE, "out_%s.txt" % run), errors="replace").read()
tries = [int(m) for m in re.findall(r"%s_%s_setup(\d+)_0000\.jpg" % (run, site), " ".join(os.listdir(d)))]
last = max(tries) if tries else 1
ts = [float(x) for x in re.findall(r"PSQ t=([\d.]+) mg spot", log)]
tk = [float(x) for x in re.findall(r"PSQ t=([\d.]+) mg setup k=1", log)]
i0 = 20
if ts and tk:
    delta = tk[-1] - ts[-1]                   # plan -> mounted, seconds
    i0 = max(0, int((delta - 1.8 - 3.2) / 0.15))
sel = [("%s_%s_setup%d_%04d.jpg" % (run, site, last, i), "set-up") for i in range(i0, min(70, i0 + 34), 2)]
sel += [("%s_%s_fire_%04d.jpg" % (run, site, i), "firing") for i in range(8, 30, 2)]
sel += [("%s_%s_packup_%04d.jpg" % (run, site, i), "pack-up") for i in range(0, 30, 2)]
for W in (560, 480, 400, 340):
    fr = []
    for fn, cap in sel:
        p = os.path.join(d, fn)
        if os.path.exists(p):
            im = Image.open(p).convert("RGB").crop((160, 90, 1120, 630)).resize((W, W * 9 // 16), Image.LANCZOS)
            fr.append(label(im, cap).quantize(96, method=Image.MEDIANCUT, dither=Image.NONE))
    if not fr:
        print("no frames for the gif")
        break
    g = OUT + "tripod_setup_fire_packup.gif"
    fr[0].save(g, save_all=True, append_images=fr[1:], duration=300, loop=0, optimize=True)
    sz = os.path.getsize(g)
    print("gif", W, len(fr), sz)
    if sz < 3 * 1024 * 1024:
        break
# contact sheet of the gif frames for QA
if sel:
    tiles = [Image.open(os.path.join(d, fn)).convert("RGB").crop((160, 90, 1120, 630)).resize((320, 180)) for fn, _ in sel if os.path.exists(os.path.join(d, fn))]
    cols = 8
    sh = Image.new("RGB", (320 * cols, 180 * ((len(tiles) + cols - 1) // cols)))
    for i, t in enumerate(tiles):
        sh.paste(t, ((i % cols) * 320, (i // cols) * 180))
    sh.save(os.path.join(HERE, "qa_gif_sheet.jpg"), quality=80)
    print("sheet", len(tiles))
