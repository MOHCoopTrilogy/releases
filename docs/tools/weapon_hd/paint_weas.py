"""Original replacement art for the Mosin sniper scope's cloth wrap (user call 2026-10-06).

The xw import's sheet textures/models/weapons/mosin_nagant/weas.jpg carried a modder note "thats is from cod2" pointing
at the cloth-wrapped scope cover (wrap tube + gathered end cap), i.e. art lifted from Call of Duty 2. This paints a
PROCEDURAL olive-drab canvas wrap into the same UV islands - nothing is derived from the old pixels, only the island
layout (from the mesh) and a target brightness - plus blanks the unused "airborne sleeve" patch and the captions.

    python docs/tools/weapon_hd/paint_weas.py      writes the 512 shipped override
        docs/tools/assets/fixes/textures/models/weapons/mosin_nagant/weas.jpg  (+ a preview)
build_sheets.py calls paint(W, H) for the HD sheet (finishes.json "paint"), so both share one painter.

Layout facts (measured from models/weapons/nagant/nagantsniper.skd, surface "Weas"):
  wrap tube  uv u 0.024-0.235 (around the scope), v 0.349-0.558 (along it)
  end cap    uv u 0.286-0.481, v 0.332-0.558 (a disc)
"""
import os, sys, io, math
import numpy as np
from PIL import Image
from scipy import ndimage

TUBE = (0.024, 0.349, 0.235, 0.558)
CAP = (0.286, 0.332, 0.481, 0.558)
RECT_TUBE = (0.0, 0.322, 0.268, 0.605)      # whole drawn area of the old art (incl. unmapped margin) is replaced
RECT_CAP = (0.272, 0.322, 0.505, 0.592)
OLIVE = np.array([60.0, 57.0, 40.0])         # faded OD canvas, mean luma close to the old cloth (~48)


def _noise(rng, H, W, sigma):
    n = ndimage.gaussian_filter(rng.standard_normal((H, W)).astype(np.float32), sigma)
    return n / (n.std() + 1e-6)


