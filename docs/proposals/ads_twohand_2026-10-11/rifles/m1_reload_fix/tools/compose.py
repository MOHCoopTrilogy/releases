"""Before / after media + engine figures from the run_m1.py captures (H:/hzm_work/m1reload/runs/<before>, <after>).

    python compose.py garand gb ga <outdir>
    python compose.py mosin  mb ma <outdir>

Writes  <gun>_reload_ads_before_after_stand.gif     before | after, standing, every 3rd capture frame (48 ms, real time)
        <gun>_reload_ads_before_after_stances.gif   six stances, before | after per stance
        <gun>_reload_ads_stills_stances.jpg          six moments x six stances, before above after
(The figures are the offline ones, vmeasure.py: a frame-minus-reference mask read 34-54 % box cover in the
settled aim itself - the no-viewmodel reference frame does not match the ADS view - so it was dropped.)
Centre box (0.4-0.6 of the picture) drawn in yellow.
"""
import os, sys, glob, json
import numpy as np
from PIL import Image, ImageDraw

RUNS = "H:/hzm_work/m1reload/runs/"
STANCES = ["stand", "crouch", "prone", "standL", "standR", "braced"]
SNAME = {"stand": "stand", "crouch": "crouch", "prone": "prone", "standL": "lean L", "standR": "lean R", "braced": "braced"}
# capture indices (one capture per 16 ms; the reload starts at index 8) of the moments shown on the still sheet -
# the rifle lane's own moments (rb60 / rb53 sheets)
MOMENTS = {
    "garand": [(40, "hand at the pouch"), (65, "clip brought up"), (76, "clip on the action"), (84, "pushed down"),
               (113, "hand on the op-rod"), (136, "back on the aim")],
    "mosin": [(34, "bolt opened"), (70, "pouch"), (100, "charger brought up"), (108, "charger in the guides"),
              (156, "hand on the bolt"), (190, "back on the aim")],
}
SPAN = {"garand": (0, 150), "mosin": (0, 215)}


def frames(sess, gun, st):
    fs = sorted(glob.glob(RUNS + "%s/ab__%s__%s__%s__reload__after__[0-9][0-9][0-9][0-9].jpg" % (sess, sess, gun, st)))
    ref = glob.glob(RUNS + "%s/ab__%s__%s__%s__reload__after__ref.jpg" % (sess, sess, gun, st))
    return fs, (ref[0] if ref else None)


def boxed(im):
    d = ImageDraw.Draw(im)
    W, H = im.size
    d.rectangle((int(W * .4), int(H * .4), int(W * .6), int(H * .6)), outline=(255, 225, 0), width=2)
    return im


def label(im, txt, col=(255, 235, 120)):
    d = ImageDraw.Draw(im)
    w = 7 * len(txt) + 8
    d.rectangle((0, 0, w, 14), fill=(0, 0, 0))
    d.text((4, 1), txt, fill=col)
    return im


def tile(path, w, txt=None):
    im = boxed(Image.open(path).convert("RGB"))
    im = im.resize((w, w * im.height // im.width), Image.LANCZOS)
    return label(im, txt) if txt else im


def figures(fs, ref, a, b):
    """viewmodel mask = |frame - reference without the viewmodel| > 40 (any channel)"""
    R0 = np.asarray(Image.open(ref).convert("RGB")).astype(np.int16)
    H, W = R0.shape[:2]
    out = []
    for p in fs[a:b]:
        F = np.asarray(Image.open(p).convert("RGB")).astype(np.int16)
        m = (np.abs(F - R0).max(2) > 40)
        m[:int(H * .06)] = False                      # compass / HUD strip
        m[int(H * .86):, :int(W * .12)] = False       # HUD bottom-left
        m[int(H * .86):, int(W * .9):] = False        # HUD bottom-right
        bx = m[int(H * .4):int(H * .6), int(W * .4):int(W * .6)].mean() * 100
        rows = np.where(m.mean(1) > 0.01)[0]
        out.append(dict(vm=round(float(m.mean() * 100), 2), box=round(float(bx), 2),
                        top=round(float(rows[0]) / H, 3) if len(rows) else None))
    return out


def main(gun, sb, sa, od):
    os.makedirs(od, exist_ok=True)
    a0, a1 = SPAN[gun]
    data = {}
    for st in STANCES:
        fb, rb = frames(sb, gun, st)
        fa, ra = frames(sa, gun, st)
        if not fb or not fa:
            print("missing", st, len(fb), len(fa))
            continue
        data[st] = (fb, rb, fa, ra)
    # standing GIF, before | after
    if "stand" in data:
        fb, _, fa, _ = data["stand"]
        n = min(len(fb), len(fa), a1)
        gif = []
        for i in range(a0, n, 3):
            L = tile(fb[i], 420, "BEFORE (shipped)  %d" % i)
            Rr = tile(fa[i], 420, "AFTER (staged fix)  %d" % i)
            S = Image.new("RGB", (844, L.height), (20, 20, 20))
            S.paste(L, (0, 0)); S.paste(Rr, (424, 0))
            gif.append(S.convert("P", palette=Image.ADAPTIVE, colors=96))
        p = os.path.join(od, "%s_reload_ads_before_after_stand.gif" % gun)
        gif[0].save(p, save_all=True, append_images=gif[1:], duration=[48] * (len(gif) - 1) + [900], loop=0, optimize=True)
        print(p, len(gif))
    # all-stance GIF: 3 rows x (before, after, before, after)
    W = 220
    gif = []
    n = min(min(len(v[0]), len(v[2])) for v in data.values())
    n = min(n, a1)
    sts = [s for s in STANCES if s in data]
    for i in range(a0, n, 4):
        tiles = []
        for st in sts:
            fb, _, fa, _ = data[st]
            tiles += [tile(fb[i], W, "%s before" % SNAME[st]), tile(fa[i], W, "%s after" % SNAME[st])]
        th = tiles[0].height
        S = Image.new("RGB", (W * 4 + 6, th * ((len(tiles) + 3) // 4) + 2), (20, 20, 20))
        for k, t in enumerate(tiles):
            S.paste(t, ((k % 4) * W + (6 if k % 4 >= 2 else 0), (k // 4) * th))
        gif.append(S.convert("P", palette=Image.ADAPTIVE, colors=96))
    p = os.path.join(od, "%s_reload_ads_before_after_stances.gif" % gun)
    gif[0].save(p, save_all=True, append_images=gif[1:], duration=[64] * (len(gif) - 1) + [900], loop=0, optimize=True)
    print(p, len(gif))
    # still sheet: rows = stance (before row, after row), columns = moments
    W = 300
    rows = []
    for st in sts:
        fb, _, fa, _ = data[st]
        for tag, fl in (("BEFORE", fb), ("AFTER", fa)):
            rows.append([tile(fl[min(i, len(fl) - 1)], W, "%s %s - %s (%d)" % (tag, SNAME[st], nm, i)) for i, nm in MOMENTS[gun]])
    th = rows[0][0].height
    cols = len(rows[0])
    S = Image.new("RGB", (W * cols, th * len(rows) + 3 * (len(rows) // 2)), (255, 255, 255))
    y = 0
    for r, row in enumerate(rows):
        for c, t in enumerate(row):
            S.paste(t, (c * W, y))
        y += th + (3 if r % 2 else 0)
    p = os.path.join(od, "%s_reload_ads_stills_stances.jpg" % gun)
    S.save(p, quality=85)
    print(p, S.size)


if __name__ == "__main__":
    main(*sys.argv[1:5])
