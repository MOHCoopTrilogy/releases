"""easky.py: the level's own sky as a MOHAA sky box (converter 0.7.17; 2048 px faces since the look round, 2026-11-13).

The original draws its sky as an eye-centred half cube (200 x 200 m wide, 100.8 m tall, bottom edge 0.84 m below the
eye): a 256x256 top, four 2:1 sides, and a moon quad on the +x side. The textures are in the level stream (SHPX,
named in ea_levels.json "sky_disc"); the box geometry, the uv corners and the moon quad are not decoded from the
disc: they are read from the original game's GPU state (H:\\hzm_work\\ref_xemu\\TRACE_sky_fog.md) and kept here as
numbers. Not reproduced: the skirt mesh below the horizon (filled with the sides' own bottom-row colour, which the
original paints in the fog colour) and the two alpha cloud layers.

build(level_obj, spec) -> {"rt": (w, h, rgba), ...} for the six faces, or None when a texture is missing.
"""
import math

# face -> strip corners (x, y, z in metres from the eye, z up) and their uv (0..1023 = 0..1), in the original's order
FACES = {
    "top": (((-100, 100, 99.9), (-100, -100, 99.9), (100, 100, 99.9), (100, -100, 99.9)),
            ((1023, 1), (1023, 1023), (0, 1), (0, 1023))),
    "nx": (((-100, 100, 100), (-100, 100, -0.84), (-100, -100, 100), (-100, -100, -0.84)),
           ((0, 1), (1023, 1), (0, 1021), (1023, 1021))),
    "px": (((100, -100, 100), (100, -100, -0.84), (100, 100, 100), (100, 100, -0.84)),
           ((1023, 1021), (0, 1021), (1023, 1), (0, 1))),
    "py": (((100, 100, 100), (100, 100, -0.84), (-100, 100, 100), (-100, 100, -0.84)),
           ((2, 1023), (2, 0), (1021, 1023), (1021, 0))),
    "ny": (((-100, -100, 100), (-100, -100, -0.84), (100, -100, 100), (100, -100, -0.84)),
           ((1022, 0), (1022, 1023), (1, 0), (1, 1023))),
}
# [look 2026-11-13, user: "the skybox for dying breath looks pretty bad quality. I love that it has a moon though!"]
# The faces were 512 px, sampled bilinearly from 128-256 px sources: the 48 px moon of the original's 256 px moon texture
# came out about 12 x 18 px and the clouds were stretched mush. Now: 2048 px faces, sampled from the sources enlarged
# smoothly beforehand (bicubic for the clouds - nothing invented, they stay soft; Lanczos for the moon, held inside its
# own source range so the sharpening adds no ring or halo), all vectorised (numpy). Every face samples the same sky
# through the same direction -> texture mapping, so the twelve cube edges meet without a seam by construction
# (edge_report() measures them).
SIZE = 2048
PRE = 4            # source pre-enlargement before sampling


