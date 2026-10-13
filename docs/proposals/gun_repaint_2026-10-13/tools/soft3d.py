"""Small software renderer for QA before the engine: orthographic, z-buffered, textured, with a soft directional
light (roughly what rgbGen lightingSpherical gives). Bone-space positions as stored in the skd (rigid parts only).

    img = render([(surface_dict, texture_rgb_float), ...], yaw, pitch, scale=px per unit, size=(W, H))
"""
import numpy as np
from scipy import ndimage as ndi


def rot(yaw, pitch, roll=0.0):
    y, p, r = np.radians([yaw, pitch, roll])
    Rz = np.array([[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    Ry = np.array([[np.cos(r), 0, np.sin(r)], [0, 1, 0], [-np.sin(r), 0, np.cos(r)]])
    return Rx @ Rz @ Ry


def render(parts, yaw, pitch, scale=20.0, size=None, roll=0.0, bg=(96, 104, 112), light=(0.35, -0.5, 0.8),
           amb=0.55, centre=None, ss=2, wrap=False, gain=1.0):
    R = rot(yaw, pitch, roll)
    allp = np.concatenate([s["pos"] for s, _ in parts]) @ R.T
    lo = allp.min(0); hi = allp.max(0)
    c = (lo + hi) / 2 if centre is None else np.asarray(centre) @ R.T
    if size is None:
        size = (int((hi[0] - lo[0]) * scale) + 40, int((hi[1] - lo[1]) * scale) + 40)
    W, H = size[0] * ss, size[1] * ss
    sc = scale * ss
    col = np.zeros((H, W, 3), np.float32) + np.array(bg, np.float32)
    zb = np.full((H, W), -1e9, np.float32)
    Lv = np.asarray(light, float); Lv /= np.linalg.norm(Lv)
    for s, tex in parts:
        th, tw = tex.shape[:2]
        P = s["pos"] @ R.T
        N = s["nrm"] @ R.T
        X = (P[:, 0] - c[0]) * sc + W / 2; Y = H / 2 - (P[:, 1] - c[1]) * sc; Z = P[:, 2]
        for t in s["tris"]:
            x, y, z = X[t], Y[t], Z[t]
            x0 = max(0, int(np.floor(x.min()))); x1 = min(W, int(np.ceil(x.max())) + 1)
            y0 = max(0, int(np.floor(y.min()))); y1 = min(H, int(np.ceil(y.max())) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(den) < 1e-9:
                continue
            xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
            w0 = ((y[1] - y[2]) * (xs - x[2]) + (x[2] - x[1]) * (ys - y[2])) / den
            w1 = ((y[2] - y[0]) * (xs - x[2]) + (x[0] - x[2]) * (ys - y[2])) / den
            w2 = 1 - w0 - w1
            m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not m.any():
                continue
            zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
            sub = zb[y0:y1, x0:x1]
            m &= zz > sub
            if not m.any():
                continue
            Wt = np.stack([w0[m], w1[m], w2[m]], -1)
            uv = Wt @ s["uv"][t]
            n = Wt @ N[t]
            n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
            u = uv[:, 0] * tw - 0.5; v = uv[:, 1] * th - 0.5
            if wrap:
                u = np.mod(u, tw); v = np.mod(v, th)
            px = np.stack([ndi.map_coordinates(tex[..., k], [v, u], order=1, mode="wrap" if wrap else "nearest")
                           for k in range(3)], -1)
            lam = amb + (1 - amb) * np.clip(n @ Lv, 0, 1) * 1.6
            sub[m] = zz[m]
            col[y0:y1, x0:x1][m] = px * lam[:, None] * gain
    if ss > 1:
        col = col.reshape(H // ss, ss, W // ss, ss, 3).mean((1, 3))
    return np.clip(col, 0, 255)
