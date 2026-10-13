"""OUR OWN diffuse sheet for the double-barrel shotgun, painted into the mesh's UV atlas by script (seeded: the same
output every run). Replaces dbs_tex.py, which composed the sheet from the author's baked diffuse / glossy sheets.

    python tools/dbs_skin.py bake       build/skin_bake.npz   (per texel: gun-space position, normal, triangle, curvature)
    python tools/dbs_skin.py paint      build/dbs_diffuse.png + assets/textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg
    python tools/dbs_skin.py view       build/_skin_view.jpg  (offline orthographic look: both sides, top, bottom, breech)
    python tools/dbs_skin.py info       geometry numbers the painter keys on

Inputs (and nothing else):
  * build/own/high_parts.json   the author's MESH (CC0), our UV atlas (Blender smart project) and the material-slot
                                flag "this face is wood" - written by `bl_build.py --own`, which opens neither the
                                author's baked sheets nor his low file;
  * build/own/bake_ao.npy       ambient occlusion we bake from that geometry (each part alone);
  * build/src/kar98_retail.png  the RETAIL Kar98 sheet (main/Pak2.pk3, 1024 x 512; written by
                                `tools/srclist.py --save textures/models/weapons/kar98/kar98`): its butt-stock wood,
                                flattened (its baked shading divided out), gives the walnut's colour and figure.
The steel is procedural (no source image). No pixel of the author's doubleBarrel*.png sheets and nothing from the images packed in his .blend files is read.

Everything is laid out in GUN space (source frame: hinge pin at the origin, +x muzzle, +y left, +z up; cm = 13.25 x
Blender units), so the grain, the scratches and the checkering run across UV seams without a break:
  WOOD   walnut: the retail Kar98 wood sampled along the part's own long axis (grip: its principal axis; forend: the barrel
         axis) as a solid (the across-grain coordinate leans through the wood, so the top, the sides and the two
         halves differ), fine pores added (the atlas is ~3 x denser than the Kar98 sheet), hand-darkened where it is
         held, rubbed light on the convex edges, cut checkering panels on the grip sides and the forend sides;
  STEEL  blued barrels / lever / triggers / guard: flat blue-black base, brushing and scratches along the barrel axis,
         a baked top light (the shader is diffuse only), worn convex edges and dark creases from the mesh curvature,
         bright muzzle rims, sooted bores, polished breech faces;
         receiver: a little colour case-hardening (grey / blue / straw mottle) and an engraved border line on its
         side flats.
"""
import os, sys, json, math, io
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
import dbslib as L

N = 2048
CM = 13.25
OWN = os.path.join(L.BUILD, 'own')
SRCD = os.path.join(L.BUILD, 'src')
PARTS = ('barrels', 'body', 'lever', 'trig_f', 'trig_r')
NAME = 'coop_dbshotgun'
TDIR = os.path.join(L.ASSETS, 'textures', 'models', 'weapons', NAME)

# ---- tunables (sRGB 0..255 unless said)
WALNUT = np.array([60.0, 35.0, 23.0])        # mean of the wood
WOOD_CONTRAST = 1.45
STEEL = np.array([27.0, 29.0, 34.0])         # blued base
WEAR = np.array([118.0, 117.0, 112.0])       # steel showing through
CASE = (np.array([72.0, 70.0, 68.0]), np.array([48.0, 60.0, 92.0]), np.array([116.0, 96.0, 58.0]), np.array([78.0, 58.0, 80.0]))
AO_K = 0.75
SHEEN = 0.40                                 # baked top light on the steel (x the base)
WOOD_PX_CM = 10.0                            # retail Kar98 px per cm of this gun (its own sheet: ~8.5)


def noise(shape, sigma, seed, wrap=True):
    r = np.random.RandomState(seed).rand(*shape).astype(np.float32)
    g = ndi.gaussian_filter(r, sigma, mode='wrap' if wrap else 'reflect')
    g -= g.mean(); g /= (g.std() + 1e-9)
    return g


