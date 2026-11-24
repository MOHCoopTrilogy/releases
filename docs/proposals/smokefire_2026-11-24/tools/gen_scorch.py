"""gen_scorch.py <outdir> [--px 512] [--n 4] - procedural blast scorch decals (smoke & fire Phase 1; our own, no third-party
art). Each variant: a ragged, feathered soot patch (no hard rim), a lighter blown-clean centre, radial soot spray past
the edge and a debris speckle. RGBA, straight alpha, colour bled into the clear border (no dark fringe under filtering).
Deterministic per variant seed. Also writes <outdir>/scorch_sheet.jpg (each variant over a dirt-coloured ground)."""
import argparse, math, os
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("--px", type=int, default=512); ap.add_argument("--n", type=int, default=4)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
N = a.px


def fbm(shape, seed, octaves=6, base=4):
    rng = np.random.default_rng(seed)
    acc = np.zeros(shape, np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        g = base * (2 ** o)
        small = rng.random((g + 1, g + 1)).astype(np.float32)
        img = np.array(Image.fromarray((small * 255).astype(np.uint8)).resize(shape[::-1], Image.BICUBIC), np.float32) / 255.0
        acc += amp * img
        tot += amp
        amp *= 0.5
    return acc / tot


def ang_noise(theta, seed, k=9):
    rng = np.random.default_rng(seed)
    v = np.zeros_like(theta)
    for i in range(1, k + 1):
        v += rng.normal() / i ** 1.2 * np.cos(i * theta + rng.random() * 6.283)
    return v / 1.6


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
cx = cy = (N - 1) / 2.0
dx, dy = (xx - cx) / (N / 2), (yy - cy) / (N / 2)
r = np.sqrt(dx * dx + dy * dy)
th = np.arctan2(dy, dx)
ground = np.array([0.42, 0.36, 0.28], np.float32)
sheet = []
for v in range(a.n):
    seed = 1124 + 97 * v
    rng = np.random.default_rng(seed)
    edge = 0.52 + 0.17 * ang_noise(th, seed, k=7) + 0.12 * (fbm((N, N), seed + 1, base=5) - 0.5)
    rays = np.zeros_like(r)
    for _ in range(rng.integers(4, 9)):                      # soot spray streaks past the edge
        t0, w, ln = rng.random() * 6.283, 0.05 + 0.10 * rng.random(), 0.22 + 0.30 * rng.random()
        d = np.angle(np.exp(1j * (th - t0)))
        rays = np.maximum(rays, np.exp(-(d / w) ** 2) * smoothstep(edge + ln, edge, r) * (0.18 + 0.27 * rng.random()))
    mott = fbm((N, N), seed + 2, base=5)
    core = smoothstep(edge + 0.04, edge - 0.34, r)                    # feathered patch, no rim
    alpha = core * (0.42 + 0.58 * mott ** 1.3)
    alpha = np.maximum(alpha, rays * (0.5 + 0.5 * mott))
    clean = smoothstep(0.24, 0.0, r + 0.08 * (mott - 0.5)) * (0.30 + 0.20 * rng.random())   # blown-clean centre: thinner, lighter
    alpha *= 1.0 - 0.45 * clean
    speck = (fbm((N, N), seed + 3, octaves=2, base=96) > 0.86) & (r > edge * 0.8) & (r < edge + 0.35)
    alpha = np.where(speck, np.maximum(alpha, 0.35), alpha)
    alpha = np.clip(alpha * smoothstep(0.98, 0.86, r), 0, 1)  # never touch the texture border
    soot = np.array([0.045, 0.040, 0.036], np.float32)
    ash = np.array([0.26, 0.23, 0.20], np.float32)
    col = soot[None, None, :] * (0.7 + 0.6 * mott[..., None]) * (1 - clean[..., None]) + ash[None, None, :] * clean[..., None]
    col = np.where(speck[..., None], np.array([0.10, 0.08, 0.06], np.float32), col)
    rgba = np.dstack([np.clip(col, 0, 1), alpha]).astype(np.float32)
    img = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA")
    nm = "scorch_%s" % "abcdefgh"[v]
    img.save(os.path.join(a.out, nm + ".tga"))
    comp = ground[None, None, :] * (0.85 + 0.3 * fbm((N, N), 7, base=16)[..., None])
    comp = comp * (1 - alpha[..., None]) + rgba[..., :3] * alpha[..., None]
    sheet.append(Image.fromarray((np.clip(comp, 0, 1) * 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS))
    print(nm, "alpha mean %.3f" % alpha.mean())
S = Image.new("RGB", (256 * len(sheet), 256))
for i, im in enumerate(sheet):
    S.paste(im, (256 * i, 0))
S.save(os.path.join(a.out, "scorch_sheet.jpg"), quality=88)
