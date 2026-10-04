# -*- coding: utf-8 -*-
"""Headless ground previewer for a MOHAA BSP (single process, numpy only).

It is NOT the engine: it draws only up-facing world surfaces (brush, soup, curve control grid, terrain) with
their diffuse texture x lightmap*2, no models, no fog, no buildings. Its job is to judge a GROUND texture at the
scale and repetition the map really draws it - before the test slot - never to replace in-engine captures.

  UV map : a top-down raster (res u/px) of surface id, texture s/t, lightmap RGB and height, built from the BSP.
  view   : per screen pixel, a ray is intersected with the height field (fixed-point iteration), s/t are read
           from the UV map (bilinear inside one surface), and the texture is sampled from its mip pyramid with
           the level from the screen-space s/t derivatives (approximating trilinear + mild anisotropy).

    from groundview import World
    w = World(bsp_bytes, region=(x0, y0, x1, y1), res=1.0, zmax=60)
    img = w.render(textures, eye=(x, y, z), yaw=deg, pitch=deg, fov=90, size=(1280, 720))
    top = w.topdown(textures, px_per_unit=0.5)
textures: {image base (lower, no ext): HxWx3 uint8}. A shader's first-stage image is used (table from the stack).
"""
import struct
import numpy as np

LM = 128


def _lumps(b):
    ident, version = struct.unpack_from("<4si", b, 0)
    n = 29 if version <= 18 else 28
    L = [struct.unpack_from("<ii", b, 12 + 8 * i) for i in range(n)]
    if version <= 18:
        L = L[:13] + L[14:]
    return lambda i: b[L[i][0]:L[i][0] + L[i][1]]