def field(seed, a, b, sa, sb, size=1024):
    """a smooth unit-variance noise field looked up at the per-texel plane coordinates (a, b) [cm]; sa / sb = feature
    size in cm along a / b. Wraps (mirror) outside its 1024 px tile."""
    px = 6.0                                           # tile px per feature sigma
    t = noise((size, size), px, seed)
    return ndi.map_coordinates(t, [b / sb * px, a / sa * px], order=1, mode='mirror')


def load():
    J = json.load(open(os.path.join(OWN, 'high_parts.json')))
    tri, pid, wood = [], [], []
    for i, p in enumerate(PARTS):
        a = np.array(J['parts'][p], np.float32)
        tri.append(a); pid += [i] * len(a); wood += J['wood'][p]
    return np.concatenate(tri), np.array(pid), np.array(wood, bool)


def raster(P2, n_tris, W, H, depth=None, eps=0.03):
    """P2: (T,3,2) pixel coords. -> tid (H,W) int32 (-1 = none), bw (H,W,3) barycentric weights. With depth (T,3):
    nearest wins (smaller = nearer)."""
    tid = -np.ones((H, W), np.int32); bw = np.zeros((H, W, 3), np.float32)
    zb = np.full((H, W), 1e30, np.float32) if depth is not None else None
    for ti in range(n_tris):
        a, b, c = P2[ti]
        x0 = max(0, int(math.floor(min(a[0], b[0], c[0])) - 1)); x1 = min(W, int(math.ceil(max(a[0], b[0], c[0])) + 2))
        y0 = max(0, int(math.floor(min(a[1], b[1], c[1])) - 1)); y1 = min(H, int(math.ceil(max(a[1], b[1], c[1])) + 2))
        if x1 <= x0 or y1 <= y0:
            continue
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
        w2 = 1 - w0 - w1
        m = (w0 >= -eps) & (w1 >= -eps) & (w2 >= -eps)
        if depth is not None:
            z = w0 * depth[ti, 0] + w1 * depth[ti, 1] + w2 * depth[ti, 2]
            m &= z < zb[y0:y1, x0:x1]
            zb[y0:y1, x0:x1][m] = z[m]
        if not m.any():
            continue
        tid[y0:y1, x0:x1][m] = ti
        bw[y0:y1, x0:x1][m] = np.stack([w0, w1, w2], -1)[m]
    return tid, bw


def interp(T, tid, bw, sl):
    out = np.zeros(tid.shape + (sl.stop - sl.start,), np.float32)
    t = np.maximum(tid, 0)
    for k in range(3):
        out += bw[..., k, None] * T[t, k, sl]
    return out


def curvature(pos, nrm, mask, pid_px, r_cm=0.22, step=2, k=40):
    """signed mean-curvature estimate per texel from the baked positions / normals (convex +, concave -), found in 3D
    so bevelled edges count (the high mesh has no hard edges: every edge is a bevel of small faces)."""
    out = np.zeros(mask.shape, np.float32)
    sub = np.zeros_like(mask); sub[::step, ::step] = True
    for p in range(len(PARTS)):
        m = mask & sub & (pid_px == p)
        if m.sum() < k + 1:
            continue
        P = pos[m] * CM; Nn = nrm[m]
        tr = cKDTree(P)
        d, j = tr.query(P, k=k, distance_upper_bound=r_cm)
        ok = np.isfinite(d) & (d > 1e-6)
        j = np.where(ok, j, 0)
        dp = P[j] - P[:, None, :]; dn = Nn[j] - Nn[:, None, :]
        same = (Nn[j] * Nn[:, None, :]).sum(2) > -0.2
        ok &= same
        num = ((dn * dp).sum(2) * ok).sum(1); den = ((dp * dp).sum(2) * ok).sum(1) + 1e-9
        c = num / den                                     # 1 / cm
        out[m] = c
    # spread the sub-sampled values over the full grid inside the islands
    val = out.copy(); w = (mask & sub).astype(np.float32)
    val = ndi.uniform_filter(val, 2 * step - 1) / np.maximum(ndi.uniform_filter(w, 2 * step - 1), 1e-6)
    val[~mask] = 0
    return val


