"""make_evidence.py - turn G:\\mohaa-wwtest\\runs_waterfix into the before/after sheets, the pan GIF and the GPU table.

    python make_evidence.py        -> evidence/*.jpg, evidence/canal_pan_before_after.gif, evidence/gpu.md
"""
import glob, json, os, re
from PIL import Image, ImageDraw, ImageFont

RUNS = r"G:\mohaa-wwtest\runs_waterfix"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
os.makedirs(OUT, exist_ok=True)
try:
    FONT = ImageFont.truetype("arialbd.ttf", 22)
except OSError:
    FONT = ImageFont.load_default()


def shot(tag, name):
    for ext in (".tga", ".jpg", ".png"):
        hits = glob.glob(os.path.join(RUNS, tag, "*%s_%s%s" % (tag, name, ext)))
        if hits:
            return Image.open(hits[0]).convert("RGB")
    return None


def label(im, text):
    im = im.copy()
    d = ImageDraw.Draw(im)
    w = d.textlength(text, font=FONT)
    d.rectangle([0, 0, w + 16, 34], fill=(0, 0, 0))
    d.text((8, 5), text, fill=(255, 255, 255), font=FONT)
    return im


def pair(a, b, la, lb, path, quality=90):
    W, H = a.size
    im = Image.new("RGB", (W * 2 + 6, H), (255, 255, 255))
    im.paste(label(a, la), (0, 0))
    im.paste(label(b, lb), (W + 6, 0))
    im.save(path, quality=quality)


def main():
    summ = {}
    for nf in glob.glob(os.path.join(RUNS, "*", "notes.json")):
        n = json.load(open(nf))
        n["tag"] = os.path.basename(os.path.dirname(nf))     # run1_* = the first AFTER build (c3ece61b)
        summ[n["tag"]] = n
    made = []
    for scene in ("wet_day", "wet_night", "river", "canal"):
        o, w = "%s_old" % scene, "%s_new" % scene
        if o not in summ or w not in summ:
            continue
        for k, what in (("F", "wet film"), ("P", "wet + puddles"), ("W", "water only")):
            a, b = shot(o, k), shot(w, k)
            if a is None or b is None:
                continue
            p = os.path.join(OUT, "%s_%s_before_after.jpg" % (scene, k))
            pair(a, b, "BEFORE (live v1.10.13) - %s" % what, "AFTER (waterfix) - %s" % what, p)
            made.append(p)
        d, g = shot(w, "D"), shot(w, "DBG")
        if d is not None and g is not None:
            p = os.path.join(OUT, "%s_debug_coverage.jpg" % scene)
            pair(d, g, "dry (wet off)", "AFTER r_hzmWetDebug: red sheltered / green sky-lit / blue puddle", p)
            made.append(p)
    a, b = shot("canal_new", "P"), shot("canal_new_msaa0", "P")
    if a is not None and b is not None:
        p = os.path.join(OUT, "canal_P_msaa8_vs_off.jpg")
        pair(a, b, "AFTER, MSAA 8x", "AFTER, MSAA off", p)
        made.append(p)
    # the pan GIF: BEFORE | AFTER side by side, the lower 70 % of the frame (the wet ground, the fence posts and the
    # canal), 0.45 scale, 15 fps, one pass (no ping-pong) - kept under 20 MB
    frames = []
    for k in range(48):
        a, b = shot("canal_old", "pan_%02d" % k), shot("canal_new", "pan_%02d" % k)
        if a is None or b is None:
            break
        W, H = a.size
        box = (0, int(H * 0.30), W, H)
        sw, sh = int(W * 0.45), int((H - box[1]) * 0.45)
        a = a.crop(box).resize((sw, sh), Image.LANCZOS)
        b = b.crop(box).resize((sw, sh), Image.LANCZOS)
        im = Image.new("RGB", (sw * 2 + 4, sh), (255, 255, 255))
        im.paste(label(a, "BEFORE"), (0, 0))
        im.paste(label(b, "AFTER"), (sw + 4, 0))
        frames.append(im)
    if frames:
        p = os.path.join(OUT, "canal_pan_before_after.gif")
        q = [f.quantize(colors=192, method=Image.MEDIANCUT, dither=Image.NONE) for f in frames]
        q[0].save(p, save_all=True, append_images=q[1:], duration=66, loop=0, optimize=True)
        made.append(p)
    # GPU ms
    rows = ["| run | MSAA | renderer md5 | feature off: frame / main p50 (ms) | feature on: frame / main p50 (ms) | on - off main (ms) |",
            "|---|---|---|---|---|---|"]
    for tag in sorted(summ):
        n = summ[tag]
        g = n.get("gpu", [])
        vals = {}
        cur = None
        for line in g:
            m = re.search(r"WFGPU (\w+)", line)
            if m:
                cur = m.group(1)
                continue
            m = re.search(r"frame p50=([\d.]+) p99=([\d.]+).*main p50=([\d.]+) p99=([\d.]+)", line)
            if m and cur:
                vals[cur] = tuple(float(x) for x in m.groups())
                cur = None
        if "off" in vals and "on" in vals:
            rows.append("| %s | %s | %s | %.3f / %.3f | %.3f / %.3f | %+.3f |" % (
                tag, n.get("msaa"), n.get("renderer_md5", "")[:8], vals["off"][0], vals["off"][2],
                vals["on"][0], vals["on"][2], vals["on"][2] - vals["off"][2]))
        else:
            rows.append("| %s | %s | %s | %s | | |" % (tag, n.get("msaa"), n.get("renderer_md5", "")[:8], n.get("error", "no GPUTIME")))
    open(os.path.join(OUT, "gpu.md"), "w").write("\n".join(rows) + "\n")
    for p in made:
        print(p, os.path.getsize(p) // 1024, "KB")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
