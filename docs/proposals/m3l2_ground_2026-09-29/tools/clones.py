# Clone / stamp detector (the independent reviewer's method, made a gate): random W-unit patches of the texture at
# 1 u/px are searched over the whole (periodic) texture in all 8 orientations by normalised cross-correlation;
# a patch whose best match elsewhere is > 0.9 has a near-exact copy. Retail control (m3l3grass_set2): 0%, median 0.36.
import numpy as np


def _orients(p):
    t = p.T
    return [p, p[:, ::-1], p[::-1], p[::-1, ::-1], t, t[:, ::-1], t[::-1], t[::-1, ::-1]]


def clone_stats(L, W=48, n=80, seed=3, excl=None):
    """L: 2-D luma at ~1 u/px, periodic. -> dict(frac90, frac97, median, worst[(y,x,by,bx,r)])"""
    rng = np.random.default_rng(seed)
    H, Wd = L.shape
    excl = W if excl is None else excl
    F = np.fft.fft2(L)
    F2 = np.fft.fft2(L * L)
    ones = np.zeros_like(L); ones[:W, :W] = 1.0
    O = np.conj(np.fft.fft2(ones))
    s1 = np.real(np.fft.ifft2(F * O))            # window sums at each top-left offset (periodic)
    s2 = np.real(np.fft.ifft2(F2 * O))
    var = np.maximum(s2 - s1 * s1 / (W * W), 1e-6)
    best = []
    for _ in range(n):
        y, x = int(rng.integers(H)), int(rng.integers(Wd))
        P = np.roll(np.roll(L, -y, 0), -x, 1)[:W, :W]
        top = 0.0
        loc = None
        for k, q in enumerate(_orients(P)):
            q0 = q - q.mean()
            nq = np.sqrt((q0 * q0).sum()) + 1e-9
            K = np.zeros_like(L); K[:W, :W] = q0
            c = np.real(np.fft.ifft2(F * np.conj(np.fft.fft2(K))))
            r = c / (nq * np.sqrt(var))
            yy, xx = np.meshgrid(np.arange(H), np.arange(Wd), indexing="ij")
            dy = np.minimum(np.abs(yy - y), H - np.abs(yy - y))
            dx = np.minimum(np.abs(xx - x), Wd - np.abs(xx - x))
            r[(dy < excl) & (dx < excl)] = -1
            j = np.argmax(r)
            if r.flat[j] > top:
                top, loc = float(r.flat[j]), (int(j // Wd), int(j % Wd), k)
        best.append((top, y, x, loc))
    v = np.array([b[0] for b in best])
    worst = sorted(best, key=lambda b: -b[0])[:5]
    return dict(frac90=float((v > 0.9).mean()), frac97=float((v > 0.97).mean()), median=float(np.median(v)),
                worst=[(round(b[0], 3), b[1], b[2], b[3]) for b in worst])