def bake():
    T, pid, wood = load()
    tid, bw = raster(T[:, :, 6:8] * N, len(T), N, N)
    mask = tid >= 0
    pos = interp(T, tid, bw, slice(0, 3)); nrm = interp(T, tid, bw, slice(3, 6))
    nrm /= np.maximum(np.linalg.norm(nrm, axis=2, keepdims=True), 1e-6)
    pid_px = np.where(mask, pid[np.maximum(tid, 0)], -1).astype(np.int8)
    cur = curvature(pos, nrm, mask, pid_px)
    np.savez_compressed(os.path.join(L.BUILD, 'skin_bake.npz'), tid=tid, pos=pos.astype(np.float32), nrm=nrm.astype(np.float16), cur=cur)
    print('baked: covered %.1f %%, curvature p1 %.2f p50 %.2f p99 %.2f /cm' % (100 * mask.mean(), *np.percentile(cur[mask], [1, 50, 99])))


def wood_atlas():
    """the retail Kar98's butt-stock wood with its baked shading divided out -> (tile rgb about 1.0, mean colour)"""
    k = np.asarray(Image.open(os.path.join(SRCD, 'kar98_retail.png')).convert('RGB'), np.float32)
    assert k.shape[:2] == (512, 1024), k.shape
    r = k[96:204, 46:300]                            # clean butt wood, 254 x 108
    lum = r.mean(2)
    flat = lum / (ndi.gaussian_filter(lum, 14, mode='reflect') + 1e-3)
    chroma = r / (lum[..., None] + 1e-3)
    chroma = chroma / chroma.mean((0, 1))[None, None, :]
    return flat[..., None] * (1 + (chroma - 1) * 0.6)


def steel_tile(size=1024):
    """procedural worn-steel detail tile (about 1.0): brushing along u, sparse scratches, pits. 40 px per cm."""
    rs = np.random.RandomState(1912)
    brush = ndi.gaussian_filter(rs.rand(size, size).astype(np.float32), (0.6, 40), mode='wrap')
    brush = (brush - brush.mean()) / brush.std()
    from PIL import ImageDraw
    im = Image.new('L', (size, size), 0); d = ImageDraw.Draw(im)
    for _ in range(420):
        x0, y0 = rs.rand(2) * size
        ln = 12 + rs.rand() ** 2 * 190
        an = rs.normal(0, 0.16) + (math.pi / 2 if rs.rand() < 0.06 else 0)
        d.line([(x0, y0), (x0 + ln * math.cos(an), y0 + ln * math.sin(an))], fill=int(90 + rs.rand() * 165), width=1)
    scr = ndi.gaussian_filter(np.asarray(im, np.float32) / 255.0, 0.55)
    pit = ndi.gaussian_filter((rs.rand(size, size) > 0.9965).astype(np.float32), 0.8) * 5.0
    return np.clip(1.0 + 0.07 * brush + 0.50 * scr - 0.45 * np.clip(pit, 0, 1), 0.5, 2.0)


def sample(at, sy, sx):
    if at.ndim == 2:
        return ndi.map_coordinates(at, [sy, sx], order=1, mode='mirror')
    return np.stack([ndi.map_coordinates(at[..., c], [sy, sx], order=1, mode='mirror') for c in range(3)], -1)