def _arr(t, sharp):
    import numpy as np
    from PIL import Image, ImageFilter
    im = Image.frombytes("RGBA", (t["w"], t["h"]), bytes(t["rgba"]))
    if not sharp:
        return np.asarray(im.resize((t["w"] * PRE, t["h"] * PRE), Image.BICUBIC), np.float32)
    # the moon: resampled PREMULTIPLIED. Its glow texels are white with a low alpha; interpolating straight colour pulled
    # that white into the disc's edge and drew a crisp bright ring (look QA 2026-11-13). Premultiplied, the edge keeps the
    # texture's own alpha falloff (about three texels) and only the disc's colour. Lanczos keeps the craters; every texel
    # is clamped into the local 3x3 range of the source so the sharpening adds no ring of its own. Returned premultiplied.
    a0 = np.asarray(im, np.float32).copy()
    # the texture's own rim: its partly transparent edge texels carry a light colour (a baked outline). Give them the
    # colour of the disc just inside, so the edge is only the alpha falloff - soft, not a drawn ring
    alpha = a0[..., 3].copy()
    edge = (alpha > 60) & (alpha < 250)
    edge0 = edge.copy()
    good = alpha >= 250
    rgb = a0[..., :3] * good[..., None]
    wsum = good.astype(np.float32)
    for _ in range(4):
        if not edge.any():
            break
        k = lambda m: (m + np.roll(m, 1, 0) + np.roll(m, -1, 0) + np.roll(m, 1, 1) + np.roll(m, -1, 1)
                       + np.roll(np.roll(m, 1, 0), 1, 1) + np.roll(np.roll(m, 1, 0), -1, 1)
                       + np.roll(np.roll(m, -1, 0), 1, 1) + np.roll(np.roll(m, -1, 0), -1, 1))
        s_ = k(rgb); w_ = k(wsum)
        fill = edge & (w_ > 0) & ~good
        a0[..., :3][fill] = (s_[fill] / w_[fill][:, None])
        rgb[fill] = a0[..., :3][fill]
        wsum[fill] = 1.0
        good = good | fill
        edge = edge & ~fill
    # an edge texel is the disc (coverage t) over the white glow (the glow's own alpha just outside, about 38): composite
    # them so the falloff runs from disc colour into glow, with neither a light ring nor a dark one
    ga = float(np.median(alpha[(alpha > 20) & (alpha < 60)])) if ((alpha > 20) & (alpha < 60)).any() else 0.0
    pm = a0.copy()
    pm[..., :3] *= a0[..., 3:4] / 255.0
    if edge0.any():
        tcov = np.clip((alpha - ga) / max(1.0, 255.0 - ga), 0.0, 1.0)[..., None]
        pm[..., :3] = np.where(edge0[..., None], a0[..., :3] * tcov + 255.0 * (ga / 255.0) * (1 - tcov), pm[..., :3])
    def up(ch, mode):
        return np.stack([np.asarray(Image.fromarray(ch[..., c]).resize((t["w"] * PRE, t["h"] * PRE), mode), np.float32)
                         for c in range(4)], -1)
    big = up(pm, Image.LANCZOS)
    lo = up(np.stack([np.asarray(Image.fromarray(pm[..., c]).filter(ImageFilter.MinFilter(3)), np.float32) for c in range(4)], -1), Image.BILINEAR)
    hi = up(np.stack([np.asarray(Image.fromarray(pm[..., c]).filter(ImageFilter.MaxFilter(3)), np.float32) for c in range(4)], -1), Image.BILINEAR)
    return np.minimum(np.maximum(big, lo), hi)


def _bilerp(a, u, v):
    """a: HxWx4 float; u, v: arrays 0..1 (v = 0 the first stored row); clamped bilinear"""
    import numpy as np
    h, w = a.shape[:2]
    x = np.clip(u * w - 0.5, 0.0, w - 1.0)
    y = np.clip(v * h - 0.5, 0.0, h - 1.0)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    top = a[y0, x0] * (1 - fx) + a[y0, x1] * fx
    bot = a[y1, x0] * (1 - fx) + a[y1, x1] * fx
    return top * (1 - fy) + bot * fy


def _uv_np(face, px, py, pz):
    import numpy as np
    cs, uvs = FACES[face]
    c0, c1, c2 = cs[0], cs[1], cs[2]
    e1 = [c1[k] - c0[k] for k in range(3)]
    e2 = [c2[k] - c0[k] for k in range(3)]
    d = (px - c0[0], py - c0[1], pz - c0[2])
    a = (d[0] * e1[0] + d[1] * e1[1] + d[2] * e1[2]) / sum(e * e for e in e1)
    b = (d[0] * e2[0] + d[1] * e2[1] + d[2] * e2[2]) / sum(e * e for e in e2)
    a = np.clip(a, 0.0, 1.0)
    b = np.clip(b, 0.0, 1.0)
    u = (uvs[0][0] + a * (uvs[1][0] - uvs[0][0]) + b * (uvs[2][0] - uvs[0][0])) / 1023.0
    v = (uvs[0][1] + a * (uvs[1][1] - uvs[0][1]) + b * (uvs[2][1] - uvs[0][1])) / 1023.0
    return u, v


def _dirs(suffix, n):
    """the engine's sky box: face suffix -> world directions of its n x n texels (s to the image's right, t up)"""
    import numpy as np
    c = (np.arange(n, dtype=np.float32) + 0.5) / n
    s = (2.0 * c - 1.0)[None, :].repeat(n, 0)
    t = (1.0 - 2.0 * c)[:, None].repeat(n, 1)
    one = np.ones_like(s)
    if suffix == "rt":
        return one, -s, t
    # the engine draws image "lf" on its second side (-x) and image "bk" on its third (+y): sky_texorder 0,2,1,3,4,5
    if suffix == "lf":
        return -one, s, t
    if suffix == "bk":
        return s, one, t
    if suffix == "ft":
        return -s, -one, t
    if suffix == "up":
        return -t, -s, one
    return t, -s, -one