def _render(S):
    """canvas at S x S. returns rgb (S,S,3) float, alpha (S,S)"""
    rng = np.random.default_rng(1891)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    u, v = (xx + 0.5) / S, (yy + 0.5) / S
    k = S / 2048.0
    rgb = np.zeros((S, S, 3), np.float32)
    alpha = np.zeros((S, S), np.float32)
    mott = 1 + 0.07 * _noise(rng, S, S, 40 * k) + 0.03 * _noise(rng, S, S, 8 * k)
    hue = 1 + 0.04 * _noise(rng, S, S, 60 * k)

    def weave(a, b):     # plain-weave canvas: two orthogonal thread sets, period ~7 px at 2048
        p = 2 * math.pi * 300
        w1 = np.sin(a * p) * (0.5 + 0.5 * np.sign(np.sin(b * p * 0.5)))
        w2 = np.sin(b * p) * (0.5 - 0.5 * np.sign(np.sin(a * p * 0.5)))
        return 0.05 * (w1 + w2) + 0.02 * _noise(rng, S, S, 0.8 * k)

    # ---- wrap tube: helically wound strips
    t = (v - TUBE[1]) / (TUBE[3] - TUBE[1])             # along the scope
    a = (u - TUBE[0]) / (TUBE[2] - TUBE[0])             # around it
    N, slant = 7.0, 0.32
    # irregular hand-wound strips: seams wander, widths vary, the cloth creases along the strip
    s = t * N + a * slant + 0.22 * _noise(rng, S, S, 90 * k) + 0.06 * _noise(rng, S, S, 20 * k)
    f = s - np.floor(s)                                 # position across a strip
    # overlapping strip edge: a soft one-sided shadow under the next strip's lip, not an inked line
    seam = 0.45 * np.exp(-f / 0.16) + 0.35 * np.exp(-((f - 1.0) / 0.06) ** 2)
    lip = np.exp(-((f - 0.97) / 0.05) ** 2)             # the overlapping edge catches light
    roll = 0.86 + 0.18 * np.sin(np.pi * f)              # each strip is rounded
    crease = 1 + 0.035 * _noise(rng, S, S, 6 * k) * np.clip(_noise(rng, S, S, 50 * k), 0, 1.5)
    ends = np.clip(np.minimum(t, 1 - t) / 0.12, 0, 1)   # grime toward the tied ends
    shade = roll * crease * (1 - 0.32 * seam) * (1 + 0.10 * lip) * (0.78 + 0.22 * ends) * mott
    tex = OLIVE * shade[..., None] * np.stack([hue, np.ones_like(hue), 2 - hue], -1)
    tex *= (1 + weave(a * 0.21 + t * 0.07, t * 0.21 - a * 0.07))[..., None]
    # stitched hems at both ends: a dashed darker thread around the scope
    for tc in (0.045, 0.955):
        band = np.exp(-((t - tc) / 0.006) ** 2)
        dash = (np.sin(a * 2 * math.pi * 26) > 0.15).astype(np.float32)
        tex *= (1 - 0.35 * band * dash)[..., None]
        tex += (10 * np.exp(-((t - tc - 0.004) / 0.003) ** 2) * dash)[..., None]
    # frayed light fibres along a few seams (sparse, soft - no salt specks)
    fray = np.clip(_noise(rng, S, S, 1.2 * k) - 1.6, 0, 1) * seam
    tex += (14 * ndimage.gaussian_filter(fray, 0.8 * k))[..., None]
    m = (u >= RECT_TUBE[0]) & (u <= RECT_TUBE[2]) & (v >= RECT_TUBE[1]) & (v <= RECT_TUBE[3])
    rgb[m] = tex[m]; alpha[m] = 1

    # ---- end cap: canvas gathered toward the centre and cinched
    cx, cy = (CAP[0] + CAP[2]) / 2, (CAP[1] + CAP[3]) / 2
    rx, ry = (CAP[2] - CAP[0]) / 2, (CAP[3] - CAP[1]) / 2
    r = np.sqrt(((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2)
    th = np.arctan2(v - cy, u - cx)
    famp = 0.6 + 0.4 * np.clip(_noise(rng, S, S, 70 * k) * 0.5 + 0.5, 0, 1)
    folds = np.sin(th * 9 + 2.6 * _noise(rng, S, S, 45 * k) + 4 * r) * np.clip(1 - r, 0, 1) ** 0.5 * famp
    pucker = 0.70 + 0.30 * np.clip(r / 0.25, 0, 1)
    cinch = np.exp(-((r - 0.86) / 0.03) ** 2)
    shade = (1 + 0.16 * folds) * pucker * (1 - 0.3 * cinch) * mott
    tex = OLIVE * shade[..., None] * np.stack([hue, np.ones_like(hue), 2 - hue], -1)
    tex *= (1 + weave(np.cos(th) * r * 0.1 + u * 0.2, np.sin(th) * r * 0.1 + v * 0.2))[..., None]
    rj = 0.80 + 0.015 * _noise(rng, S, S, 60 * k)
    dash = (np.sin(th * 40) > 0.1).astype(np.float32) * np.exp(-((r - rj) / 0.012) ** 2)
    tex *= (1 - 0.35 * dash)[..., None]
    m = (u >= RECT_CAP[0]) & (u <= RECT_CAP[2]) & (v >= RECT_CAP[1]) & (v <= RECT_CAP[3])
    rgb[m] = tex[m]; alpha[m] = 1
    return np.clip(rgb, 0, 255), alpha


def paint(W, H):
    """rgb (H,W,3) float + alpha (H,W) at the requested size (rendered at >= 2048 and resampled, so the weave never
    aliases into moire at 512)"""
    S = max(2048, W, H)
    rgb, a = _render(S)
    if (W, H) != (S, S):
        rgb = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize((W, H), Image.LANCZOS), np.float32)
        a = (np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((W, H), Image.NEAREST), np.float32) / 255)
    return rgb, a


def main():
    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)
    import vfs, build_sheets as B
    rel = "textures/models/weapons/mosin_nagant/weas.jpg"
    # base = the shipped xw art with captions + the unused sleeve blanked (finishes.json "erase")
    orig = Image.open(io.BytesIO(vfs.read(rel))).convert("RGB")
    base = np.asarray(B.erase(orig, "textures/models/weapons/mosin_nagant/weas"), np.float32)
    rgb, a = paint(*orig.size)
    out = base * (1 - a[..., None]) + rgb * a[..., None]
    dst = os.path.join(os.path.dirname(os.path.dirname(HERE)), "tools", "assets", "fixes", *rel.split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dst, quality=95, subsampling=0)
    prev = Image.new("RGB", (1024 + 8, 512), "white")
    prev.paste(orig, (0, 0)); prev.paste(Image.open(dst), (520, 0))
    prev.save(os.path.join(B.BUILD, "qa", "weas_override.jpg"), quality=90)
    print("wrote", dst, os.path.getsize(dst))


if __name__ == "__main__":
    main()