def geometry(T, pid, wood):
    """numbers the painter keys on, from the mesh (cm, source frame)"""
    G = {}
    P = T[:, :, :3] * CM
    b = P[pid == 0].reshape(-1, 3)
    G['breech_x'], G['muzzle_x'] = float(b[:, 0].min()), float(b[:, 0].max())
    M = json.load(open(os.path.join(L.BUILD, 'model.json')))['A']
    G['bore_y'], G['bore_z'], G['r_bore'], G['r_out'] = (M[k] * CM for k in ('bore_y', 'bore_z', 'r_bore', 'r_out'))
    gw = P[(pid == 1) & wood].reshape(-1, 3)
    c = gw.mean(0)
    u, s, vt = np.linalg.svd((gw - c)[:, [0, 2]], full_matrices=False)
    ax = vt[0] if vt[0][0] > 0 else -vt[0]
    G['grip_c'] = c.tolist(); G['grip_ax'] = [float(ax[0]), 0.0, float(ax[1])]
    sg = (gw - c)[:, [0, 2]] @ ax
    G['grip_s'] = [float(sg.min()), float(sg.max())]
    tg = (gw - c)[:, [0, 2]] @ np.array([-ax[1], ax[0]])
    G['grip_t'] = [float(tg.min()), float(tg.max())]
    G['grip_y'] = float(np.abs(gw[:, 1]).max())
    fw = P[(pid == 0) & wood].reshape(-1, 3)
    G['fore_x'] = [float(fw[:, 0].min()), float(fw[:, 0].max())]
    G['fore_z'] = [float(fw[:, 2].min()), float(fw[:, 2].max())]
    G['fore_y'] = float(np.abs(fw[:, 1]).max())
    bs = P[(pid == 1) & ~wood].reshape(-1, 3)
    G['steel_body_x'] = [float(bs[:, 0].min()), float(bs[:, 0].max())]
    G['steel_body_z'] = [float(bs[:, 2].min()), float(bs[:, 2].max())]
    G['steel_body_y'] = float(np.abs(bs[:, 1]).max())
    return G


