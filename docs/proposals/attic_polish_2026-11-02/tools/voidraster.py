"""voidraster.py - the fast form of voidtrace.py (same scenes, models, poses, camera, report): every triangle is clipped to the
near plane, projected and FILLED (PIL); a pixel no room triangle covers is the void. Weather layers (hzm_wx_*) are drawn first in
their own colour and the room over them: a weather pixel whose ray does not pass through the gable pane or the skylight is a leak.
~0.2-0.5 s a frame instead of ~5-10 s.  Same command line as voidtrace.py (--grid = image width)."""
import json, math, os, re, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import voidtrace as V  # noqa: E402


def cam(pose, aspect, w):
    x, y, z, pitch, yaw, _r, fov = pose
    h = max(8, int(round(w / aspect)))
    pr, yr = math.radians(pitch), math.radians(yaw)
    f = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), -math.sin(pr)])
    r = np.array([math.sin(yr), -math.cos(yr), 0.0])
    u = np.cross(r, f)
    ty = math.tan(math.radians(fov / 2))
    return np.array([x, y, z]), f, r, u, ty * aspect, ty, w, h


def raster(T, c, mask_img, col):
    o, f, r, u, tx, ty, w, h = c
    d = T - o[None, None, :]
    zc = d @ f
    xc = d @ r
    yc = d @ u
    near = 0.5
    dr = ImageDraw.Draw(mask_img)

    def px(x, y, z):
        return ((x / z / tx + 1) * 0.5 * w, (1 - y / z / ty) * 0.5 * h)

    allin = (zc > near).all(1)
    for k in np.nonzero(allin)[0]:
        pts = [px(xc[k, i], yc[k, i], zc[k, i]) for i in range(3)]
        dr.polygon(pts, fill=col)
    part = ~allin & (zc > near).any(1)
    for k in np.nonzero(part)[0]:
        poly = []
        for i in range(3):
            a, b = i, (i + 1) % 3
            za, zb = zc[k, a], zc[k, b]
            if za > near:
                poly.append((xc[k, a], yc[k, a], za))
            if (za > near) != (zb > near):
                s = (near - za) / (zb - za)
                poly.append((xc[k, a] + (xc[k, b] - xc[k, a]) * s, yc[k, a] + (yc[k, b] - yc[k, a]) * s, near))
        if len(poly) >= 3:
            dr.polygon([px(*p) for p in poly], fill=col)


def frame(Troom, Twx, pose, aspect, w):
    c = cam(pose, aspect, w)
    img = Image.new("L", (c[6], c[7]), 0)
    if len(Twx):
        raster(Twx, c, img, 128)
    raster(Troom, c, img, 255)
    a = np.asarray(img)
    void = a == 0
    wx = a == 128
    if wx.any():
        o, f, r, u, tx, ty, W_, H_ = c
        ys, xs = np.nonzero(wx)
        xn = (xs + 0.5) / W_ * 2 - 1
        yn = 1 - (ys + 0.5) / H_ * 2
        D = f[None, :] + xn[:, None] * tx * r[None, :] + yn[:, None] * ty * u[None, :]
        D /= np.linalg.norm(D, axis=1, keepdims=True)
        ok = V.through_opening(o.astype(np.float32), D.astype(np.float32), np.full(len(D), 5000.0, np.float32))
        void[ys[~ok], xs[~ok]] = True
    # confirm every candidate with an exact ray (the fill can leave hairline cracks along shared edges): only real gaps stay
    if void.any():
        o, f, r, u, tx, ty, W_, H_ = c
        ys, xs = np.nonzero(void)
        xn = (xs + 0.5) / W_ * 2 - 1
        yn = 1 - (ys + 0.5) / H_ * 2
        D = (f[None, :] + xn[:, None] * tx * r[None, :] + yn[:, None] * ty * u[None, :])
        D = (D / np.linalg.norm(D, axis=1, keepdims=True)).astype(np.float32)
        TT = TALL[0]
        t, j = V.first_hit(o.astype(np.float32), D, TT)
        real = ~np.isfinite(t)
        if TALL[1].any():
            wxh = np.isfinite(t) & TALL[1][np.maximum(j, 0)]
            real |= wxh & ~V.through_opening(o.astype(np.float32), D, t)
        void[:] = False
        void[ys[real], xs[real]] = True
    return void


TALL = [None, None]


def main():
    a = sys.argv[1:]
    pak, ui, poses_f, scene = a[:4]
    opt = lambda k, d: a[a.index(k) + 1] if k in a else d  # noqa: E731
    aspects = {"16:9": 16 / 9, "21:9": 2.39, "4:3": 4 / 3}
    asp = [(k, aspects[k]) for k in opt("--aspect", "16:9,21:9,4:3").split(",")]
    w = int(opt("--grid", "192"))
    only = opt("--only", None)
    png = opt("--png", None)
    src = V.Src(pak, opt("--add", None))
    T, W = V.load_tris(src, V.scene_models(ui, scene))
    Troom, Twx = T[~W].astype(np.float64), T[W].astype(np.float64)
    TALL[0], TALL[1] = T, W
    P = json.load(open(poses_f))[scene]["poses"]
    rep = []
    for pn, pose in P:
        if only and not re.search(only, pn):
            continue
        for an, av in asp:
            void = frame(Troom, Twx, pose, av, w)
            n = int(void.sum())
            r_ = dict(scene=scene, pose_name=pn, aspect=an, pose=pose, void=n, frac=round(n / void.size, 4))
            if n:
                ys, xs = np.nonzero(void)
                r_["bbox_frac"] = [round(xs.min() / void.shape[1], 2), round(ys.min() / void.shape[0], 2),
                                   round((xs.max() + 1) / void.shape[1], 2), round((ys.max() + 1) / void.shape[0], 2)]
                if png:
                    os.makedirs(png, exist_ok=True)
                    Image.fromarray(np.where(void, 255, 40).astype(np.uint8)).save(os.path.join(png, "%s_%s_%s.png" % (scene, pn, an.replace(":", ""))))
            rep.append(r_)
            if n:
                print("  %-14s %-5s void %6d (%5.2f %%) %s" % (pn, an, n, 100.0 * n / void.size, r_.get("bbox_frac", "")), flush=True)
    bad = [r for r in rep if r["void"]]
    print("%s: %d frames, %d with void" % (scene, len(rep), len(bad)))
    out = opt("--out", None)
    if out:
        json.dump(rep, open(out, "w"), indent=1)


if __name__ == "__main__":
    main()
