"""Offline textured side / top / front views of the new C96 skd at a clip frame (no engine): reads the .skd back with the
project's reader (so it also proves the file parses), poses bones from a .skc frame, z-buffer + lambert.
    python view_skd.py out.jpg [--ov ship] [--clip c96n_fire.skc] [--frames 0,2,4] [--views side,top,front,34] [--tex path.jpg] [--w 900]
"""
import os, sys, argparse
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(1, r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\tools')
import skdlib as S
HERE = os.path.dirname(os.path.abspath(__file__))
SH = os.path.join(HERE, '..', 'ship')


def load_gun(skdp):
    m = S.read_skd(open(skdp, 'rb').read())
    return m


def pose(m, skc, f):
    a = S.read_skc(open(skc, 'rb').read())
    bn = {}
    for b in m.bones:
        i = a.channels.index(b.name + ' pos'); j = a.channels.index(b.name + ' rot')
        pos = S.skc_channel(a, f, i); q = S.skc_channel(a, f, j)
        bn[b.index] = (np.array(S.quat_to_mat3(q)), np.array(pos[:3]))
    return bn


def tris_world(m, bn):
    out = []
    for s in m.surfaces:
        T = np.frombuffer(s.tri_bytes, '<i4').reshape(-1, 3)
        P = np.zeros((len(s.verts), 3)); N = np.zeros((len(s.verts), 3)); UV = np.zeros((len(s.verts), 2))
        for i, (n, uv, wl, _ml) in enumerate(s.verts):
            bi, bw, off = wl[0]
            Mx, t = bn[bi]
            P[i] = np.array(off) @ Mx + t
            N[i] = np.array(n) @ Mx
            UV[i] = uv
        out.append((T, P, N, UV))
    return out


def render(surfs, tex, view, W, H, light=(0.4, -0.5, -0.7), boxes=()):
    P_all = np.vstack([s[1] for s in surfs])
    ctr = (P_all.min(0) + P_all.max(0)) / 2
    # gun frame: +x muzzle, +y right, +z down.  views: camera axes (right, up, toward-camera)
    if view == 'side':     # looking at the gun's LEFT side?  camera on the +y (right) side looking toward -y: right = -x..; show muzzle left like the look sheet
        R = np.array([-1.0, 0, 0]); U = np.array([0, 0, -1.0]); Fw = np.array([0, 1.0, 0])
    elif view == 'sideL':
        R = np.array([1.0, 0, 0]); U = np.array([0, 0, -1.0]); Fw = np.array([0, -1.0, 0])
    elif view == 'top':
        R = np.array([1.0, 0, 0]); U = np.array([0, -1.0, 0]); Fw = np.array([0, 0, 1.0])
    elif view == 'front':
        R = np.array([0, 1.0, 0]); U = np.array([0, 0, -1.0]); Fw = np.array([1.0, 0, 0])
    else:                  # 3/4 from front-right-above
        a = np.radians(35); b = np.radians(-22)
        Fw = -np.array([np.cos(a) * np.cos(b), -np.sin(a) * np.cos(b), -np.sin(b)])
        Fw = np.array([-0.55, 0.65, 0.35]); Fw /= np.linalg.norm(Fw)
        R = np.cross(np.array([0, 0, -1.0]), Fw); R /= np.linalg.norm(R); U = np.cross(Fw, R)
    ext = np.abs((P_all - ctr) @ np.stack([R, U], 1)).max()
    sc = 0.46 * min(W, H) / ext
    img = np.full((H, W, 3), 0.62, np.float32); img[:] = np.array([0.58, 0.61, 0.66])
    zb = np.full((H, W), -1e9, np.float32)
    L = np.array(light, float); L /= np.linalg.norm(L)
    th, tw = tex.shape[:2]
    for (T, P, N, UV) in surfs:
        X = (P - ctr) @ R * sc + W / 2; Y = -((P - ctr) @ U) * sc + H / 2; Z = (P - ctr) @ Fw
        Z = -Z     # larger = nearer the camera (camera looks along +Fw)
        Nn = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        lam = np.clip(Nn @ -L, 0, 1) * 0.55 + np.clip(-(Nn @ Fw), 0, 1) * 0.35 + 0.35
        for t in T:
            x = X[t]; y = Y[t]
            x0, x1 = int(max(0, np.floor(x.min()))), int(min(W - 1, np.ceil(x.max())))
            y0, y1 = int(max(0, np.floor(y.min()))), int(min(H - 1, np.ceil(y.max())))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(den) < 1e-9:
                continue
            l0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
            l1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
            l2 = 1 - l0 - l1
            m = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
            if not m.any():
                continue
            z = l0 * Z[t[0]] + l1 * Z[t[1]] + l2 * Z[t[2]]
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            m &= z > sub
            if not m.any():
                continue
            u = l0 * UV[t[0], 0] + l1 * UV[t[1], 0] + l2 * UV[t[2], 0]
            v = l0 * UV[t[0], 1] + l1 * UV[t[1], 1] + l2 * UV[t[2], 1]
            c = tex[(np.clip(v, 0, 1) * (th - 1)).astype(int) % th, (np.clip(u, 0, 1) * (tw - 1)).astype(int) % tw]
            sh = l0 * lam[t[0]] + l1 * lam[t[1]] + l2 * lam[t[2]]
            col = np.clip(c * sh[..., None] * 1.6, 0, 1)      # x1.6: the engine's lightingSpherical is brighter than lambert here
            reg = img[y0:y1 + 1, x0:x1 + 1]
            reg[m] = col[m]
            sub[m] = z[m]
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for (b0, b1, colr) in boxes:
        pts = [np.array([x, y, z]) for x in (b0[0], b1[0]) for y in (b0[1], b1[1]) for z in (b0[2], b1[2])]
        pr = [(float((p - ctr) @ R * sc + W / 2), float(-((p - ctr) @ U) * sc + H / 2)) for p in pts]
        for i in range(8):
            for j in range(i + 1, 8):
                if bin(i ^ j).count('1') == 1:
                    d.line([pr[i], pr[j]], fill=colr, width=1)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('--clip', default='c96n_idle.skc'); ap.add_argument('--frames', default='0')
    ap.add_argument('--views', default='sideL,top,front,34'); ap.add_argument('--tex', default=None); ap.add_argument('--w', type=int, default=640)
    ap.add_argument('--skd', default=None); ap.add_argument('--box', action='append', default=[])
    a = ap.parse_args()
    md = os.path.join(SH, 'models', 'weapons', 'coop_c96n')
    m = load_gun(a.skd or os.path.join(md, 'c96n.skd'))
    tex = np.asarray(Image.open(a.tex or os.path.join(SH, 'textures', 'models', 'weapons', 'coop_c96n', 'coop_c96n.jpg')).convert('RGB')).astype(np.float32) / 255.0
    W, H = a.w, int(a.w * 0.62)
    rows = []
    for f in [int(x) for x in a.frames.split(',')]:
        bn = pose(m, os.path.join(md, a.clip), f)
        surfs = tris_world(m, bn)
        tiles = []
        for v in a.views.split(','):
            bx = [(np.array([float(q) for q in b.split(',')[:3]]), np.array([float(q) for q in b.split(',')[3:6]]), (255, 60, 60)) for b in a.box]
            im = render(surfs, tex, v, W, H, boxes=bx)
            ImageDraw.Draw(im).text((4, 3), '%s f%d %s' % (v, f, a.clip), fill=(255, 255, 0))
            tiles.append(im)
        rows.append(tiles)
    cols = len(rows[0])
    S2 = Image.new('RGB', (W * cols, H * len(rows)))
    for r, tiles in enumerate(rows):
        for c, im in enumerate(tiles):
            S2.paste(im, (c * W, r * H))
    S2.save(a.out, quality=90)
    print(a.out, S2.size, 'surfaces', len(m.surfaces), 'bones', [b.name for b in m.bones])


if __name__ == '__main__':
    main()
