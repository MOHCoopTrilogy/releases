"""[QA 2026-11-09] The Panzerfaust source's warning labels read "Starker Feuerstahl !" - a misspelling of the real marking
("Achtung! Starker Feuerstrahl!"). Re-letter both labels "Starker Feuerstrahl !" in the label's own red, in a condensed DIN-style
face (Bahnschrift SemiBold Condensed, the closest Windows face to DIN 1451), fitted to the old text's box and multiplied by the
label's own wear so the new letters sit IN the paint, not on it. Arrows, "Vorsicht !" and the rest of the map are untouched.
    python pzf_decal.py <BaseColor in> <out.png> [--sheet sheet.jpg]
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

Image.MAX_IMAGE_PIXELS = None
# (crop box in the 4096 map, rotated 180 deg on the tube, x where the arrow starts in the upright crop)
LABELS = [((40, 1600, 760, 1730), True), ((140, 3030, 880, 3160), False)]
TEXT = "Starker Feuerstrahl !"


def font(size):
    f = ImageFont.truetype("bahnschrift.ttf", size)
    try:
        f.set_variation_by_name("Condensed")
    except Exception:
        pass
    return f


def fix(crop):
    a = np.asarray(crop).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    red = (r - g > 45) & (r - b > 45)
    # the arrow = the right-most red blob; the text = red pixels left of the gap before it
    cols = red.sum(0)
    xs = np.where(cols > 0)[0]
    d = np.diff(xs)
    gaps = np.where(d > 12)[0]
    text = red.copy()
    if len(gaps):
        # the arrow is the end cluster behind the WIDEST gap (it points right on one label, left on the other once upright)
        first, last = gaps[0], gaps[-1]
        if d[first] >= d[last]:
            text[:, :xs[first] + 6] = False
        else:
            text[:, xs[last] + 6:] = False
    ys, xs2 = np.where(text)
    box = (xs2.min(), ys.min(), xs2.max(), ys.max())
    lum = a[text].mean(-1)
    redcol = a[text][lum <= np.percentile(lum, 35)].mean(0)      # the solid paint, not the anti-aliased edge
    # erase: paper colour = the label's non-red pixels, smoothed, with the grime (luminance ratio) kept
    paper = Image.fromarray(np.where(red[..., None], 0, a).astype(np.uint8))
    m = Image.fromarray((~red * 255).astype(np.uint8))
    pb = np.asarray(paper.filter(ImageFilter.BoxBlur(9))).astype(np.float32)
    mb = np.asarray(m.filter(ImageFilter.BoxBlur(9))).astype(np.float32)[..., None] / 255.0
    fill = pb / np.maximum(mb, 1e-3)
    dil = np.asarray(Image.fromarray((text * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    out = a.copy()
    out[dil] = fill[dil]
    # draw the corrected text into the same box (cap height = the box height), condensed to the box width
    h = box[3] - box[1] + 1; w = box[2] - box[0] + 1
    f = font(int(h * 1.32))
    tw, th = f.getbbox(TEXT)[2] - f.getbbox(TEXT)[0], f.getbbox(TEXT)[3] - f.getbbox(TEXT)[1]
    lay = Image.new('L', (tw + 8, th + 8), 0)
    ImageDraw.Draw(lay).text((4 - f.getbbox(TEXT)[0], 4 - f.getbbox(TEXT)[1]), TEXT, font=f, fill=255)
    lay = lay.crop(lay.getbbox()).resize((w, h), Image.LANCZOS)
    al = np.zeros(red.shape, np.float32)
    al[box[1]:box[1] + h, box[0]:box[0] + w] = np.asarray(lay).astype(np.float32) / 255.0
    # wear: where the original paint was chipped (paper lighter than the label mean), the new paint is chipped too
    wear = np.clip(fill.mean(-1) / (np.median(fill[~red].mean(-1)) + 1e-3), 0.6, 1.1)
    paint = redcol[None, None, :] * wear[..., None]
    out = out * (1 - al[..., None]) + paint * al[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), box


def main():
    src, dst = sys.argv[1], sys.argv[2]
    im = Image.open(src).convert('RGB')
    for (box, flip) in LABELS:
        c = im.crop(box)
        if flip:
            c = c.rotate(180)
        c2, tb = fix(c)
        if flip:
            c2 = c2.rotate(180)
        im.paste(c2, box[:2])
        print('label', box, 'text box', tb)
    im.save(dst)


if __name__ == '__main__':
    main()
