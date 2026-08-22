"""Player-SKIN texture upscale (user-approved 2026-08-21).
Same proven recipe as the 2026-08-19 weapon-variant run: ESRGAN 4x per unique image,
validator (luma correlation >=0.65 + black-output guard) with Lanczos fallback, ship as a
2x supersample, GPU cooldown every 2 images, originals backed up as *.pre_upscale_nobuild
(bug-1917: never overwrite a gitignored binary without a backup).

Scope differs: only textures REFERENCED BY models/player/*.tik surface lines, <=256px, and
NOT already shadowed by an HD .dds in a retail/HD pak (the engine loads .dds before .tga, so
upscaling a shadowed file changes nothing on screen).
"""
import subprocess, os, glob, math, time, shutil, io, re, struct, zipfile, collections
from PIL import Image

ROOT = "C:/mohaa-coop-dev/hzm-mohaa-coop-mod/"
ESR = "C:/mohaa-coop-dev/_tools/realesrgan/realesrgan-ncnn-vulkan.exe"
WORK = os.path.expandvars(r"%TEMP%\claude\C--mohaa-coop-dev\277135cf-ad44-4f7d-b2d4-b293580237c0\scratchpad\upskin")
os.makedirs(WORK, exist_ok=True)
LOG = os.path.join(WORK, "log.txt")

def log(m):
    print(m, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(m + "\n")

# 1. textures referenced by player tiks
skin_tex = set()
for tik in glob.glob(ROOT + "models/player/*.tik"):
    try: d = io.open(tik, encoding="utf-8", errors="replace").read()
    except Exception: continue
    for m in re.finditer(r'surface\s+\S+\s+shader\s+(\S+)', d):
        skin_tex.add(m.group(1).lower().strip())

# 2. HD .dds shadows
shadow = set()
for root in (r'G:\mohaa-gl2\main', r'G:\mohaa-gl2\mainta', r'G:\mohaa-gl2\maintt'):
    for f in sorted(glob.glob(os.path.join(root, '*.pk3'))):
        if 'co-op_hzm' in os.path.basename(f): continue
        try: z = zipfile.ZipFile(f)
        except Exception: continue
        for n in z.namelist():
            ln = n.lower()
            if ln.startswith('textures/') and ln.endswith('.dds'):
                shadow.add(os.path.splitext(os.path.basename(ln))[0])

targets = []
for p in glob.glob(ROOT + "textures/*"):
    b = os.path.basename(p); stem = os.path.splitext(b)[0].lower(); ext = os.path.splitext(b)[1].lower()
    if ext not in ('.tga', '.jpg', '.jpeg'): continue
    if stem not in skin_tex or stem in shadow: continue
    if 'nobuild' in p.lower() or '.bak' in p.lower(): continue
    try:
        with Image.open(p) as im: w, h = im.size
    except Exception: continue
    if max(w, h) <= 256 and min(w, h) >= 32:
        targets.append(p)
log("targets: %d player-skin textures <=256px, not HD-shadowed" % len(targets))

def brightness(img):
    d = list(img.convert("L").resize((64, 64)).getdata()); return sum(d) / len(d)
def corr(a_img, b_img):
    a = list(a_img.convert("L").resize((64, 64)).getdata())
    b = list(b_img.convert("L").resize((64, 64)).getdata())
    ma, mb = sum(a)/len(a), sum(b)/len(b)
    cov = sum((x-ma)*(y-mb) for x, y in zip(a, b))
    va = math.sqrt(sum((x-ma)**2 for x in a)) or 1
    vb = math.sqrt(sum((y-mb)**2 for y in b)) or 1
    return cov/(va*vb)

done = fell = fail = 0
for i, src in enumerate(sorted(targets), 1):
    try: im = Image.open(src)
    except Exception as e:
        log("UNREADABLE %s %s" % (src, e)); fail += 1; continue
    w, hgt = im.size
    alpha = im.split()[3] if im.mode == "RGBA" else None
    rgb = im.convert("RGB")
    ti, to = os.path.join(WORK, "in.png"), os.path.join(WORK, "out.png")
    for f in (ti, to):
        if os.path.exists(f): os.remove(f)
    rgb.save(ti)
    try:
        subprocess.run([ESR, "-i", ti, "-o", to, "-s", "4", "-t", "256", "-j", "1:1:1"],
                       capture_output=True, timeout=300)
    except Exception: pass
    good = False
    if os.path.exists(to):
        up = Image.open(to).convert("RGB")
        good = (corr(rgb, up) >= 0.65) and not (brightness(up) < 8 and brightness(rgb) > 20)
    if good:
        two = up.resize((w*2, hgt*2), Image.LANCZOS)
    else:
        two = rgb.resize((w*2, hgt*2), Image.LANCZOS); fell += 1
        log("FALLBACK(lanczos) %s" % os.path.basename(src))
    if alpha is not None:
        two = two.convert("RGBA"); two.putalpha(alpha.resize((w*2, hgt*2), Image.LANCZOS))
    bak = src + ".pre_upscale_nobuild"
    if not os.path.exists(bak): shutil.copy2(src, bak)
    ext = os.path.splitext(src)[1].lower()
    if ext in (".jpg", ".jpeg"): two.convert("RGB").save(src, quality=95)
    else: (two if alpha is not None else two.convert("RGB")).save(src, format="TGA")
    done += 1
    if done % 2 == 0: time.sleep(10)
    if done % 15 == 0: log("  progress %d/%d (fallback=%d)" % (i, len(targets), fell))
log("DONE: upscaled=%d lanczos_fallback=%d failed=%d of %d" % (done, fell, fail, len(targets)))
