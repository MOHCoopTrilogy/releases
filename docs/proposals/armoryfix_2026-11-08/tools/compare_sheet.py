"""compare_sheet.py <out.jpg> - before / after of the Armory at every tested resolution: per row one gun, per column (resolution x
before/after) the hero box and its slot tile, cropped from the audit frames (armory_audit.py shoot before_<res> / after_<res>)."""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import armory_audit as A  # noqa: E402

RUNS = A.RUNS
RES = [("43s", "4:3 1440x1080"), ("1080", "16:9 1920x1080"), ("219s", "21:9 1920x804"), ("uw", "21:9 3440x1440")]
BEFORE = {"1080": "before", "219s": "before219", "43s": "before_43s", "uw": "before_uw"}
IDS = ["01", "25", "81", "43", "45", "48", "53", "52", "64", "66", "69"]


def frame(tag, g):
    for ext in (".tga", ".jpg"):
        p = os.path.join(RUNS, "armory_%s" % tag, "a_%s%s" % (g, ext))
        if os.path.isfile(p):
            return Image.open(p).convert("RGB")
    return None


def crop(im, r, pad=0):
    W, H = im.size
    x, y, w, h = r
    return im.crop((int((x - pad) * W / 640.0), int((y - pad) * H / 480.0), int((x + w + pad) * W / 640.0), int((y + h + pad) * H / 480.0)))


def main(out):
    R = {d["id"]: d for d in A.roster()}
    SR = A.slot_rects()
    cw, hh, sh_, lab = 300, 116, 70, 14
    cols = [(r, n, s) for r, n in RES for s in ("before", "after")]
    W = 120 + cw * len(cols)
    H = 30 + (hh + sh_ + lab) * len(IDS)
    sh = Image.new("RGB", (W, H), (12, 12, 12))
    d = ImageDraw.Draw(sh)
    for c, (r, n, s) in enumerate(cols):
        d.text((120 + c * cw + 4, 4), "%s  %s" % (n, s.upper()), fill=(255, 210, 90) if s == "after" else (200, 200, 200))
    for k, g in enumerate(IDS):
        y = 30 + k * (hh + sh_ + lab)
        d.text((4, y + 40), "%s %s" % (g, R[g]["name"][:16]), fill="yellow")
        slot = int(R[g]["slots"][0])
        for c, (r, n, s) in enumerate(cols):
            im = frame(BEFORE[r] if s == "before" else "after_%s" % r, g)
            x = 120 + c * cw
            if im is None:
                d.text((x + 4, y + 40), "(no frame)", fill="red")
                continue
            sh.paste(crop(im, A.HERO).resize((cw - 6, hh)), (x, y))
            if slot in SR:
                sh.paste(crop(im, SR[slot]).resize((int(sh_ * 2.2), sh_)), (x, y + hh + 2))
    sh.save(out, quality=88)
    print("wrote", out, sh.size)


if __name__ == "__main__":
    main(sys.argv[1])
