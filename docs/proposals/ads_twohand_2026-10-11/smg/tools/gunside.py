"""A gun mesh from its LEFT side, its RIGHT side and from above, near-orthographic, with a ruler in the weapon-tag frame
(x forward, y right, z down; u) - where is the cocking handle / bolt / slot on THIS mesh? Optional markers.

    python gunside.py <tik> <out.jpg> [--anim idle:0] [--x -4,32] [--mark x,y,z[,label] ...] [--pak overlay.pk3]
"""
import sys, os, argparse
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
import raster
os.chdir(_c)
PR = V.PR
from PIL import Image, ImageDraw
BG = (206, 212, 218)


def view(g, kind, x0, x1, W=1100):
    """kind: 'left' (camera on the -y side), 'right', 'top' (camera above, muzzle to the right)"""
    P = np.vstack([s['P'] for s in g['surfs']])
    P = P[(P[:, 0] >= x0) & (P[:, 0] <= x1)]
    cen = np.array([(x0 + x1) / 2.0, (P[:, 1].min() + P[:, 1].max()) / 2.0, (P[:, 2].min() + min(P[:, 2].max(), P[:, 2].min() + 0.42 * (x1 - x0))) / 2.0])
    span = (x1 - x0)
    dist = 400.0
    fov = np.degrees(2 * np.arctan(span / 2.0 / dist))
    H = int(W * 0.42)
    # gungeo frame: +x muzzle, +y right, +z DOWN. The raster wants an up vector.
    if kind == 'left':
        eye, up = cen + np.array([0, -dist, 0.0]), np.array([0, 0, -1.0])
    elif kind == 'right':
        eye, up = cen + np.array([0, dist, 0.0]), np.array([0, 0, -1.0])
    else:
        eye, up = cen + np.array([0, 0, -dist]), np.array([0, -1.0, 0]) if False else np.array([0, 1.0, 0])
    rgb, ids, dep = raster.render({'surfs': g['surfs']}, eye, cen, up, fov=fov, W=W, H=H, bg=BG, znear=1.0, tex=True)
    im = Image.fromarray(rgb.astype(np.uint8))
    return im, cen, span, eye, up


def to_px(p, kind, cen, span, W, H):
    s = W / span
    if kind == 'left':
        return (W / 2 + (p[0] - cen[0]) * s * (1), H / 2 + (p[2] - cen[2]) * s)
    if kind == 'right':
        return (W / 2 - (p[0] - cen[0]) * s, H / 2 + (p[2] - cen[2]) * s)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tik'); ap.add_argument('out'); ap.add_argument('--anim', default='idle:0'); ap.add_argument('--x', default=None)
    ap.add_argument('--mark', action='append', default=[]); ap.add_argument('--w', type=int, default=1100)
    a = ap.parse_args()
    an, fr = a.anim.split(':')
    g = PR.gungeo.load_gun(a.tik, anim=an, frame=int(fr))
    P = np.vstack([s['P'] for s in g['surfs']])
    x0, x1 = ([float(v) for v in a.x.split(',')] if a.x else (P[:, 0].min() - 1, P[:, 0].max() + 1))
    ims = []
    for kind in ('left', 'right', 'top'):
        im, cen, span, eye, up = view(g, kind, x0, x1, a.w)
        W, H = im.size
        d = ImageDraw.Draw(im)
        # which way does x run in this picture? project two points through the same camera as a check
        s = W / span
        flip = {'left': 1, 'right': -1, 'top': 1}[kind]
        # determine the picture's x direction from the rendered silhouette is fragile: use the camera basis
        fwd = cen - eye; fwd /= np.linalg.norm(fwd)
        right = np.cross(fwd, up); right /= np.linalg.norm(right)
        upv = np.cross(right, fwd)

        def px(p):
            q = np.asarray(p, float) - cen
            return (W / 2 + (q @ right) * s, H / 2 - (q @ upv) * s)
        for xv in range(int(np.ceil(x0)), int(x1) + 1):
            if xv % 2 == 0:
                u, _ = px((xv, cen[1], cen[2]))
                d.line((u, H - 14, u, H - 4), fill=(0, 0, 0))
                d.text((u - 6, H - 26), str(xv), fill=(0, 0, 0))
        if kind != 'top':
            for zv in range(int(np.ceil(P[:, 2].min())), int(P[:, 2].max()) + 1):
                if zv % 2 == 0:
                    _, v = px((cen[0], cen[1], zv))
                    d.line((2, v, 10, v), fill=(0, 0, 0)); d.text((12, v - 5), 'z%d' % zv, fill=(0, 0, 0))
        else:
            for yv in range(int(np.ceil(P[:, 1].min())), int(P[:, 1].max()) + 1):
                _, v = px((cen[0], yv, cen[2]))
                d.line((2, v, 10, v), fill=(0, 0, 0)); d.text((12, v - 5), 'y%d' % yv, fill=(0, 0, 0))
        for mk in a.mark:
            t = mk.split(',')
            p = [float(v) for v in t[:3]]
            u, v = px(p)
            d.ellipse((u - 4, v - 4, u + 4, v + 4), outline=(255, 0, 0), width=2)
            if len(t) > 3:
                d.text((u + 6, v - 6), t[3], fill=(255, 0, 0))
        d.text((4, 2), '%s  %s  %s' % (os.path.basename(a.tik), kind, a.anim), fill=(0, 0, 0))
        ims.append(im)
    S = Image.new('RGB', (ims[0].width, sum(i.height for i in ims)), 'white')
    y = 0
    for im in ims:
        S.paste(im, (0, y)); y += im.height
    S.save(a.out, quality=90)
    print(a.out)
    for s_ in g['surfs']:
        print('  %-14s %4d verts  min %s max %s' % (s_['name'], len(s_['P']), np.round(s_['P'].min(0), 2), np.round(s_['P'].max(0), 2)))


if __name__ == '__main__':
    main()
