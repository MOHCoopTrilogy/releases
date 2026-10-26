"""ice_look.py - offline look-dev for the frozenriver ice (BEFORE = retail pixel, AFTER = prototype ice material).
Prototype of the proposed gl2 ice term; numbers are the starting values for the GLSL, not final.
Reuses ww_look (Scene / geometry / sky probe / retail shading) from docs/proposals/water_wetness_2026-09-27/tools.
usage: python ice_look.py <view> [tag]   (views in VIEWS) -> $ICE_OUT/<view>_BEFORE.jpg, _AFTER.jpg, _AB.jpg"""
import os, sys, json, math
import numpy as np
from PIL import Image
from scipy import ndimage
WW = r"C:\mohaa-coop-dev\docs\proposals\water_wetness_2026-09-27\tools"
sys.path.insert(0, WW)
import ww_look as L
from ww_fs import FS

TEX = r"H:\hzm_work\ice1025_textures"
OUT = os.environ.get("ICE_OUT", r"H:\hzm_work\ice1025_out")
os.makedirs(OUT, exist_ok=True)

VIEWS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "views.json")))


def mips(a):
    out = [a]
    while min(out[-1].shape[:2]) > 8:
        x = out[-1]; h, w = x.shape[0] // 2 * 2, x.shape[1] // 2 * 2
        out.append(x[:h, :w].reshape(h // 2, 2, w // 2, 2, -1).mean((1, 3)))
    return out


def load(name, gray=False):
    im = Image.open(name).convert("L" if gray else "RGB").resize((1024, 1024), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    return mips(a[..., None] if gray else a)


def samp(mp, u, v, lod):
    """trilinear, wrapped. u,v arrays (tiles), lod float array (0 = full res)."""
    nl = len(mp); lod = np.clip(lod, 0, nl - 1.001); l0 = np.floor(lod).astype(int); fr = (lod - l0)
    res = np.zeros((len(u), mp[0].shape[2]), np.float32)
    for l in np.unique(l0):
        m = l0 == l
        for dl in (0, 1):
            wgt = (1 - fr[m]) if dl == 0 else fr[m]
            t = mp[min(l + dl, nl - 1)]; h, w = t.shape[:2]
            x = (u[m] % 1.0) * w - 0.5; y = (v[m] % 1.0) * h - 0.5
            x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); ax = (x - x0)[:, None]; ay = (y - y0)[:, None]
            g = lambda yy, xx: t[yy % h, xx % w]
            c = (g(y0, x0) * (1 - ax) + g(y0, x0 + 1) * ax) * (1 - ay) + (g(y0 + 1, x0) * (1 - ax) + g(y0 + 1, x0 + 1) * ax) * ay
            res[m] += c * wgt[:, None]
    return res


def fbm(x, y, seed=3):
    rng = np.random.default_rng(seed); out = np.zeros_like(x); a = 1.0; tot = 0
    for o in range(5):
        ph = rng.uniform(0, 6.28, 4); f = 2 ** o
        out += a * (np.sin(x * f * 0.9 + ph[0]) * np.sin(y * f * 1.1 + ph[1]) + np.sin((x + y) * f * 0.7 + ph[2]) * np.sin((x - y) * f * 0.8 + ph[3]))
        tot += a * 2; a *= 0.55
    return out / tot * 0.5 + 0.5


class IceMat:
    def __init__(self, a="Ice001", b="Ice004"):
        self.c = [load(f"{TEX}/{n}/{n}_2K-JPG_Color.jpg") for n in (a, b)]
        self.n = [load(f"{TEX}/{n}/{n}_2K-JPG_NormalGL.jpg") for n in (a, b)]
        self.r = [load(f"{TEX}/{n}/{n}_2K-JPG_Roughness.jpg", True) for n in (a, b)]


def ice_after(S, G, eye, base, lmv, tri_ice, mat, frost_tex, bankdist=None, P=None):
    P = P or {}
    H, W = G["tid"].shape
    m = np.isin(G["tid"], tri_ice)
    ys, xs = np.nonzero(m)
    pos = G["pos"][ys, xs]; dist = G["dist"][ys, xs]
    V = np.asarray(eye, float)[None] - pos; V /= np.linalg.norm(V, axis=1, keepdims=True)
    wpp = dist / (W * 0.5 / math.tan(math.radians(40)))
    tile1, tile2 = P.get("tile1", 640.0), P.get("tile2", 1090.0)
    lod1 = np.log2(np.maximum(wpp / (tile1 / 1024.0), 1e-3)); lod2 = np.log2(np.maximum(wpp / (tile2 / 1024.0), 1e-3))
    u1, v1 = pos[:, 0] / tile1, pos[:, 1] / tile1
    c, s = math.cos(0.61), math.sin(0.61)
    u2, v2 = (pos[:, 0] * c - pos[:, 1] * s) / tile2 + 0.37, (pos[:, 0] * s + pos[:, 1] * c) / tile2 + 0.11
    mac = fbm(pos[:, 0] / 900.0, pos[:, 1] / 900.0)
    w2 = np.clip(0.25 + 0.5 * mac, 0, 1)
    col = samp(mat.c[0], u1, v1, lod1) * (1 - w2)[:, None] + samp(mat.c[1], u2, v2, lod2) * w2[:, None]
    nm = samp(mat.n[0], u1, v1, lod1) * (1 - w2)[:, None] + samp(mat.n[1], u2, v2, lod2) * w2[:, None]
    rg = samp(mat.r[0], u1, v1, lod1)[:, 0] * (1 - w2) + samp(mat.r[1], u2, v2, lod2)[:, 0] * w2
    lum = (col * np.array([.299, .587, .114], np.float32)).sum(1)
    deep = np.array(P.get("deep", [0.035, 0.11, 0.20]), np.float32); white = np.array(P.get("white", [0.80, 0.90, 0.98]), np.float32)
    k = (np.clip((lum - 0.18) / 0.55, 0, 1) ** 1.1)[:, None]
    alb = deep[None] * (1 - k) + white[None] * k
    ft = samp(frost_tex, pos[:, 0] / 1024.0, pos[:, 1] / 1024.0, np.log2(np.maximum(wpp / 1.0, 1e-3)))
    fm = np.clip((fbm(pos[:, 0] / 380.0 + 4, pos[:, 1] / 380.0 - 2, 11) - 0.58) * 5.0, 0, 1)
    if bankdist is not None:
        bd = bankdist(pos[:, 0], pos[:, 1]); fm = np.maximum(fm * 0.6, np.clip(1 - bd / P.get("drift", 170.0), 0, 1) ** 1.5)
    alb = alb * (1 - fm)[:, None] + ft * 0.95 * fm[:, None]
    rg = np.clip(rg * 0.55 + 0.10, 0.05, 1) * (1 - fm) + 0.85 * fm
    nxy = (nm[:, :2] * 2 - 1) * P.get("nstr", 1.8) * np.clip(1.0 - dist / 3500.0, 0.15, 1)[:, None] * (1 - fm)[:, None]
    N = np.stack([nxy[:, 0], nxy[:, 1], np.ones(len(nxy))], 1); N /= np.linalg.norm(N, axis=1, keepdims=True)
    haze = S.sky_fog_frac(np.asarray(eye, float))
    diff = alb * lmv[ys, xs]
    ndv = np.clip((N * V).sum(1), 0, 1); F0 = 0.04
    F = (F0 + (1 - F0) * (1 - ndv) ** 5) * (1 - fm)
    R = 2 * (N * V).sum(1)[:, None] * N - V
    env = L.sky_sample(S.sky_blur[2], R) * (1 - haze) + S.fogc[None] * haze
    env = env * P.get("envgain", 1.0) + np.array(P.get("envlift", [0.0, 0.0, 0.0]), np.float32)[None]
    Hh = V + (-S.sun)[None]; Hh /= np.linalg.norm(Hh, axis=1, keepdims=True)
    nh = np.clip((N * Hh).sum(1), 0, 1); a2 = np.maximum(rg, 0.06) ** 4
    D = a2 / (math.pi * ((nh * nh) * (a2 - 1) + 1) ** 2)
    nl = np.clip((N * (-S.sun)[None]).sum(1), 0, 1)
    glint = np.minimum(D * nl * F * 0.25, P.get("glintcap", 4.0))[:, None] * S.sunc[None] * P.get("glint", 1.0)
    out = base.copy()
    out[ys, xs] = diff * (1 - F[:, None]) * P.get("diffgain", 1.0) + env * F[:, None] + glint
    return out, m


def build_bankdist(S, tri_ice):
    occ, ox, oy, cell = S.occ
    z0 = float(S.xyz[tri_ice].reshape(-1, 3)[:, 2].mean())
    d = ndimage.distance_transform_edt(~(occ > z0 + 28)) * cell
    def f(x, y):
        ix = np.clip(((x - ox) / cell).astype(int), 0, d.shape[1] - 1); iy = np.clip(((y - oy) / cell).astype(int), 0, d.shape[0] - 1)
        return d[iy, ix]
    return f


_CACHE = {}


def render(view, W=1280, H=720, ss=2, P=None, tag=""):
    mp, eye, tgt = VIEWS[view]
    if mp not in _CACHE:
        fs = FS(); S = L.Scene(fs, "maps/%s.bsp" % mp); S.build_occlusion(); _CACHE[mp] = (fs, S)
    fs, S = _CACHE[mp]
    ids = [i for i, s in enumerate(S.shaders) if "frozenriver" in s[0].lower()]
    tri_ice = np.nonzero(np.isin(S.shv, ids))[0]
    RW, RH = W * ss, H * ss
    eye = np.asarray(eye, float)
    cam, yaw, el = L.look_camera(eye, tgt, RW, RH)
    z, tid, bary = L.render_geometry(S, eye, cam, RW, RH)
    G = L.gbuf(S, eye, cam, RW, RH, tid, bary)
    base, alb, lmv = L.shade_base(S, G, RW, RH)
    img_t = fs.load_image("textures/central_europe_winter/frozenriver", compressed=False)[0]
    frost_tex = mips(img_t[..., :3].astype(np.float32))
    if "mat" not in _CACHE:
        _CACHE["mat"] = IceMat()
    after, m = ice_after(S, G, eye, base, lmv, tri_ice, _CACHE["mat"], frost_tex, build_bankdist(S, tri_ice), P)
    b = L.fog_and_sky(S, base, G, cam, RW, RH, eye); a = L.fog_and_sky(S, after, G, cam, RW, RH, eye)
    la = lambda x: float(np.exp(np.mean(np.log(x.mean(-1) + 1e-4))))
    k = min(max(la(b), .25), 4) / min(max(la(a), .25), 4)
    b8 = L.to8(L.downsample(L.grade(b), ss)); a8 = L.to8(L.downsample(L.grade(a, k), ss))
    Image.fromarray(b8).save(f"{OUT}/{view}{tag}_BEFORE.jpg", quality=93); Image.fromarray(a8).save(f"{OUT}/{view}{tag}_AFTER.jpg", quality=93)
    ab = np.concatenate([L.label(b8, "BEFORE (retail frozenriver)"), np.zeros((6, W, 3), np.uint8), L.label(a8, "AFTER (prototype ice material, offline)")], 0)
    Image.fromarray(ab).save(f"{OUT}/{view}{tag}_AB.jpg", quality=90)
    print(view, "ae", round(k, 2), "ice frac", float(m.mean()), flush=True)


if __name__ == "__main__":
    render(sys.argv[1], tag=sys.argv[2] if len(sys.argv) > 2 else "")
