"""easky.py: the level's own sky as a MOHAA sky box (converter 0.7.17).

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
SIZE = 512


def _sample(im, u, v):
    """bilinear, clamped; u, v in 0..1; v = 0 is the first stored row"""
    w, h, px = im["w"], im["h"], im["rgba"]
    x, y = min(max(u * w - 0.5, 0.0), w - 1.0), min(max(v * h - 0.5, 0.0), h - 1.0)
    x0, y0 = int(x), int(y)
    x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)
    fx, fy = x - x0, y - y0
    out = []
    for c in range(4):
        a = px[(y0 * w + x0) * 4 + c] * (1 - fx) + px[(y0 * w + x1) * 4 + c] * fx
        b = px[(y1 * w + x0) * 4 + c] * (1 - fx) + px[(y1 * w + x1) * 4 + c] * fx
        out.append(a * (1 - fy) + b * fy)
    return out


def _uv(face, p):
    cs, uvs = FACES[face]
    c0, c1, c2 = cs[0], cs[1], cs[2]
    e1 = [c1[k] - c0[k] for k in range(3)]
    e2 = [c2[k] - c0[k] for k in range(3)]
    d = [p[k] - c0[k] for k in range(3)]
    a = sum(d[k] * e1[k] for k in range(3)) / sum(e * e for e in e1)
    b = sum(d[k] * e2[k] for k in range(3)) / sum(e * e for e in e2)
    a, b = min(max(a, 0.0), 1.0), min(max(b, 0.0), 1.0)
    return tuple((uvs[0][k] + a * (uvs[1][k] - uvs[0][k]) + b * (uvs[2][k] - uvs[0][k])) / 1023.0 for k in range(2))


def _dir(suffix, s, t):
    """the engine's sky box: face suffix and s, t in -1..1 (s to the image's right, t up) -> world direction"""
    if suffix == "rt":
        return (1.0, -s, t)
    # the engine draws image "lf" on its second side (-x) and image "bk" on its third (+y): sky_texorder 0,2,1,3,4,5
    if suffix == "lf":
        return (-1.0, s, t)
    if suffix == "bk":
        return (s, 1.0, t)
    if suffix == "ft":
        return (-s, -1.0, t)
    if suffix == "up":
        return (-t, -s, 1.0)
    return (t, -s, -1.0)


def build(L, spec):
    tex = {k: L.texture(spec[k]) for k in ("top", "nx", "px", "py", "ny")}
    if any(v is None or v.get("rgba") is None for v in tex.values()):
        return None
    moon = L.texture(spec["moon"]) if spec.get("moon") else None
    mq = spec.get("moon_quad")            # x, y0, y1, z0, z1 (metres from the eye)
    gain = float(spec.get("gain", 0.75))
    # below the box: the mean of the sides' bottom edge (the original paints that band in the fog colour)
    low = [0.0, 0.0, 0.0]
    n = 0
    for f in ("nx", "px", "py", "ny"):
        for i in range(17):
            c = _sample(tex[f], *_uv(f, tuple(FACES[f][0][1][k] + (FACES[f][0][3][k] - FACES[f][0][1][k]) * i / 16.0 for k in range(3))))
            low = [low[k] + c[k] for k in range(3)]
            n += 1
    low = [v / n for v in low]
    out = {}
    for suf in ("rt", "bk", "lf", "ft", "up", "dn"):
        buf = bytearray(SIZE * SIZE * 4)
        for py_ in range(SIZE):
            t = 1.0 - 2.0 * (py_ + 0.5) / SIZE
            for px_ in range(SIZE):
                s = 2.0 * (px_ + 0.5) / SIZE - 1.0
                d = _dir(suf, s, t)
                m = max(abs(d[0]), abs(d[1]), d[2] * 100.0 / 99.9 if d[2] > 0 else 0.0)
                p = tuple(v * 100.0 / m for v in d)
                if p[2] < -0.84:
                    c = low
                else:
                    if p[2] >= 99.89:
                        f = "top"
                    elif abs(p[0]) >= abs(p[1]):
                        f = "px" if p[0] > 0 else "nx"
                    else:
                        f = "py" if p[1] > 0 else "ny"
                    c = _sample(tex[f], *_uv(f, p))
                c = [c[0] * gain, c[1] * gain, c[2] * gain]
                if moon is not None and mq and d[0] > 0:
                    q = tuple(v * mq[0] / d[0] for v in d)
                    if mq[1] <= q[1] <= mq[2] and mq[3] <= q[2] <= mq[4]:
                        mc = _sample(moon, (q[1] - mq[1]) / (mq[2] - mq[1]), (mq[4] - q[2]) / (mq[4] - mq[3]))
                        al = mc[3] / 255.0
                        c = [c[k] * (1 - al) + mc[k] * al for k in range(3)]
                o = (py_ * SIZE + px_) * 4
                buf[o], buf[o + 1], buf[o + 2], buf[o + 3] = (min(255, int(c[0] + 0.5)), min(255, int(c[1] + 0.5)),
                                                             min(255, int(c[2] + 0.5)), 255)
        out[suf] = (SIZE, SIZE, bytes(buf))
    return out
