import numpy as np


def box_blur(a, r):
    """separable box blur, radius r, edge-clamped (no scipy)"""
    if r <= 0:
        return a
    k = 2 * r + 1
    for ax in (0, 1):
        p = [(0, 0), (0, 0)]
        p[ax] = (r, r)
        pa = np.pad(a, p, mode='edge')
        c = np.cumsum(pa, axis=ax, dtype=np.float64)
        z = np.zeros_like(np.take(c, [0], axis=ax))
        c = np.concatenate([z, c], axis=ax)
        n = a.shape[ax]
        a = ((np.take(c, range(k, k + n), axis=ax) - np.take(c, range(0, n), axis=ax)) / k).astype(np.float32)
    return a