def build(L, spec, size=None):
    import numpy as np
    tex = {k: L.texture(spec[k]) for k in ("top", "nx", "px", "py", "ny")}
    if any(v is None or v.get("rgba") is None for v in tex.values()):
        return None
    n = int(size or SIZE)
    src = {k: _arr(v, False) for k, v in tex.items()}
    moon = L.texture(spec["moon"]) if spec.get("moon") else None
    msrc = _arr(moon, True) if moon is not None and moon.get("rgba") is not None else None
    mq = spec.get("moon_quad")            # x, y0, y1, z0, z1 (metres from the eye)
    gain = float(spec.get("gain", 0.75))
    # below the box: the mean of the sides' bottom edge (the original paints that band in the fog colour)
    lows = []
    for f in ("nx", "px", "py", "ny"):
        i = np.arange(17, dtype=np.float32) / 16.0
        p0, p1 = FACES[f][0][1], FACES[f][0][3]
        u, v = _uv_np(f, p0[0] + (p1[0] - p0[0]) * i, p0[1] + (p1[1] - p0[1]) * i, p0[2] + (p1[2] - p0[2]) * i)
        lows.append(_bilerp(src[f], u, v)[:, :3])
    low = np.concatenate(lows).mean(0)
    # [2026-11-15, sweep S4] the original's skirt below the horizon: its own texture (T_jZ: a dark tree line over a grey
    # band), on a ring from 0.84 m to 30.9 m below the eye at 100 m (TRACE_sky_fog draw 67), drawn with the box's own
    # vertex colour. The skirt's uv are not in the trace: u runs once round each side of the box (as the side faces do),
    # v from the horizon down. Below the skirt: its own bottom row.
    sk = L.texture(spec["skirt"]) if spec.get("skirt") else None
    sksrc = _arr(sk, False) if sk is not None and sk.get("rgba") is not None else None
    if sksrc is not None:
        low = sksrc[-2:, :, :3].reshape(-1, 3).mean(0)
    out = {}
    for suf in ("rt", "bk", "lf", "ft", "up", "dn"):
        dx, dy, dz = _dirs(suf, n)
        m = np.maximum(np.maximum(np.abs(dx), np.abs(dy)), np.where(dz > 0, dz * 100.0 / 99.9, 0.0))
        px, py, pz = dx * 100.0 / m, dy * 100.0 / m, dz * 100.0 / m
        col = np.empty((n, n, 3), np.float32)
        col[:] = low
        below = pz < -0.84
        top = (~below) & (pz >= 99.89)
        side = (~below) & (~top)
        xs = side & (np.abs(px) >= np.abs(py))
        ys = side & (np.abs(px) < np.abs(py))
        for f, sel in (("top", top), ("px", xs & (px > 0)), ("nx", xs & (px <= 0)), ("py", ys & (py > 0)), ("ny", ys & (py <= 0))):
            if sel.any():
                u, v = _uv_np(f, px[sel], py[sel], pz[sel])
                col[sel] = _bilerp(src[f], u, v)[:, :3]
        if sksrc is not None:
            sk_sel = below & (pz >= -30.9)
            if sk_sel.any():
                ax = np.abs(px[sk_sel]) >= np.abs(py[sk_sel])
                # u along the side the direction falls on (0..1 over 200 m), v down the skirt (0 at -0.84, 1 at -30.9)
                su = np.where(ax, (py[sk_sel] + 100.0) / 200.0, (px[sk_sel] + 100.0) / 200.0)
                sv = np.clip((-0.84 - pz[sk_sel]) / (30.9 - 0.84), 0.0, 1.0)
                col[sk_sel] = _bilerp(sksrc, su, sv)[:, :3]
        col *= gain
        if spec.get("tint"):
            col *= np.asarray(spec["tint"], np.float32)    # [2026-11-15] the original's sky is darker and less blue (frames)
        gb = spec.get("glow_band")
        if gb:
            # [2026-11-15, coordinator QA on the trial sheet] the original's horizon carries a continuous orange-pink glow
            # behind the burning city across the whole skyline width (ref_xemu atmo far_*c); its distant glow particles
            # do not draw in ours (open). The band is painted into the sky: a soft arc over the city's yaw range
            # (feathered at the ends), peaking just above the horizon and fading up (sig_up) and below it (sig_dn)
            yaw = np.degrees(np.arctan2(dy, dx)); el = np.degrees(np.arctan2(dz, np.hypot(dx, dy)))
            y0, y1 = gb["yaw"]; fe = float(gb.get("feather", 15.0))
            wy = np.clip(np.minimum(yaw - y0, y1 - yaw) / fe, 0.0, 1.0)
            wy = wy * wy * (3 - 2 * wy)
            de = el - float(gb.get("peak", 1.5))
            we = np.exp(-0.5 * (de / np.where(de > 0, float(gb.get("sig_up", 5.0)), float(gb.get("sig_dn", 2.0)))) ** 2)
            col += (wy * we)[:, :, None] * np.asarray(gb["rgb"], np.float32)[None, None, :] * 255.0
        if msrc is not None and mq:
            pos = dx > 0
            with np.errstate(divide="ignore", invalid="ignore"):
                qy = np.where(pos, dy * mq[0] / dx, -1e9)
                qz = np.where(pos, dz * mq[0] / dx, -1e9)
            sel = pos & (qy >= mq[1]) & (qy <= mq[2]) & (qz >= mq[3]) & (qz <= mq[4])
            if sel.any():
                mc = _bilerp(msrc, (qy[sel] - mq[1]) / (mq[2] - mq[1]), (mq[4] - qz[sel]) / (mq[4] - mq[3]))
                al = mc[:, 3:4] / 255.0
                col[sel] = col[sel] * (1 - al) + mc[:, :3]       # premultiplied moon (see _arr)
        rgba = np.empty((n, n, 4), np.uint8)
        rgba[..., :3] = np.clip(col + 0.5, 0, 255).astype(np.uint8)
        rgba[..., 3] = 255
        out[suf] = (n, n, rgba.tobytes())
    # the cloud layers' texture (cAe3, white with alpha), enlarged smoothly 4x: the shader draws it as two scrolling stages
    cl = L.texture(spec["clouds"]) if spec.get("clouds") else None
    if cl is not None and cl.get("rgba") is not None:
        from PIL import Image
        im = Image.frombytes("RGBA", (cl["w"], cl["h"]), bytes(cl["rgba"])).resize((cl["w"] * 4, cl["h"] * 4), Image.BICUBIC)
        out["clouds"] = (im.width, im.height, im.tobytes())
    return out