def paint(preview=False):
    T, pid, wood = load()
    G = geometry(T, pid, wood)
    Bk = np.load(os.path.join(L.BUILD, 'skin_bake.npz'))
    tid = Bk['tid']; mask = tid >= 0
    pos = Bk['pos'] * CM; nrm = Bk['nrm'].astype(np.float32); cur = Bk['cur']
    t0 = np.maximum(tid, 0)
    part = np.where(mask, pid[t0], -1); wd = mask & wood[t0]
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    nx, ny, nz = nrm[..., 0], nrm[..., 1], nrm[..., 2]
    up = np.clip(nz, 0, 1)
    ao = np.clip(np.load(os.path.join(OWN, 'bake_ao.npy'))[..., 0], 0, 1)
    ao = np.where(mask, ao, 1.0)

    # ------------------------------------------------------------------ steel
    tile = steel_tile()
    # the lookup plane: along the barrels, and around (a lean through y so top / sides / the two tubes differ)
    ry = np.abs(y) - G['bore_y']; rz = z - G['bore_z']
    rr = np.hypot(ry, rz)
    arc = np.arctan2(y - np.sign(y) * G['bore_y'], rz) * G['r_out'] + 11.0 * (y > 0)      # not mirrored tube to tube
    tube = (part == 0) & ~wd & (rr < G['r_out'] * 1.15)
    domz = np.abs(nz) >= np.abs(ny); domx = (np.abs(nx) > np.abs(ny)) & (np.abs(nx) > np.abs(nz))
    a_s = np.where(domx, y, x)
    b_s = np.where(tube, arc, np.where(domx, z, np.where(domz, y + 9.0 * np.sign(nz), z + 5.0 * np.sign(ny))))
    det = sample(tile, b_s * 40.0 + 9, a_s * 40.0 + 500)
    mott = 0.05 * field(11, x, z + 0.7 * y, 0.5, 0.5) + 0.06 * field(12, x, z + 0.7 * y, 2.5, 1.2)
    streak = 0.75 + 0.5 * (0.5 + 0.5 * field(13, x, y + 0.3 * z, 3.0, 0.08))
    shade = 0.84 + 0.18 * up + SHEEN * (up ** 8) * streak
    lum = det * (1 + mott) * shade
    blue = STEEL[None, None, :] * lum[..., None]
    conv = np.clip(cur, 0, None); conc = np.clip(-cur, 0, None)
    brk = np.clip(0.55 + 0.30 * field(14, x + y, z, 0.25, 0.25) + 0.30 * field(15, x, z + y, 1.4, 1.4), 0.1, 1.2)
    wear = np.clip((conv - 1.2) / 5.0, 0, 1) * brk * (0.6 + 0.4 * det)
    # where a hand or a holster rubs: the muzzle ends, the lever's thumb piece, the guard's bow, the triggers
    rub = np.zeros_like(x)
    rub += np.clip((x - (G['muzzle_x'] - 1.6)) / 1.6, 0, 1) * (part == 0) * 0.35
    rub += (part == 2) * 0.22 + ((part == 3) | (part == 4)) * 0.18
    recv = (part == 1) & ~wd & (x > RECV_X) & (z > RECV_Z)
    thin = ((part == 1) & ~wd & ~recv) | (part >= 3)          # guard bow, triggers, tang, grip cap: thin parts read
    rub += ((part == 1) & ~wd & ~recv) * 0.12                 # as all edge to the curvature estimate
    wear = np.where(thin, np.clip((conv - 4.0) / 9.0, 0, 1) * brk, wear)
    wear = np.clip(wear * (1 + 2.5 * rub) + rub * np.clip(0.35 + 0.5 * field(16, x, z + y, 0.6, 0.3), 0, 1) * 0.35, 0, 0.72)
    wear = np.minimum(wear, np.where(thin, 0.42, 0.72))
    steel = blue * (1 - wear[..., None]) + WEAR[None, None, :] * wear[..., None] * (0.72 + 0.28 * shade[..., None])
    dirt = np.clip((conc - 0.8) / 4.0, 0, 1)
    steel *= (1 - 0.5 * dirt)[..., None]

    # receiver: colour case-hardening on the body's steel above the guard (grey / blue / straw / plum mottle)
    f1 = field(21, x + 0.6 * z, z + 0.8 * y, 0.55, 0.45); f2 = field(22, x + 0.5 * y, z - 0.4 * x, 0.45, 0.55); f3 = field(23, x, z - 0.6 * y, 0.8, 0.6)
    w_b = np.clip(0.25 + 0.55 * f1, 0, 0.75); w_s = np.clip(0.50 * f2 - 0.25, 0, 0.55); w_p = np.clip(0.45 * f3 - 0.35, 0, 0.4)
    cc = CASE[0][None, None, :] * np.ones_like(x)[..., None]
    for wgt, col in ((w_b, CASE[1]), (w_s, CASE[2]), (w_p, CASE[3])):
        cc = cc * (1 - wgt[..., None]) + col[None, None, :] * wgt[..., None]
    cg = cc.mean(2, keepdims=True)
    cc = cg + (cc - cg) * CASE_SAT
    cc = cc * (0.60 * det * (0.86 + 0.18 * up + 0.30 * up ** 8))[..., None]
    cwear = np.clip((conv - 1.2) / 5.0, 0, 1) * brk * 0.6
    cc = cc * (1 - cwear[..., None]) + WEAR[None, None, :] * cwear[..., None]
    cc *= (1 - 0.5 * dirt)[..., None]
    col = np.where(recv[..., None], cc, steel)

    # engraved border line on the receiver's side flats: a cut (dark, with a lit lower lip) following the flat's outline
    flat = recv & (np.abs(ny) > 0.93)
    lab, nl = ndi.label(flat)
    if nl:
        area = ndi.sum(flat, lab, np.arange(1, nl + 1))
        big = np.isin(lab, 1 + np.nonzero(area > 9000)[0])
        d = ndi.distance_transform_edt(big)
        for d0, wdt, k in ((9.0, 2.2, 0.62), (15.0, 1.3, 0.45)):
            line = np.clip(1 - np.abs(d - d0) / wdt, 0, 1) * big
            lip = np.clip(1 - np.abs(d - d0 - wdt - 0.6) / 1.2, 0, 1) * big
            col = col * (1 - k * line)[..., None] + (lip * 14)[..., None]
        # a row of small punched dots between the two lines
        dots = np.clip(1 - np.abs(d - 12.0) / 1.2, 0, 1) * big * (np.sin(x * 26.0) * np.sin(z * 26.0) > 0.55)
        col *= (1 - 0.4 * dots)[..., None]
        print('engraved flats: %d of %d flat patches, %.1f %% of the sheet' % (int((area > 9000).sum()), nl, 100 * big.mean()))

    # barrels: bores, muzzle faces, breech faces
    brl = (part == 0) & ~wd
    inward = (ry * np.sign(y) * ny + rz * nz) < -0.3 * np.maximum(rr, 1e-3) / 1.0
    bore = brl & (rr < G['r_bore'] * 1.04) & (np.abs(nx) < 0.5) & inward
    depth = np.minimum(G['muzzle_x'] - x, x - G['breech_x'])
    bcol = 5.0 + 22.0 * np.exp(-depth / 0.9) * (0.6 + 0.4 * up)
    col = np.where(bore[..., None], bcol[..., None] * np.array([1.0, 0.98, 0.95])[None, None, :], col)
    muz = brl & (nx > 0.6) & (x > G['muzzle_x'] - 0.4)
    ring = np.clip((rr - G['r_bore']) / (G['r_out'] - G['r_bore'] + 1e-6), 0, 1.5)
    mcol = (86.0 + 40.0 * ring + 10 * field(31, y, z, 0.1, 0.1)) * (0.8 + 0.2 * np.cos(rr * 55.0) ** 2)
    col = np.where(muz[..., None], mcol[..., None] * np.array([1.0, 1.0, 0.98])[None, None, :], col)
    bre = brl & (nx < -0.6) & (x < G['breech_x'] + 0.6)
    fcol = (118.0 + 14 * field(32, y, z, 0.15, 0.15)) * (0.86 + 0.14 * np.cos(rr * 40.0) ** 2) * det
    col = np.where(bre[..., None], fcol[..., None] * np.array([1.0, 1.0, 1.02])[None, None, :], col)
    # the standing breech (body faces looking at the muzzle, behind the barrels) and the action flats: polished
    sbre = recv & (nx > 0.75) & (np.abs(x - G['breech_x']) < 0.8) & (z > G['bore_z'] - 2.2)
    pcol = (104.0 + 12 * field(33, y, z, 0.2, 0.2)) * det
    col = np.where(sbre[..., None], pcol[..., None] * np.array([1.0, 1.0, 1.02])[None, None, :], col)

    # ------------------------------------------------------------------ wood
    at = wood_atlas()
    lum_at = at.mean(2, keepdims=True)
    at = np.clip(lum_at ** WOOD_CONTRAST * (at / lum_at), 0.05, 3.0)
    wcol = np.zeros_like(col)
    gax = np.array(G['grip_ax']); gc = np.array(G['grip_c'])
    gperp = np.array([-gax[2], 0.0, gax[0]])
    rel = pos - gc[None, None, :]
    s_g = rel @ gax; t_g = rel @ gperp
    chk = np.zeros_like(x)
    for which, s_w, t_w, y_w, off in (('grip', s_g, t_g, y, (40.0, 30.0)), ('fore', x - G['fore_x'][0], z - G['fore_z'][0], y, (170.0, 260.0))):
        m = wd & ((part == 1) if which == 'grip' else (part == 0))
        if not m.any():
            continue
        warp = 0.10 * field(41, s_w, t_w + y_w, 1.2, 0.8) + 0.22 * field(42, s_w, t_w + y_w, 5.0, 2.5)
        across = t_w + 0.55 * y_w + warp                                  # leans through the blank
        w = sample(at, across * WOOD_PX_CM + off[0], s_w * WOOD_PX_CM + off[1])
        # pores: short dark dashes along the grain, a faint long streak, a slow figure
        pores = field(43, s_w, across, 0.16, 0.012)
        long_ = field(44, s_w, across, 2.2, 0.035)
        fig = field(45, s_w + 0.5 * across, across, 1.5, 0.5)
        k = 1 - 0.20 * np.clip(pores - 0.6, 0, 2) + 0.10 * long_ * 0.6 + 0.08 * fig
        w = WALNUT[None, None, :] * w * k[..., None]
        sheen = 0.84 + 0.14 * up + 0.30 * up ** 5
        w = w * sheen[..., None]
        wcol[m] = w[m]
    # checkering: grip sides and forend sides. Panels are regions in the part's own (s, t) plane; the cut lines
    # cross at +-30 deg to the grain, 0.19 cm apart.
    PIT = 0.19
    gs0, gs1 = G['grip_s']; gt0, gt1 = G['grip_t']
    u_g = (s_g - gs0) / (gs1 - gs0); v_g = (t_g - gt0) / (gt1 - gt0)
    pan_g = wd & (part == 1) & (np.abs(ny) > 0.45)
    eg = np.maximum(np.abs(u_g - GRIP_PANEL[0]) / GRIP_PANEL[2], np.abs(v_g - GRIP_PANEL[1]) / GRIP_PANEL[3])
    fx0, fx1 = G['fore_x']; fz0, fz1 = G['fore_z']
    u_f = (x - fx0) / (fx1 - fx0); v_f = (z - fz0) / (fz1 - fz0)
    pan_f = wd & (part == 0) & (np.abs(ny) > 0.45)
    ef = np.maximum(np.abs(u_f - FORE_PANEL[0]) / FORE_PANEL[2], np.abs(v_f - FORE_PANEL[1]) / FORE_PANEL[3])
    for pan, e, s_w, t_w in ((pan_g, eg, s_g, t_g), (pan_f, ef, x, z)):
        inside = pan & (e < 1.0)
        c30, s30 = math.cos(math.radians(30)), math.sin(math.radians(30))
        l1 = np.abs(((s_w * s30 + t_w * c30) / PIT) % 1.0 - 0.5) * 2          # 0 at the cut, 1 at the diamond's ridge
        l2 = np.abs(((-s_w * s30 + t_w * c30) / PIT) % 1.0 - 0.5) * 2
        dia = np.minimum(l1, l2)
        k = 0.62 + 0.55 * dia ** 0.8                                          # cuts dark, points a little light
        border = pan & (np.abs(e - 1.0) < 0.035)
        wcol = np.where(inside[..., None], wcol * (k * 0.90)[..., None], wcol)
        wcol = np.where(border[..., None], wcol * 0.55, wcol)
        chk += inside
    # handled wood: darker in the hand's place, lighter rubbed convex edges, dark creases and where wood meets steel
    wcur = np.clip((conv - 1.0) / 6.0, 0, 1) * np.clip(0.5 + 0.6 * field(46, x, z + y, 0.5, 0.5), 0, 1)
    wcol = wcol * (1 + 0.30 * wcur)[..., None]
    wcol *= (1 - 0.45 * np.clip((conc - 0.6) / 4.0, 0, 1))[..., None]
    grime = np.clip(0.5 + 0.5 * field(47, x, z + y, 0.8, 0.8), 0, 1)
    hold = np.exp(-((u_g - 0.45) / 0.35) ** 2) * (part == 1) * 0.16 + np.exp(-((u_f - 0.45) / 0.4) ** 2) * (part == 0) * 0.10
    wcol *= (1 - hold * grime)[..., None]
    col = np.where(wd[..., None], wcol, col)

    # ------------------------------------------------------------------ occlusion, padding, write
    col = col * (1 - AO_K * (1 - ao))[..., None]
    col = np.clip(col, 0, 255)
    dist, idx = ndi.distance_transform_edt(~mask, return_distances=True, return_indices=True)
    out = col[idx[0], idx[1]]
    out[dist > 24] = np.array([30.0, 30.0, 31.0])
    img = Image.fromarray(out.astype(np.uint8))
    img.save(os.path.join(L.BUILD, 'dbs_diffuse.png'))
    os.makedirs(TDIR, exist_ok=True)
    img.save(os.path.join(TDIR, NAME + '.jpg'), quality=93, subsampling=0)
    # the region masks of this sheet, for the finish set (tools/dbs_finish.py): what must stay readable on every finish
    np.savez_compressed(os.path.join(L.BUILD, 'skin_masks.npz'), mask=mask, wood=wd, recv=recv, bore=bore, muz=muz, bre=bre, sbre=sbre, chk=chk > 0,
                        part=part.astype(np.int8), dist=dist.astype(np.float16), idx=idx.astype(np.int16))
    for nm, m in (('wood', wd), ('blued', mask & ~wd & ~recv), ('receiver', recv)):
        print('%-9s mean rgb %s  %.1f %% of the sheet' % (nm, out[m].mean(0).round(1), 100 * m.mean()))
    print('checkered texels %.2f %%, bore %.2f %%, muzzle faces %.3f %%, breech faces %.3f %%, standing breech %.3f %%' % (
        100 * (chk > 0).mean(), 100 * bore.mean(), 100 * muz.mean(), 100 * bre.mean(), 100 * sbre.mean()))
    if os.environ.get('DBS_CMP'):
        o = np.asarray(Image.open(os.environ['DBS_CMP']).convert('RGB'), np.float32)
        for nm, m in (('wood', wd), ('blued', mask & ~wd & ~recv), ('receiver', recv)):
            print('   CMP %-9s mean rgb %s' % (nm, o[m].mean(0).round(1)))
    return out