class World:
    def __init__(self, b, region, res=1.0, zmax=1e9, zmin=-1e9, nz_min=0.5, tcgen=None):
        tcgen = tcgen or {}
        lump = _lumps(b)
        sh = lump(0)
        self.names = [sh[i * 140:i * 140 + 64].split(b"\0")[0].decode("latin1").lower().replace("\\", "/")
                      for i in range(len(sh) // 140)]
        lmb = np.frombuffer(lump(2), "u1")
        self.lm = lmb[:len(lmb) // (LM * LM * 3) * LM * LM * 3].reshape(-1, LM, LM, 3).astype(np.float32)
        dv = lump(4)
        nv = len(dv) // 44
        V = np.frombuffer(dv[:nv * 44], dtype=np.dtype([("xyz", "<f4", 3), ("st", "<f4", 2), ("lm", "<f4", 2),
                                                         ("n", "<f4", 3), ("c", "u1", 4)]))
        IX = np.frombuffer(lump(5), "<i4")
        x0, y0, x1, y1 = region
        self.region, self.res = region, res
        W, H = int(np.ceil((x1 - x0) / res)), int(np.ceil((y1 - y0) / res))
        self.W, self.H = W, H
        self.Z = np.full((H, W), -1e9, np.float32)
        self.SID = np.full((H, W), -1, np.int32)
        self.S = np.zeros((H, W), np.float32)
        self.T = np.zeros((H, W), np.float32)
        self.L = np.zeros((H, W, 3), np.float32)
        self.surf_shader = []
        self.zmax, self.zmin = zmax, zmin
        sfr = lump(3)
        for i in range(len(sfr) // 108):
            f = struct.unpack_from("<7i", sfr, i * 108)
            sn, fog, st, fv, nvx, fi, nix = f
            lmn = struct.unpack_from("<i", sfr, i * 108 + 28)[0]
            if not (0 <= sn < len(self.names)) or st not in (1, 2, 3):
                continue
            if st in (1, 3):
                if nix < 3:
                    continue
                idx = IX[fi:fi + nix].reshape(-1, 3) + fv
            else:
                pw, ph = struct.unpack_from("<2i", sfr, i * 108 + 96)
                if not (pw >= 2 and ph >= 2 and pw * ph == nvx):
                    continue
                g = np.arange(pw * ph).reshape(ph, pw)
                q = np.stack([g[:-1, :-1].ravel(), g[:-1, 1:].ravel(), g[1:, :-1].ravel(), g[1:, 1:].ravel()], 1)
                idx = np.concatenate([q[:, [0, 1, 2]], q[:, [1, 3, 2]]]) + fv
            sid = len(self.surf_shader)
            self.surf_shader.append(self.names[sn])
            P = V["xyz"][idx].astype(np.float64)
            if P[..., 0].max() < x0 or P[..., 0].min() > x1 or P[..., 1].max() < y0 or P[..., 1].min() > y1:
                continue
            ST = V["st"][idx].astype(np.float64)
            if self.names[sn] in tcgen:                       # shader tcGen vector: s = xyz.v0, t = xyz.v1
                v0, v1 = tcgen[self.names[sn]]
                ST = np.stack([P @ np.asarray(v0, float), P @ np.asarray(v1, float)], -1)
            LMC = V["lm"][idx].astype(np.float64)
            for k in range(len(idx)):
                self._tri(P[k], ST[k], LMC[k], lmn, sid, nz_min)
        tr = lump(22)
        for i in range(len(tr) // 388):
            o = i * 388
            lscale, ps, pt = struct.unpack_from("<BBB", tr, o + 1)
            tc = np.array(struct.unpack_from("<8f", tr, o + 4)).reshape(2, 2, 2)
            px, py = struct.unpack_from("<bb", tr, o + 36)
            zb = struct.unpack_from("<h", tr, o + 38)[0]
            shn, lmi = struct.unpack_from("<HH", tr, o + 40)
            hm = np.frombuffer(tr[o + 304:o + 304 + 81], "u1").reshape(9, 9).astype(np.float64) * 2 + zb
            X0, Y0 = px * 64.0, py * 64.0
            if X0 + 512 < x0 or X0 > x1 or Y0 + 512 < y0 or Y0 > y1:
                continue
            sid = len(self.surf_shader)
            self.surf_shader.append(self.names[shn])
            lsz = (lscale * 8 + 1 - 1) / float(LM)
            ls0, lt0 = (ps + 0.5) / LM, (pt + 0.5) / LM
            # tMin/sMin floor offsets do not matter for tiling textures
            for r in range(8):
                for c in range(8):
                    u0, u1, v0, v1 = c / 8.0, (c + 1) / 8.0, r / 8.0, (r + 1) / 8.0
                    def pt_(u, v):
                        xyz = (X0 + 512 * u, Y0 + 512 * v, hm[int(round(v * 8)), int(round(u * 8))])
                        s = (tc[0, 0] * (1 - u) * (1 - v) + tc[1, 0] * u * (1 - v) + tc[0, 1] * (1 - u) * v
                             + tc[1, 1] * u * v)
                        return xyz, s, (ls0 + lsz * u, lt0 + lsz * v)
                    a, b_, c_, d = pt_(u0, v0), pt_(u1, v0), pt_(u0, v1), pt_(u1, v1)
                    for tri in ((a, b_, d), (a, d, c_)):
                        self._tri(np.array([t[0] for t in tri]), np.array([t[1] for t in tri]),
                                  np.array([t[2] for t in tri]), lmi, sid, -1.0)
        self.surf_shader = np.array(self.surf_shader, dtype=object)

    def _tri(self, P, ST, LMC, lmn, sid, nz_min):
        n = np.cross(P[1] - P[0], P[2] - P[0])
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            return
        if nz_min > -1 and n[2] / ln < nz_min and -n[2] / ln < nz_min:
            return
        if min(P[:, 2]) > self.zmax or max(P[:, 2]) < self.zmin:
            return
        x0, y0 = self.region[0], self.region[1]
        gx = (P[:, 0] - x0) / self.res - 0.5
        gy = (P[:, 1] - y0) / self.res - 0.5
        ia, ib = max(0, int(np.floor(gx.min()))), min(self.W - 1, int(np.ceil(gx.max())))
        ja, jb = max(0, int(np.floor(gy.min()))), min(self.H - 1, int(np.ceil(gy.max())))
        if ia > ib or ja > jb:
            return
        xs, ys = np.meshgrid(np.arange(ia, ib + 1, dtype=np.float64), np.arange(ja, jb + 1, dtype=np.float64))
        d = (gy[1] - gy[2]) * (gx[0] - gx[2]) + (gx[2] - gx[1]) * (gy[0] - gy[2])
        if abs(d) < 1e-12:
            return
        w0 = ((gy[1] - gy[2]) * (xs - gx[2]) + (gx[2] - gx[1]) * (ys - gy[2])) / d
        w1 = ((gy[2] - gy[0]) * (xs - gx[2]) + (gx[0] - gx[2]) * (ys - gy[2])) / d
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any():
            return
        z = w0 * P[0, 2] + w1 * P[1, 2] + w2 * P[2, 2]
        sl = (slice(ja, jb + 1), slice(ia, ib + 1))
        m &= (z > self.Z[sl]) & (z <= self.zmax)
        if not m.any():
            return
        self.Z[sl][m] = z[m]
        self.SID[sl][m] = sid
        self.S[sl][m] = (w0 * ST[0, 0] + w1 * ST[1, 0] + w2 * ST[2, 0])[m]
        self.T[sl][m] = (w0 * ST[0, 1] + w1 * ST[1, 1] + w2 * ST[2, 1])[m]
        if 0 <= lmn < len(self.lm):
            lu = (w0 * LMC[0, 0] + w1 * LMC[1, 0] + w2 * LMC[2, 0])[m] * LM - 0.5
            lv = (w0 * LMC[0, 1] + w1 * LMC[1, 1] + w2 * LMC[2, 1])[m] * LM - 0.5
            self.L[sl][m] = _bilin(self.lm[lmn], lu, lv, wrap=False)
        else:
            self.L[sl][m] = 128.0

    # ---------------------------------------------------------------------------------------------------
    def shader_mask(self, pattern):
        import re
        rx = re.compile(pattern)
        ok = np.array([bool(rx.search(s)) for s in self.surf_shader] + [False])
        return ok[self.SID]

    def render(self, tex_of_shader, eye, yaw, pitch, fov=80.0, size=(1280, 720), lm_gain=2.0, aniso=4.0,
               sky=(150, 160, 170)):
        Wd, Hd = size
        ex, ey, ez = eye
        fx = np.tan(np.radians(fov) / 2)
        fy = fx * Hd / Wd
        u = (np.arange(Wd) + 0.5) / Wd * 2 - 1
        v = 1 - (np.arange(Hd) + 0.5) / Hd * 2
        U, Vv = np.meshgrid(u * fx, v * fy)
        cy, sy, cp, sp = np.cos(np.radians(yaw)), np.sin(np.radians(yaw)), np.cos(np.radians(pitch)), np.sin(np.radians(pitch))
        fwd = np.array([cy * cp, sy * cp, -sp])            # pitch > 0 looks down (engine convention)
        right = np.array([sy, -cy, 0.0])
        up = np.cross(right, fwd)
        D = fwd[None, None] + U[..., None] * right[None, None] + Vv[..., None] * up[None, None]
        # height-field intersection by fixed-point iteration on the plane z = h(x, y)
        valid = D[..., 2] < -1e-4
        h = np.full(U.shape, np.median(self.Z[self.Z > -1e8]) if (self.Z > -1e8).any() else 0.0)
        for _ in range(6):
            t = np.where(valid, (h - ez) / np.minimum(D[..., 2], -1e-4), 0)
            X, Y = ex + t * D[..., 0], ey + t * D[..., 1]
            gx, gy = (X - self.region[0]) / self.res - 0.5, (Y - self.region[1]) / self.res - 0.5
            inb = valid & (gx >= 0) & (gx < self.W - 1) & (gy >= 0) & (gy < self.H - 1)
            ii = np.clip(np.round(gx).astype(int), 0, self.W - 1)
            jj = np.clip(np.round(gy).astype(int), 0, self.H - 1)
            zz = self.Z[jj, ii]
            h = np.where(inb & (zz > -1e8), zz, h)
        sid = np.where(inb, self.SID[jj, ii], -1)
        # bilinear s/t inside one surface
        i0, j0 = np.clip(np.floor(gx).astype(int), 0, self.W - 2), np.clip(np.floor(gy).astype(int), 0, self.H - 2)
        fxw, fyw = np.clip(gx - i0, 0, 1), np.clip(gy - j0, 0, 1)
        same = ((self.SID[j0, i0] == sid) & (self.SID[j0, i0 + 1] == sid) & (self.SID[j0 + 1, i0] == sid)
                & (self.SID[j0 + 1, i0 + 1] == sid))
        def bl(A):
            return (A[j0, i0] * (1 - fxw) * (1 - fyw) + A[j0, i0 + 1] * fxw * (1 - fyw)
                    + A[j0 + 1, i0] * (1 - fxw) * fyw + A[j0 + 1, i0 + 1] * fxw * fyw)
        S = np.where(same, bl(self.S), self.S[jj, ii])
        T = np.where(same, bl(self.T), self.T[jj, ii])
        Lr = np.where(same[..., None], np.stack([bl(self.L[..., c]) for c in range(3)], -1), self.L[jj, ii])
        out = np.empty((Hd, Wd, 3), np.float32)
        out[:] = sky
        for s_id in np.unique(sid):
            if s_id < 0:
                continue
            m = sid == s_id
            tex = tex_of_shader(self.surf_shader[s_id])
            if tex is None:
                out[m] = (255, 0, 255)
                continue
            out[m] = 0
            self._sample_into(out, m, tex, S, T, Lr, lm_gain, aniso)
        return np.clip(out, 0, 255).astype(np.uint8)

    def _sample_into(self, out, m, pyr, S, T, Lr, lm_gain, aniso):
        th, tw = pyr[0].shape[:2]
        su, tv = S * tw, T * th
        # screen derivatives (texels per pixel)
        dsx, dsy = np.gradient(su, axis=1), np.gradient(su, axis=0)
        dtx, dty = np.gradient(tv, axis=1), np.gradient(tv, axis=0)
        a = np.hypot(dsx, dtx)
        b = np.hypot(dsy, dty)
        big, small = np.maximum(a, b), np.minimum(a, b)
        foot = np.maximum(small, big / aniso)
        lev = np.clip(np.log2(np.maximum(foot, 1e-6)), 0, len(pyr) - 1)
        lev = np.where(m, lev, 0)
        l0 = np.floor(lev).astype(int)
        fr = lev - l0
        col = np.zeros(out.shape, np.float32)
        for k in np.unique(l0[m]):
            mk = m & (l0 == k)
            c0 = _bilin(pyr[k], su[mk] / (2 ** k) - 0.5, tv[mk] / (2 ** k) - 0.5, wrap=True)
            k1 = min(k + 1, len(pyr) - 1)
            c1 = _bilin(pyr[k1], su[mk] / (2 ** k1) - 0.5, tv[mk] / (2 ** k1) - 0.5, wrap=True)
            f = fr[mk][:, None]
            col[mk] = c0 * (1 - f) + c1 * f
        out[m] = col[m] * np.clip(Lr[m] * lm_gain / 255.0, 0, 255.0 / 128)

    def topdown(self, tex_of_shader, px_per_unit=1.0, lm_gain=2.0, lit=True):
        """straight-down view of the region (north up), textures sampled at their own resolution."""
        x0, y0, x1, y1 = self.region
        Wd, Hd = int((x1 - x0) * px_per_unit), int((y1 - y0) * px_per_unit)
        xs = x0 + (np.arange(Wd) + 0.5) / px_per_unit
        ys = y1 - (np.arange(Hd) + 0.5) / px_per_unit
        X, Y = np.meshgrid(xs, ys)
        gx, gy = (X - x0) / self.res - 0.5, (Y - y0) / self.res - 0.5
        i0, j0 = np.clip(np.floor(gx).astype(int), 0, self.W - 2), np.clip(np.floor(gy).astype(int), 0, self.H - 2)
        ii = np.clip(np.round(gx).astype(int), 0, self.W - 1)
        jj = np.clip(np.round(gy).astype(int), 0, self.H - 1)
        sid = self.SID[jj, ii]
        fxw, fyw = np.clip(gx - i0, 0, 1), np.clip(gy - j0, 0, 1)
        same = ((self.SID[j0, i0] == sid) & (self.SID[j0, i0 + 1] == sid) & (self.SID[j0 + 1, i0] == sid)
                & (self.SID[j0 + 1, i0 + 1] == sid))
        def bl(A):
            return (A[j0, i0] * (1 - fxw) * (1 - fyw) + A[j0, i0 + 1] * fxw * (1 - fyw)
                    + A[j0 + 1, i0] * (1 - fxw) * fyw + A[j0 + 1, i0 + 1] * fxw * fyw)
        S = np.where(same, bl(self.S), self.S[jj, ii])
        T = np.where(same, bl(self.T), self.T[jj, ii])
        Lr = np.where(same[..., None], np.stack([bl(self.L[..., c]) for c in range(3)], -1), self.L[jj, ii])
        if not lit:
            Lr = np.full_like(Lr, 128.0 / lm_gain)
        out = np.zeros((Hd, Wd, 3), np.float32)
        for s_id in np.unique(sid):
            if s_id < 0:
                continue
            m = sid == s_id
            tex = tex_of_shader(self.surf_shader[s_id])
            if tex is None:
                out[m] = (255, 0, 255)
                continue
            self._sample_into(out, m, tex, S, T, Lr, lm_gain, 4.0)
        return np.clip(out, 0, 255).astype(np.uint8), sid


def _bilin(img, u, v, wrap=True):
    h, w = img.shape[:2]
    u0 = np.floor(u).astype(np.int64)
    v0 = np.floor(v).astype(np.int64)
    fu, fv = (u - u0)[:, None], (v - v0)[:, None]
    if wrap:
        a, b = u0 % w, (u0 + 1) % w
        c, d = v0 % h, (v0 + 1) % h
    else:
        a, b = np.clip(u0, 0, w - 1), np.clip(u0 + 1, 0, w - 1)
        c, d = np.clip(v0, 0, h - 1), np.clip(v0 + 1, 0, h - 1)
    return (img[c, a] * (1 - fu) * (1 - fv) + img[c, b] * fu * (1 - fv) + img[d, a] * (1 - fu) * fv
            + img[d, b] * fu * fv)


def pyramid(rgb):
    """float32 box-filtered mip chain down to 1x1 (what the DDS mips / GL generate)."""
    p = [np.asarray(rgb, np.float32)]
    while p[-1].shape[0] > 1 or p[-1].shape[1] > 1:
        a = p[-1]
        h, w = a.shape[:2]
        h2, w2 = max(1, h // 2), max(1, w // 2)
        if h >= 2 and w >= 2:
            a = a[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2, 3).mean((1, 3))
        elif h >= 2:
            a = a[:h2 * 2].reshape(h2, 2, w, 3).mean(1)
        else:
            a = a[:, :w2 * 2].reshape(h, w2, 2, 3).mean(2)
        p.append(a)
    return p
