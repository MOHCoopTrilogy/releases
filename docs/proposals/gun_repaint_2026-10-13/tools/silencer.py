"""Shared silencer sheet repaint: textures/models/weapons/colt/colt45s2 (today 320x240 .tga, near black) ->
2048x2048 DXT1 .dds on the SAME UV layout (surface Cylinder1 of six skds: silenced Colt, Beretta, Garand, grease gun,
Kar98 sniper, Mosin sniper - all six carry identical UVs, asserted below; mesh, tiks and shader untouched).

    python silencer.py            writes assets/textures/models/weapons/colt/colt45s2.dds
    python silencer.py --preview  + evidence/silencer_sheet_old_new.jpg, evidence/silencer_soft3d.jpg (software render)

How it is painted (seeded, same output every run, no source pixels at all - everything is procedural):
  * the tube's two half shells are PLANAR projections (texels get scarce towards the side seams), so nothing is
    painted in sheet space: every texel's bone-space position is baked from the mesh and turned into tube coordinates
    (t along the axis 0 rear .. 1 muzzle, theta round the axis). All detail is a function of (t, theta) or is sampled
    from an unwrapped (t, theta) canvas that is periodic in theta -> continuous across both seams, no stretch.
  * dark blued / parkerized steel, lathe lines round the tube, fine grain, soft mottle, a broken sheen along each
    shell's centre line (these shaders are rgbGen lightingSpherical: no specular, the sheen has to be in the diffuse;
    it is on BOTH shells because the six guns mount the tube with different roll),
  * end caps: a joint groove with a worn lip at each end, diamond knurling on both caps (faded out where the planar
    projection has too few texels to hold it), worn muzzle rim,
  * muzzle face: turning rings, recess step, dark bore, soot round the bore, worn chamfer; rear face plain,
  * handling scratches and nicks drawn on the canvas.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import rplib as L
import soft3d

STEM = "textures/models/weapons/colt/colt45s2"
SKDS = ["models/weapons/beretta/berettasilenced.skd", "models/weapons/colt45/colt45_silenced.skd",
        "models/weapons/garand/garand_silenced.skd", "models/weapons/greasegun/greasegun_silenced.skd",
        "models/weapons/kar98sniper/kar98snipersilenced.skd", "models/weapons/nagant/nagantsnipersilenced.skd"]
SURF = "Cylinder1"
N = 2048
BASE = np.array([35.0, 36.0, 38.5])          # blued / dark parkerized steel (first engine look at 29: too black beside the Colt)
WEAR = np.array([118.0, 116.0, 110.0])       # bare worn steel
SOOT = np.array([9.0, 9.0, 9.5])
CT, CTH = 4096, 1920                         # unwrapped canvas: t along x, theta (360 deg) along y; square in gun space
KN = 24                                      # knurl diamonds round the tube
CAP_R, CAP_F = 0.135, 0.925                  # joint grooves (t)
KNURL = ((0.028, 0.112), (0.941, 0.978))
SEED = 1943


def sub(s, ids):
    m = np.isin(s["isl"], ids)
    d = dict(s); d["tris"] = s["tris"][m]; d["isl"] = s["isl"][m]
    return d


def frame(s):
    """tube frame from the mesh: islands by triangle count (caps 12, shells 72, collar 84)."""
    cnt = {k: int((s["isl"] == k).sum()) for k in range(s["n"])}
    caps = [k for k, c in cnt.items() if c == 12]; shells = [k for k, c in cnt.items() if c == 72]
    collar = [k for k, c in cnt.items() if c == 84]
    assert len(caps) == 2 and len(shells) == 2 and len(collar) == 2, cnt
    cen = {k: s["pos"][np.unique(s["tris"][s["isl"] == k])].mean(0) for k in cnt}
    ccol = (cen[collar[0]] + cen[collar[1]]) / 2
    caps.sort(key=lambda k: np.linalg.norm(cen[k] - ccol))
    rear, muz = caps
    a = cen[muz] - cen[rear]; Lt = np.linalg.norm(a); a /= Lt
    vi = np.unique(s["tris"][np.isin(s["isl"], shells)])
    d = s["pos"][vi] - cen[rear]
    rad = d - np.outer(d @ a, a)
    R = np.linalg.norm(rad, axis=1).max()
    n2 = s["nrm"][np.unique(s["tris"][s["isl"] == shells[0]])].mean(0)
    e1 = n2 - (n2 @ a) * a; e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    return dict(rear=rear, muz=muz, shells=shells, collar=collar, o=cen[rear], a=a, L=Lt, R=R, e1=e1, e2=e2)


def canvas():
    """unwrapped layers, periodic in theta (rows): lines (lathe), grain, mottle, streak, scratch, patch."""
    rs = np.random.RandomState(SEED)
    fine = ndi.gaussian_filter1d(rs.rand(CT).astype(np.float32), 0.8, mode="wrap")
    mid = ndi.gaussian_filter1d(rs.rand(CT).astype(np.float32), 3.0, mode="wrap")
    fine = (fine - fine.mean()) / fine.std(); mid = (mid - mid.mean()) / mid.std()
    amp = 0.75 + 0.25 * np.clip(L.noise((CTH, CT), 90, SEED + 1), -1.5, 1.5) / 1.5
    lines = 1 + (0.060 * fine + 0.040 * mid)[None, :] * amp
    cut = np.zeros(CT, np.float32)                      # a few distinct tool marks
    for x in rs.randint(0, CT, 46):
        cut[x] = rs.uniform(0.05, 0.14)
    cut = ndi.gaussian_filter1d(cut, 0.7, mode="wrap") * 2.2
    lines = lines * (1 - cut[None, :] * (0.6 + 0.4 * amp))
    grain = 1 + 0.040 * L.noise((CTH, CT), 0.75, SEED + 2)
    mott = 1 + 0.035 * L.noise((CTH, CT), 38, SEED + 3) + 0.045 * L.noise((CTH, CT), 170, SEED + 4)
    st = np.random.RandomState(SEED + 5).rand(CTH, CT).astype(np.float32)
    st = ndi.gaussian_filter(st, (1.6, 70), mode="wrap"); st = (st - st.mean()) / st.std()
    streak = np.clip(1 + 0.30 * st, 0.4, 1.6)
    # scratches: thin bright lines, mostly along the tube (drawn 3x for the theta wrap), a few nicks
    im = Image.new("L", (CT, CTH), 0); d = ImageDraw.Draw(im)
    for i in range(210):
        x = rs.uniform(0, CT); y = rs.uniform(0, CTH)
        ang = rs.normal(0, 0.16) if rs.rand() < 0.72 else rs.uniform(0, np.pi)
        ln = rs.uniform(25, 150) if rs.rand() < 0.75 else rs.uniform(150, 520)
        v = int(rs.uniform(40, 150)); dx = np.cos(ang) * ln; dy = np.sin(ang) * ln
        bend = rs.normal(0, 0.03) * ln
        for oy in (-CTH, 0, CTH):
            pts = [(x, y + oy), (x + dx / 2 - np.sin(ang) * bend, y + oy + dy / 2 + np.cos(ang) * bend), (x + dx, y + oy + dy)]
            d.line(pts, fill=v, width=1 if rs.rand() < 0.8 else 2)
    for i in range(90):
        x = rs.uniform(0, CT); y = rs.uniform(0, CTH); r = rs.uniform(0.8, 2.6)
        d.ellipse([x - r * 1.6, y - r, x + r * 1.6, y + r], fill=int(rs.uniform(70, 170)))
    scr = ndi.gaussian_filter(np.asarray(im, np.float32) / 255, 0.55)
    scrb = ndi.gaussian_filter(scr, (5.0, 0.6), mode="wrap")     # for the texel-poor zone next to the seams
    p = L.noise((CTH, CT), 55, SEED + 6) * 0.6 + L.noise((CTH, CT), 150, SEED + 7) * 0.6
    patch = np.clip((p - 0.95) / 0.9, 0, 1)             # sparse soft rubbed areas
    brk = np.clip(0.55 + 0.30 * L.noise((CTH, CT), 5, SEED + 8) + 0.25 * L.noise((CTH, CT), 22, SEED + 9), 0.05, 1.0)
    return dict(lines=lines, grain=grain, mott=mott, streak=streak, scr=scr, scrb=scrb, patch=patch, brk=brk)


def samp(layer, t, th):
    x = np.clip(t, 0, 1) * (CT - 1)
    y = (th / (2 * np.pi)) % 1.0 * CTH
    return ndi.map_coordinates(layer, [y, x], order=1, mode="grid-wrap")


def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def paint(s, f, cv):
    pos, nrm, isl = L.bake(s, N, N)
    tp, tn, ti = L.bake(sub(s, f["shells"]), N, N)       # shells win where the collar's strip overlaps them
    tm = ti >= 0
    pos[tm] = tp[tm]; isl[tm] = ti[tm]
    mask = isl >= 0
    d = pos - f["o"][None, None, :]
    ax = d @ f["a"]
    rad = d - ax[..., None] * f["a"][None, None, :]
    t = ax / f["L"]
    th = np.arctan2(rad @ f["e2"], rad @ f["e1"])
    r = np.linalg.norm(rad, axis=2) / f["R"]
    col = np.zeros((N, N, 3), np.float32)
    rs = np.random.RandomState(SEED + 20)

    # ---------------- tube shells ----------------
    for k, phi0 in ((f["shells"][0], 0.0), (f["shells"][1], np.pi)):
        m = isl == k
        phi = np.angle(np.exp(1j * (th - phi0)))             # angle from this shell's centre line
        cphi = np.cos(phi)
        lum = samp(cv["lines"], t, th) * samp(cv["grain"], t, th) * samp(cv["mott"], t, th)
        shade = (0.82 + 0.16 * np.clip(cphi, 0, 1) + 0.60 * np.exp(-(phi / 0.36) ** 2) * samp(cv["streak"], t, th)
                 + 0.16 * np.exp(-(phi / 0.85) ** 2))
        tone = np.where((t < CAP_R) | (t > CAP_F), 1.10, 1.0)   # the caps are separate parts: a shade lighter
        # knurling on both caps
        dth = 2 * np.pi / KN
        pt = dth * f["R"] / f["L"]
        a_ = t / pt + th / dth; b_ = t / pt - th / dth
        fa = a_ - np.floor(a_); fb = b_ - np.floor(b_)
        hgt = 1 - np.maximum(np.abs(2 * fa - 1), np.abs(2 * fb - 1)) ** 2.4
        slope = (fa - 0.5) + (fb - 0.5)
        kl = 0.70 + 0.40 * hgt + 0.17 * slope * (1 - 0.5 * hgt)
        inb = np.zeros_like(t)
        for (k0, k1) in KNURL:
            inb = np.maximum(inb, smooth(t, k0, k0 + 0.004) * (1 - smooth(t, k1 - 0.004, k1)))
        fade = smooth(cphi, 0.035, 0.11)                       # too few texels near the seams: fade to plain
        kmix = inb * fade
        # where the knurl is faded out the band keeps the knurl's mean tone (no light stripe along the seam)
        lum_k = lum * (1 - inb) + (0.35 + 0.65 * lum) * kl * kmix + 0.90 * lum * (inb - kmix)
        # plain ring left and right of each band so the knurl sits on a turned shoulder
        L_ = lum_k * shade * tone
        c = BASE[None, None, :] * L_[..., None]
        # wear ---------------------------------------------------------------------------------------
        brk = samp(cv["brk"], t, th)                   # isotropic in gun space: no stripes, no seam stretch
        w = np.zeros_like(t)
        w += smooth(t, 0.9905, 0.9985) * 0.80 * np.clip(brk + 0.15, 0, 1)      # muzzle rim
        w += (1 - smooth(t, 0.0015, 0.0065)) * 0.28 * brk                       # rear rim
        for g, side in ((CAP_R, -1), (CAP_F, +1)):                              # worn lip on the cap side of a joint
            lip = np.exp(-((t - (g + side * 0.0042)) / 0.0018) ** 2)
            w += lip * 0.55 * brk
        w += kmix * smooth(hgt, 0.72, 0.95) * 0.34 * np.clip(0.3 + brk, 0, 1)   # knurl tops polished by the hand
        sharp = smooth(cphi, 0.15, 0.45)
        scr = samp(cv["scr"], t, th) * sharp + samp(cv["scrb"], t, th) * (1 - sharp)
        w += scr * 0.75
        w += samp(cv["patch"], t, th) * 0.10 * (0.5 + 0.5 * samp(cv["streak"], t, th))
        w = np.clip(w, 0, 0.72)
        c = c * (1 - w[..., None]) + WEAR[None, None, :] * (w * (0.72 + 0.28 * np.clip(shade, 0, 1.4)))[..., None]
        # joint grooves: dark cut, soft dirt next to it
        for g in (CAP_R, CAP_F):
            cut = np.exp(-((t - g) / 0.0019) ** 2)
            dirt = np.exp(-((t - g) / 0.007) ** 2)
            c *= (1 - 0.80 * cut - 0.12 * dirt * (1 - cut))[..., None]
        col[m] = c[m]

    # ---------------- end faces ----------------
    ring1 = ndi.gaussian_filter1d(rs.rand(1024).astype(np.float32), 1.1); ring1 = (ring1 - ring1.mean()) / ring1.std()
    ring2 = ndi.gaussian_filter1d(rs.rand(1024).astype(np.float32), 6.0); ring2 = (ring2 - ring2.mean()) / ring2.std()
    ang = np.arctan2(rad @ f["e2"], rad @ f["e1"])
    rr = np.clip(r, 0, 1.05)
    rings = 1 + 0.075 * np.interp(rr * 900, np.arange(1024), ring1) + 0.05 * np.interp(rr * 900, np.arange(1024), ring2)
    g2 = 1 + 0.035 * L.noise((N, N), 0.8, SEED + 40)
    an = np.random.RandomState(SEED + 41).rand(720).astype(np.float32)
    an = ndi.gaussian_filter1d(an, 3, mode="wrap"); an = (an - an.mean()) / an.std()
    spoke = np.interp((ang % (2 * np.pi)) / (2 * np.pi) * 720, np.arange(720), an, period=720)
    nz = L.noise((N, N), 7, SEED + 42)
    # muzzle face
    m = isl == f["muz"]
    lum = rings * g2 * (0.93 + 0.10 * smooth(rr, 0.2, 1.0))
    lum = lum * np.where(rr < 0.60, 0.90, 1.0)                                  # recessed centre a shade darker
    c = BASE[None, None, :] * 1.10 * lum[..., None]
    soot = np.exp(-np.clip(rr - 0.27, 0, 9) / (0.11 + 0.035 * spoke)) * (0.62 + 0.12 * nz)
    soot = np.clip(soot, 0, 0.8) * (rr < 0.60)
    c = c * (1 - soot[..., None]) + SOOT[None, None, :] * soot[..., None]
    step = np.exp(-((rr - 0.60) / 0.012) ** 2)
    c *= (1 - 0.65 * step)[..., None]
    w = np.exp(-((rr - 0.632) / 0.012) ** 2) * 0.40 * np.clip(0.55 + 0.4 * nz, 0, 1)        # step's lit lip
    nf = L.noise((N, N), 2.2, SEED + 43)
    w += smooth(rr, 0.925, 0.962) * 0.50 * np.clip(0.62 + 0.22 * nz + 0.22 * nf, 0.2, 1)     # chamfer
    w += np.exp(-((rr - 0.292) / 0.011) ** 2) * 0.16                                          # crown of the bore
    w = np.clip(w, 0, 0.7)
    c = c * (1 - w[..., None]) + WEAR[None, None, :] * w[..., None]
    bore = 1 - smooth(rr, 0.255, 0.275)
    c = c * (1 - bore[..., None]) + np.array([4.0, 4.0, 4.5])[None, None, :] * bore[..., None]
    col[m] = c[m]
    # rear face (mostly hidden by the collar)
    m = isl == f["rear"]
    lum = rings * g2 * (0.80 + 0.12 * smooth(rr, 0.3, 1.0))
    c = BASE[None, None, :] * lum[..., None]
    w = smooth(rr, 0.90, 0.96) * 0.30 * np.clip(0.6 + 0.4 * nz, 0, 1)
    c = c * (1 - w[..., None]) + WEAR[None, None, :] * w[..., None]
    hole = 1 - smooth(rr, 0.40, 0.44)
    c *= (1 - 0.6 * hole)[..., None]
    col[m] = c[m]

    # ---------------- collar (its strip is a few texels wide: plain turned steel) ----------------
    m = np.isin(isl, f["collar"])
    axr = ax / f["R"]
    lines = 1 + 0.07 * np.interp((axr * 220) % 1024, np.arange(1024), ring1, period=1024)
    c = BASE[None, None, :] * (0.98 * lines * g2 * (1 + 0.04 * nz))[..., None]
    col[m] = c[m]
    out = L.pad(col, mask, 28, fill=tuple(BASE * 0.95))
    return out, mask, dict(t=t, th=th, isl=isl)


def soft_preview(S, new, old, path):
    """software renders: old | new, side (seam facing), top, three-quarter muzzle, three-quarter rear."""
    f = frame(S)
    s = S
    views = [(0, 0, 0), (0, 90, 0), (55, 70, 20), (-125, 70, 20)]
    # put the tube axis on x for the renderer
    B = np.stack([f["a"], f["e2"], f["e1"]], 0)           # rows: new x (axis), y (seam side), z (shell centre)
    s2 = dict(s); s2["pos"] = (s["pos"] - f["o"]) @ B.T; s2["nrm"] = s["nrm"] @ B.T
    sc = 900.0 / f["L"]
    rows = []
    for (yaw, pitch, roll) in views:
        a = soft3d.render([(s2, old)], yaw, pitch, scale=sc, roll=roll, gain=1.6, bg=(150, 156, 160))
        b = soft3d.render([(s2, new)], yaw, pitch, scale=sc, roll=roll, gain=1.6, bg=(150, 156, 160))
        h = max(a.shape[0], b.shape[0]); w = max(a.shape[1], b.shape[1])
        row = np.zeros((h, 2 * w + 10, 3), np.float32) + 255
        row[:a.shape[0], :a.shape[1]] = a; row[:b.shape[0], w + 10:w + 10 + b.shape[1]] = b
        rows.append(row)
    W = max(r.shape[1] for r in rows); H = sum(r.shape[0] + 6 for r in rows)
    sh = np.zeros((H, W, 3), np.float32) + 255; y = 0
    for r_ in rows:
        sh[y:y + r_.shape[0], :r_.shape[1]] = r_; y += r_.shape[0] + 6
    Image.fromarray(sh.astype(np.uint8)).save(path, quality=90)
    return path


def main():
    pv = "--preview" in sys.argv
    S = [L.load_skd(p, [SURF])[SURF] for p in SKDS]
    for p, s in zip(SKDS[1:], S[1:]):
        assert s["uv"].shape == S[0]["uv"].shape and np.abs(s["uv"] - S[0]["uv"]).max() < 1e-5, p
        assert (s["tris"] == S[0]["tris"]).all(), p
    print("six skds: identical UVs and triangles on", SURF)
    s = S[0]
    f = frame(s)
    print("frame: L %.2f R %.2f rear isl %d muzzle isl %d shells %s collar %s" % (f["L"], f["R"], f["rear"], f["muz"], f["shells"], f["collar"]))
    cv = canvas()
    new, mask, dbg = paint(s, f, cv)
    if "--draft" in sys.argv:                 # look at the paint without the (slow) DXT encode; writes no asset
        back = np.clip(new, 0, 255)
    else:
        p, n = L.write_dds(new, STEM + ".dds")
        back = L.dds_decode_top(p)
        print("wrote", p, n, "bytes; mean", new[mask].mean(0).round(1), "dxt err (mean abs)", float(np.abs(back - np.clip(new, 0, 255)).mean().round(2)))
    if pv:
        old, vp, pak = L.read_image(STEM)
        print("today:", vp, pak, old.shape)
        oldu = np.asarray(Image.fromarray(old.astype(np.uint8)).resize((N, N), Image.BICUBIC), np.float32)
        L.side_by_side(oldu, back, os.path.join(L.EVI, "silencer_sheet_old_new.jpg"), h=900,
                       labels=("today 320x240 tga (shown x4 brightness-true)", "repaint 2048x2048 dds (decoded DXT1)"))
        soft_preview(s, back, oldu, os.path.join(L.EVI, "silencer_soft3d.jpg"))
        # 1:1 crops of the decoded dds: rear cap + knurl, mid tube, muzzle end, muzzle face
        crops = [(260, 150, 760, 480), (900, 150, 1400, 480), (1010, 520, 1300, 850), (40, 1090, 580, 1790)]
        tiles = [Image.fromarray(back.astype(np.uint8)).crop(c) for c in crops]
        W = sum(t_.size[0] for t_ in tiles) + 8 * (len(tiles) - 1); H = max(t_.size[1] for t_ in tiles)
        sh = Image.new("RGB", (W, H), (255, 255, 255)); x = 0
        for t_ in tiles:
            sh.paste(t_, (x, 0)); x += t_.size[0] + 8
        sh.save(os.path.join(L.EVI, "silencer_sheet_crops_1to1.jpg"), quality=92)


if __name__ == "__main__":
    main()