# checkering panels: centre u, centre v, half-width u, half-width v in the part's normalised (s, t) box
RECV_X, RECV_Z = -12.6, -1.2        # cm: the receiver (case-coloured) is the body's steel ahead of / above this
CASE_SAT = 0.55
GRIP_PANEL = (0.47, 0.50, 0.30, 0.34)
FORE_PANEL = (0.50, 0.42, 0.36, 0.30)


def view(sheet=None, out=None, Wp=1500):
    """offline orthographic look at the textured mesh (no engine): left side, right side, top, bottom, breech end"""
    T, pid, wood = load()
    tex = np.asarray(Image.open(sheet or os.path.join(L.BUILD, 'dbs_diffuse.png')).convert('RGB'), np.float32)
    P = T[:, :, :3] * CM
    lo = P.reshape(-1, 3).min(0) - 0.5; hi = P.reshape(-1, 3).max(0) + 0.5
    sc = Wp / (hi[0] - lo[0])
    panels = []
    # (title, horizontal axis, sign, vertical axis, sign, depth axis, sign: viewer at +sign*inf)
    for title, ah, sh, av, sv, ad, sd in (('left side', 0, 1, 2, -1, 1, 1), ('right side', 0, -1, 2, -1, 1, -1),
                                          ('top', 0, 1, 1, 1, 2, 1), ('bottom', 0, 1, 1, -1, 2, -1)):
        W = int((hi[ah] - lo[ah]) * sc); H = int((hi[av] - lo[av]) * sc)
        hx = (P[:, :, ah] - lo[ah]) * sc if sh > 0 else (hi[ah] - P[:, :, ah]) * sc
        vy = (P[:, :, av] - lo[av]) * sc if sv > 0 else (hi[av] - P[:, :, av]) * sc
        tid, bw = raster(np.stack([hx, vy], -1), len(T), W, H, depth=-sd * P[:, :, ad], eps=0.001)
        uv = interp(T, tid, bw, slice(6, 8)); nr = interp(T, tid, bw, slice(3, 6))
        c = tex[np.clip((uv[..., 1] * N).astype(int), 0, N - 1), np.clip((uv[..., 0] * N).astype(int), 0, N - 1)]
        ld = np.array([0.25, 0.35 * sd if ad == 1 else 0.2, 0.9]); ld /= np.linalg.norm(ld)
        lit = 0.75 + 0.75 * np.clip(nr @ ld, 0, 1)
        im = np.where((tid >= 0)[..., None], np.clip(c * lit[..., None] * 1.6, 0, 255), 120.0)
        panels.append(Image.fromarray(im.astype(np.uint8)))
    Wm = max(p.size[0] for p in panels); Hm = sum(p.size[1] for p in panels)
    sh_ = Image.new('RGB', (Wm, Hm), (120, 120, 120)); yy = 0
    for p in panels:
        sh_.paste(p, (0, yy)); yy += p.size[1]
    out = out or os.path.join(L.BUILD, '_skin_view.jpg')
    sh_.save(out, quality=90)
    print('wrote', out, sh_.size)


def main():
    cmd = sys.argv[1]
    if cmd == 'bake':
        bake()
    elif cmd == 'info':
        T, pid, wood = load()
        print(json.dumps(geometry(T, pid, wood), indent=1))
    elif cmd == 'paint':
        paint()
    elif cmd == 'view':
        view(*(sys.argv[2:4]))


if __name__ == '__main__':
    main()
