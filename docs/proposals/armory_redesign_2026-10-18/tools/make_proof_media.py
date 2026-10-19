"""make_proof_media.py <runDir> <outDir> - turn a run_armory_proof.py run into the shareable media.

  <outDir>/armory_<shot>_<WxH>.jpg   every screenshot (q=90)
  <outDir>/armory_browse.gif         the browsing frames (1280x720 session), 960x540, 0.75 s per frame, loops
  <outDir>/armory_contact_<WxH>.jpg  one contact sheet per size (3 columns)
"""
import glob, os, sys
from PIL import Image

run, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
for sz in sorted(os.listdir(run)):
    d = os.path.join(run, sz)
    if not os.path.isdir(d):
        continue
    shots = sorted(f for f in glob.glob(os.path.join(d, "*.tga")) if not os.path.basename(f).startswith("gif_"))
    ims = []
    for f in shots:
        im = Image.open(f).convert("RGB")
        nm = os.path.splitext(os.path.basename(f))[0]
        im.save(os.path.join(out, "armory_%s_%s.jpg" % (nm, sz)), quality=90)
        ims.append(im)
    if ims:
        w, h = ims[0].size
        k = 3
        s = 640.0 / w
        tw, th = int(w * s), int(h * s)
        rows = (len(ims) + k - 1) // k
        sheet = Image.new("RGB", (tw * k, th * rows))
        for i, im in enumerate(ims):
            sheet.paste(im.resize((tw, th), Image.LANCZOS), ((i % k) * tw, (i // k) * th))
        sheet.save(os.path.join(out, "armory_contact_%s.jpg" % sz), quality=88)
    fr = sorted(glob.glob(os.path.join(d, "gif_*.tga")))
    if fr:
        fs = [Image.open(f).convert("RGB").resize((960, 540), Image.LANCZOS) for f in fr]
        pal = [f.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE) for f in fs]
        pal[0].save(os.path.join(out, "armory_browse.gif"), save_all=True, append_images=pal[1:], duration=750, loop=0, optimize=True)
        print("gif", len(fs), "frames")
print("media ->", out)
