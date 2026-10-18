"""make_sheets.py placements|zones - contact sheets from the harness screenshots (tools/runs/<session>/*.jpg).
placements: one tile per placed switch, lit shot unless it is too dark (then the fullbright one), label = map + switch number.
zones: one tile per defend zone (marker visible), label = map + zone number + name."""
import glob, os, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageStat

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
MEDIA = os.path.join(os.path.dirname(HERE), "media")
MAPS_AP = "e3l1 e3l2 m1l1 m2l1 m3l2 m4l1 m4l2 t1l1 t3l1".split()
MAPS_CZ = "m1l1 m4l1 m1l2a m2l1 m3l2 m5l1a m6l3b t1l2 t2l1 t3l1 e3l1 e3l2".split()


def font(sz):
    for f in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def bright(im):
    return ImageStat.Stat(im.convert("L")).mean[0]


def tile(im, w, h, label):
    im = im.convert("RGB").resize((w, h))
    d = ImageDraw.Draw(im)
    f = font(max(12, h // 14))
    tw = d.textlength(label, font=f)
    d.rectangle([0, 0, tw + 12, h // 11 + 8], fill=(0, 0, 0))
    d.text((6, 3), label, fill=(255, 255, 255), font=f)
    return im


def sheet(tiles, cols, w, h, out):
    rows = (len(tiles) + cols - 1) // cols
    S = Image.new("RGB", (cols * w, rows * h), (20, 20, 20))
    for i, t in enumerate(tiles):
        S.paste(t, ((i % cols) * w, (i // cols) * h))
    os.makedirs(MEDIA, exist_ok=True)
    S.save(out, quality=88)
    print(out, S.size, len(tiles), "tiles")


def find(sess, stem):
    c = glob.glob(os.path.join(RUNS, sess, stem + ".*"))
    c = [x for x in c if x.lower().endswith((".jpg", ".png", ".jpeg"))]
    return c[0] if c else None


def placements():
    tiles = []
    for m in MAPS_AP:
        sess = "ap_v2" + m
        for i in range(1, 9):
            lit = find(sess, "v2%s_%s_%d_lit" % (m, m, i))
            if not lit:
                break
            fb = find(sess, "v2%s_%s_%d_fb" % (m, m, i))
            im = Image.open(lit)
            tag = ""
            if bright(im) < 45 and fb:
                im = Image.open(fb)
                tag = " (fullbright)"
            tiles.append(tile(im, 480, 270, "%s  switch %d%s" % (m, i, tag)))
    sheet(tiles, 4, 480, 270, os.path.join(MEDIA, "placements_v2.jpg"))


def zones():
    tiles = []
    import json
    Z = json.load(open("C:/mohaa-coop-dev/docs/tools/counter_zones.json"))
    for m in MAPS_CZ:
        sess = "ap_cz" + m if False else "cz_cz" + m
        n = len(Z.get(m, []))
        for i in range(1, max(n, 1) + 1):
            stem = "cz%s_%s_z%d" % (m, m, i) if n else "cz%s_%s_zfb" % (m, m)
            f = find(sess, stem)
            if not f:
                continue
            nm = Z[m][i - 1]["name"] if n else "runtime zone"
            tiles.append(tile(Image.open(f), 360, 203, "%s  zone %d: %s" % (m, i, nm)))
    sheet(tiles, 6, 360, 203, os.path.join(MEDIA, "zones_v2.jpg"))


if __name__ == "__main__":
    {"placements": placements, "zones": zones}[sys.argv[1]]()