def edge_report(faces):
    """mean absolute colour step across each of the twelve cube edges (a texel on each side): the seam check"""
    import numpy as np
    n = faces["rt"][0]
    F = {k: np.frombuffer(v[2], np.uint8).reshape(n, n, 4)[..., :3].astype(np.float32) for k, v in faces.items()}
    # direction of a face texel -> which neighbour face holds the next texel: compare each face's border row/column with the
    # texel the same direction lands on in the neighbour (found by sampling the neighbour at the edge-adjacent direction)
    rep = {}
    for suf in F:
        dx, dy, dz = _dirs(suf, n)
        for name, (yy, xx) in (("top", (0, slice(None))), ("bottom", (n - 1, slice(None))),
                               ("left", (slice(None), 0)), ("right", (slice(None), n - 1))):
            d = np.stack([dx[yy, xx], dy[yy, xx], dz[yy, xx]], -1)
            # push the direction one texel outward and find where it lands
            k = 2.0 / n
            if name == "top":
                d2 = d + k * np.stack(_t_axis(suf), -1)
            elif name == "bottom":
                d2 = d - k * np.stack(_t_axis(suf), -1)
            elif name == "left":
                d2 = d - k * np.stack(_s_axis(suf), -1)
            else:
                d2 = d + k * np.stack(_s_axis(suf), -1)
            other, oy, ox = _locate(d2, n)
            a = F[suf][yy, xx]
            b = np.stack([F[o][y, x] for o, y, x in zip(other, oy, ox)])
            rep[(suf, name)] = float(np.abs(a - b).mean())
    return rep


def _s_axis(suf):
    return {"rt": (0, -1, 0), "lf": (0, 1, 0), "bk": (1, 0, 0), "ft": (-1, 0, 0), "up": (0, -1, 0), "dn": (0, -1, 0)}[suf]


def _t_axis(suf):
    return {"rt": (0, 0, 1), "lf": (0, 0, 1), "bk": (0, 0, 1), "ft": (0, 0, 1), "up": (-1, 0, 0), "dn": (1, 0, 0)}[suf]


def _locate(d, n):
    """directions (k x 3) -> (face, row, col) of the texel each one falls in"""
    import numpy as np
    out_f, out_y, out_x = [], [], []
    for x, y, z in d:
        ax = max(abs(x), abs(y), abs(z))
        if ax == abs(x):
            f = "rt" if x > 0 else "lf"
            s, t = ((-y / x), z / abs(x)) if x > 0 else ((y / -x), z / abs(x))
        elif ax == abs(y):
            f = "bk" if y > 0 else "ft"
            s, t = ((x / y), z / abs(y)) if y > 0 else ((-x / -y), z / abs(y))
        else:
            f = "up" if z > 0 else "dn"
            s, t = ((-y / z), (-x / z)) if z > 0 else ((-y / -z), (x / -z))
        col = int(min(n - 1, max(0, (s + 1) * 0.5 * n)))
        row = int(min(n - 1, max(0, (1 - t) * 0.5 * n)))
        out_f.append(f); out_y.append(row); out_x.append(col)
    return out_f, out_y, out_x
