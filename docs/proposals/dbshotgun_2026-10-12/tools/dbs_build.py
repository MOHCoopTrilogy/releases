"""Game mesh of the double-barrel shotgun: build/high_parts.json (bl_build.py) -> assets/models/weapons/coop_dbshotgun/*

    python tools/dbs_build.py            writes the .skd, the bind/idle .skc, the two texture sheets and the shader

Source frame (bl_build.py): hinge pin at the origin, +x muzzle, +y LEFT, +z up, Blender units (BU).
Game frame = the retail weapon-tag frame (shotgun.skd): +x muzzle, +y RIGHT, +z DOWN, skd units (the tik scales 0.52):
    p_raw = K * (x, -y, -z) + T                       (a half turn about the barrel axis: no mirroring)
K: 13.25 skd units (cm) per BU -> the gun is 60 cm long over all with 33 cm (13 in) barrels 2.8 cm across each.
T: puts the triggers where the pump gun's trigger is (x ~ +1 u scaled), the bores on the pump gun's bore line
   (z -4.3 u) and the gun's centre plane on the pump gun's (y -1.05 u) - so the retail shotgun hands land on it.

Bones (all POSROT, identity rotation in the bind pose):
    origin                       receiver, fences, stock, guard, pins, safety
    dbs_barrels  (origin)        barrels, lumps, forend wood, bead        pivot = the hinge pin
    tag_barrel   (dbs_barrels)   between the muzzles
    tag_eject    (origin)        over the breech
    dbs_lever    (origin)        top lever                                 pivot = its screw (front end), turns about z
    dbs_trig_f / dbs_trig_r (origin)   front / rear trigger                pivot = their top, turn about y
    dbs_shell_r / dbs_shell_l (dbs_barrels)  one shell each                origin = the centre of the shell's head, chambered
"""
import os, sys, json, math
import numpy as np
from PIL import Image, ImageDraw
import dbslib as L
import dbs_skx as X

K = 13.25
SCALE = 0.52
T = np.array([9.3, -1.05, -2.44]) / SCALE
NAME = 'coop_dbshotgun'
MDIR = os.path.join(L.ASSETS, 'models', 'weapons', NAME)
TDIR = os.path.join(L.ASSETS, 'textures', 'models', 'weapons', NAME)
SEG = 14                    # shell / bead roundness


def to_raw(p):
    p = np.asarray(p, float)
    return p * np.array([K, -K, -K]) + T


def nrm_raw(n):
    return np.asarray(n, float) * np.array([1.0, -1.0, -1.0])


def load_parts():
    P = json.load(open(os.path.join(L.BUILD, 'high_parts.json')))['parts']
    return {k: np.array(v, float) for k, v in P.items()}            # (T, 3, 8): xyz n uv


def anchors(P):
    """measured places on the source mesh (BU, source frame)"""
    b = P['barrels'].reshape(-1, 8)[:, :3]
    x0, x1 = b[:, 0].min(), b[:, 0].max()
    # bore axis: mean of the breech-ring points of the +y barrel (ring radii 0.084 .. 0.109 around it)
    # bore axis: least-squares circle through the INWARD-facing points of the +y tube a little ahead of the breech
    # (inward = the normal points at the axis guess), so lumps, rib and the other tube cannot pull it
    a = P['barrels'].reshape(-1, 8)
    seg = a[(a[:, 0] > x0 + 0.02) & (a[:, 0] < x0 + 1.2) & (a[:, 1] > 0.01)]
    cy, cz = (b[:, 1].max()) / 2, b[b[:, 0] < x0 + 0.3][:, 2].max() - b[:, 1].max() / 2
    for _ in range(4):
        d = np.stack([seg[:, 1] - cy, seg[:, 2] - cz], 1)
        r = np.linalg.norm(d, axis=1)
        inward = (np.einsum('ij,ij->i', d, seg[:, 4:6]) < -0.5 * r) & (r < 0.1)
        q = seg[inward]
        Amat = np.c_[2 * q[:, 1], 2 * q[:, 2], np.ones(len(q))]
        sol = np.linalg.lstsq(Amat, q[:, 1] ** 2 + q[:, 2] ** 2, rcond=None)[0]
        cy, cz = sol[0], sol[1]
        r_bore = math.sqrt(sol[2] + cy * cy + cz * cz)
    r_out = b[:, 1].max() - cy
    top = b[b[:, 0] > x1 - 0.05][:, 2].max()
    btop = b[(b[:, 0] < x0 + 0.05) & (np.abs(b[:, 1]) < 0.03)][:, 2].max()      # top of the breech end, centre line
    lv = P['lever'].reshape(-1, 8)[:, :3]
    tf = P['trig_f'].reshape(-1, 8)[:, :3]
    tr = P['trig_r'].reshape(-1, 8)[:, :3]
    return dict(breech_x=x0, muzzle_x=x1, bore_y=cy, bore_z=cz, r_out=r_out, r_bore=r_bore, muzzle_top=top, breech_top=btop,
                lever_pivot=np.array([lv[:, 0].max() - 0.035, 0.0, (lv[:, 2].min() + lv[:, 2].max()) / 2]),
                trig_f_pivot=np.array([tf[tf[:, 2] > tf[:, 2].max() - 0.02][:, 0].mean(), 0.0, tf[:, 2].max()]),
                trig_r_pivot=np.array([tr[tr[:, 2] > tr[:, 2].max() - 0.02][:, 0].mean(), 0.0, tr[:, 2].max()]))


# ---------------------------------------------------------------- the small second sheet: brass, shell hull, primer
PS = 256            # parts sheet size
# uv rectangles (u0, v0, u1, v1)
UV_BRASS = (0.02, 0.02, 0.48, 0.23)        # brass band (bead, shell head sides)
UV_HULL = (0.02, 0.27, 0.98, 0.73)         # red paper hull, u = around, v = along
UV_HEAD = (0.52, 0.02, 0.73, 0.23)         # shell head disc (brass, primer in the middle)
UV_CRIMP = (0.77, 0.02, 0.98, 0.23)        # the closed front of the shell


def parts_sheet():
    im = Image.new('RGB', (PS, PS), (150, 118, 52))
    px = np.asarray(im).astype(float).copy()
    yy, xx = np.mgrid[0:PS, 0:PS] / PS
    rng = np.random.default_rng(7)
    noise = rng.normal(0, 1, (PS, PS))

    def rect(r):
        return (xx >= r[0] - 0.02) & (xx < r[2] + 0.02) & (yy >= r[1] - 0.02) & (yy < r[3] + 0.02)
    # brass band: polished, a soft highlight stripe across v
    m = rect(UV_BRASS)
    t = (yy - UV_BRASS[1]) / (UV_BRASS[3] - UV_BRASS[1])
    sh = 0.78 + 0.5 * np.exp(-((t - 0.35) / 0.18) ** 2)
    px[m] = (np.array([176, 136, 58])[None] * sh[m][:, None] + noise[m][:, None] * 3)
    # hull: dull red waxed paper, faint lengthwise ribs, darker toward the brass
    m = rect(UV_HULL)
    u = (xx - UV_HULL[0]) / (UV_HULL[2] - UV_HULL[0])
    v = (yy - UV_HULL[1]) / (UV_HULL[3] - UV_HULL[1])
    rib = 0.94 + 0.06 * np.sin(u * 2 * np.pi * 28)
    lit = 0.8 + 0.3 * np.exp(-((u % 0.5 - 0.2) / 0.1) ** 2)
    px[m] = (np.array([142, 34, 28])[None] * (rib * lit * (0.85 + 0.15 * v))[m][:, None] + noise[m][:, None] * 4)
    # head disc: brass, a turned ring, nickel primer with a pit
    cu, cv = (UV_HEAD[0] + UV_HEAD[2]) / 2, (UV_HEAD[1] + UV_HEAD[3]) / 2
    rr = np.hypot(xx - cu, yy - cv) / ((UV_HEAD[2] - UV_HEAD[0]) / 2)
    m = rect(UV_HEAD)
    base = np.array([170, 132, 56])[None] * (0.9 + 0.12 * np.cos(rr * 20))[..., None]
    base = np.where((rr < 0.36)[..., None], np.array([186, 180, 164])[None] * (0.8 + 0.3 * rr[..., None]), base)
    base = np.where(((rr > 0.36) & (rr < 0.42))[..., None], np.array([70, 52, 22])[None], base)
    px[m] = base[m]
    # crimp: folded star, darker red
    cu, cv = (UV_CRIMP[0] + UV_CRIMP[2]) / 2, (UV_CRIMP[1] + UV_CRIMP[3]) / 2
    ang = np.arctan2(yy - cv, xx - cu)
    rr = np.hypot(xx - cu, yy - cv) / ((UV_CRIMP[2] - UV_CRIMP[0]) / 2)
    m = rect(UV_CRIMP)
    star = 0.72 + 0.28 * np.abs(np.sin(ang * 3)) * np.clip(rr * 1.5, 0, 1)
    px[m] = (np.array([128, 30, 26])[None] * star[..., None])[m]
    return Image.fromarray(np.clip(px, 0, 255).astype(np.uint8))


def _uvr(r, u, v):
    return (r[0] + (r[2] - r[0]) * u, r[1] + (r[3] - r[1]) * v)


def lathe(profile, axis_o, seg=SEG):
    """profile: [(x along, radius, uvrect, v)] rings along +x from axis_o; returns triangles of corners
    (pos3, normal3, uv2) in the SOURCE frame, counter-clockwise seen from outside"""
    tris = []
    o = np.asarray(axis_o, float)
    ring = lambda x, r, k: o + np.array([x, r * math.cos(2 * math.pi * k / seg), r * math.sin(2 * math.pi * k / seg)])
    for (xa, ra, rect, va), (xb, rb, _, vb) in zip(profile[:-1], profile[1:]):
        if rect is None:
            continue
        dx, dr = xb - xa, rb - ra
        for k in range(seg):
            c = []
            for (x, r, v, kk) in ((xa, ra, va, k), (xb, rb, vb, k), (xb, rb, vb, k + 1), (xa, ra, va, k + 1)):
                a = 2 * math.pi * kk / seg
                n = np.array([-dr, dx * math.cos(a), dx * math.sin(a)])
                n = n / (np.linalg.norm(n) or 1.0)
                c.append((ring(x, r, kk), n, _uvr(rect, kk / seg, v)))
            # outside = +radius: (a_k, a_k+1, b_k+1) is counter-clockwise from outside for +x right-handed
            tris.append([c[0], c[3], c[2]]); tris.append([c[0], c[2], c[1]])
    return tris


def disc(x, r, rect, axis_o, facing, seg=SEG):
    o = np.asarray(axis_o, float)
    n = np.array([float(facing), 0, 0])
    cu = _uvr(rect, 0.5, 0.5)
    tris = []
    for k in range(seg):
        a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        p0 = o + np.array([x, r * math.cos(a0), r * math.sin(a0)]); p1 = o + np.array([x, r * math.cos(a1), r * math.sin(a1)])
        u0 = _uvr(rect, 0.5 + 0.5 * math.cos(a0), 0.5 + 0.5 * math.sin(a0)); u1 = _uvr(rect, 0.5 + 0.5 * math.cos(a1), 0.5 + 0.5 * math.sin(a1))
        c = (o + np.array([x, 0, 0]), n, cu)
        tris.append([c, (p0, n, u0), (p1, n, u1)] if facing > 0 else [c, (p1, n, u1), (p0, n, u0)])
    return tris


def shell_tris(A, head):
    """one shell, head centre at `head` (source frame), pointing +x"""
    rb = A['r_bore']
    hr, rim, ln = rb * 0.91, rb * 1.11, 0.445                       # 5.9 cm shell, 2.1 cm hull
    t = []
    t += disc(0.0, rim, UV_HEAD, head, -1)
    t += lathe([(0.0, rim, UV_BRASS, 0.0), (0.012, rim, UV_BRASS, 0.15), (0.0125, hr, UV_BRASS, 0.2),
                (0.115, hr, None, 1.0)], head)
    t += lathe([(0.115, hr, UV_HULL, 0.0), (ln - 0.012, hr, UV_HULL, 0.96), (ln, hr * 0.9, None, 1.0)], head)
    t += disc(ln, hr * 0.9, UV_CRIMP, head, +1)
    return t


def bead_tris(A):
    """a brass bead on a short post between the muzzles, top just over the barrel tops"""
    r = 0.03                    # 4 mm bead: at r 0.022 it drew 8 px across at 1280 x 720 (run look3)
    cx, cz = A['muzzle_x'] - 0.06, A['muzzle_top'] + 0.016
    t = []
    n_lat = 6
    for i in range(n_lat):
        for k in range(SEG):
            c = []
            for (ii, kk) in ((i, k), (i + 1, k), (i + 1, k + 1), (i, k + 1)):
                th = math.pi * ii / n_lat; ph = 2 * math.pi * kk / SEG
                n = np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)])
                c.append((np.array([cx, 0, cz]) + r * n, n, _uvr(UV_BRASS, kk / SEG, 0.1 + 0.8 * ii / n_lat)))
            t.append([c[0], c[1], c[2]]); t.append([c[0], c[2], c[3]])
    # post: from between the barrels up into the bead
    post = [(0.0, 0.011, UV_BRASS, 0.9), (cz - A['bore_z'], 0.011, None, 0.6)]
    for (p, n, uv) in [c for tri in lathe(post, (0, 0, 0), 8) for c in tri]:
        pass
    pt = []
    for tri in lathe(post, (0, 0, 0), 8):
        # lathe runs along +x: turn it to run along +z (x->z, y->x, z->y), then place
        q = [(np.array([cx + p[1], p[2], A['bore_z'] + p[0]]), np.array([n[1], n[2], n[0]]), uv) for (p, n, uv) in tri]
        pt.append(q)
    return t + pt


def build():
    P = load_parts()
    A = anchors(P)
    bones = [('origin', 'worldbone'), ('dbs_barrels', 'origin'), ('tag_barrel', 'dbs_barrels'), ('tag_eject', 'origin'),
             ('dbs_lever', 'origin'), ('dbs_trig_f', 'origin'), ('dbs_trig_r', 'origin'),
             ('dbs_shell_r', 'dbs_barrels'), ('dbs_shell_l', 'dbs_barrels')]
    bi = {n: i for i, (n, _) in enumerate(bones)}
    # bind positions, source frame (world); +y is LEFT in the source frame, so the RIGHT barrel is -y
    head_x = A['breech_x'] + 0.004
    W = {'origin': np.zeros(3), 'dbs_barrels': np.zeros(3),
         'tag_barrel': np.array([A['muzzle_x'], 0.0, A['bore_z']]),
         'tag_eject': np.array([A['breech_x'], 0.0, A['bore_z'] + 0.12]),
         'dbs_lever': A['lever_pivot'], 'dbs_trig_f': A['trig_f_pivot'], 'dbs_trig_r': A['trig_r_pivot'],
         'dbs_shell_r': np.array([head_x, -A['bore_y'], A['bore_z']]),
         'dbs_shell_l': np.array([head_x, A['bore_y'], A['bore_z']])}
    Wraw = {k: (to_raw(v) if k != 'origin' else np.zeros(3)) for k, v in W.items()}
    part_bone = {'body': 'origin', 'barrels': 'dbs_barrels', 'lever': 'dbs_lever', 'trig_f': 'dbs_trig_f', 'trig_r': 'dbs_trig_r'}

    def corners(tris, bone):
        out = []
        for tri in tris:
            c = []
            for (p, n, uv) in tri:
                c.append((bi[bone], to_raw(p) - Wraw[bone], nrm_raw(n), np.asarray(uv, float)))
            a, b, cc = c[0][1], c[1][1], c[2][1]
            fn = np.cross(b - a, cc - a)
            if np.dot(fn, c[0][2] + c[1][2] + c[2][2]) > 0:          # retail winding: cross . n < 0
                c = [c[0], c[2], c[1]]
            out.append(c)
        return out

    main = []
    for part in ('barrels', 'body', 'lever', 'trig_f', 'trig_r'):
        tris = [[(c[:3], c[3:6], c[6:8]) for c in tri] for tri in P[part]]
        cs = corners(tris, part_bone[part])
        # Blender's triangle order is scattered over the mesh: slabs along the gun, so a surface's triangles share
        # their vertices (unsorted: 20,175 vertices in 23 surfaces for 9,200 real ones)
        cs.sort(key=lambda c: (c[0][1][0] + c[1][1][0] + c[2][1][0]))
        main += cs
    small = corners(bead_tris(A), 'dbs_barrels')
    small += corners(shell_tris(A, W['dbs_shell_r']), 'dbs_shell_r')
    small += corners(shell_tris(A, W['dbs_shell_l']), 'dbs_shell_l')
    surfs = X.split_surfaces('dbs', main) + X.split_surfaces('dbsx', small)
    return dict(bones=bones, W=W, Wraw=Wraw, A=A, surfs=surfs, bi=bi)


def bind_frame(M, over=None):
    """channel names + one frame of values: every bone at its bind place (local = world - parent's), identity rotation;
    over: {bone: (pos_raw_local or None, quat or None)}"""
    over = over or {}
    par = dict(M['bones'])
    ch, vals = [], []
    for n, p in M['bones']:
        loc = M['Wraw'][n] - (M['Wraw'][p] if p in M['Wraw'] else 0)
        pos, q = over.get(n, (None, None))
        ch += [n + ' pos', n + ' rot']
        vals += [(*(loc if pos is None else pos), 0.0), (0.0, 0.0, 0.0, 1.0) if q is None else tuple(q)]
    return ch, vals


def bounds(M):
    pts = []
    for (_, _, verts) in M['surfs']:
        for (n, uv, b, off) in verts:
            pts.append(np.asarray(off) + M['Wraw'][M['bones'][b][0]])
    pts = np.array(pts)
    return pts.min(0), pts.max(0), float(np.linalg.norm(pts, axis=1).max())


SHADER = """// HZM coop: double-barrel shotgun (model: "Double Barrel Shotgun" by Jean PFP, CC0, opengameart.org)
// NEW names, defined in this one file only (TRAPS T6)
coop_dbshotgun
{
	qer_editorimage textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun.jpg
		rgbGen lightingSpherical
	}
}

coop_dbshotgun_parts
{
	qer_editorimage textures/models/weapons/coop_dbshotgun/coop_dbshotgun_parts.jpg
	{
		map textures/models/weapons/coop_dbshotgun/coop_dbshotgun_parts.jpg
		rgbGen lightingSpherical
	}
}
"""


def main():
    M = build()
    os.makedirs(MDIR, exist_ok=True); os.makedirs(TDIR, exist_ok=True)
    os.makedirs(os.path.join(L.ASSETS, 'scripts'), exist_ok=True)
    skd = X.build_skd(NAME, M['bones'], M['surfs'])
    open(os.path.join(MDIR, NAME + '.skd'), 'wb').write(skd)
    ch, vals = bind_frame(M)
    bmin, bmax, rad = bounds(M)
    open(os.path.join(MDIR, 'coop_dbs_idle.skc'), 'wb').write(X.build_skc(ch, [vals], 0.25, bmin, bmax, rad))
    Image.open(os.path.join(L.BUILD, 'dbs_diffuse.png')).convert('RGB').save(os.path.join(TDIR, NAME + '.jpg'), quality=93, subsampling=0)
    parts_sheet().save(os.path.join(TDIR, NAME + '_parts.jpg'), quality=93, subsampling=0)
    open(os.path.join(L.ASSETS, 'scripts', NAME + '.shader'), 'w', newline='\n').write(SHADER)
    nt = sum(len(s[1]) for s in M['surfs']); nv = sum(len(s[2]) for s in M['surfs'])
    print('skd %d bytes, %d bones, %d surfaces, %d verts, %d tris' % (len(skd), len(M['bones']), len(M['surfs']), nv, nt))
    for s in M['surfs']:
        print('   ', s[0], len(s[2]), 'verts', len(s[1]), 'tris')
    print('anchors (BU):', {k: (np.round(v, 3).tolist() if hasattr(v, '__len__') else round(float(v), 4)) for k, v in M['A'].items()})
    sc = lambda p: np.round(np.asarray(p) * SCALE, 2).tolist()
    print('scaled game frame: bounds', sc(bmin), sc(bmax))
    for k, v in M['Wraw'].items():
        print('    bone %-12s at %s' % (k, sc(v)))
    json.dump({'surfaces': [s[0] for s in M['surfs']], 'bones': M['bones'],
               'Wraw': {k: v.tolist() for k, v in M['Wraw'].items()}, 'A': {k: (v.tolist() if hasattr(v, 'tolist') else float(v)) for k, v in M['A'].items()},
               # sight points, scaled game units (weapon model space as cg_adssights.h wants it)
               'sight': {'F': (to_raw([M['A']['muzzle_x'] - 0.06, 0, M['A']['muzzle_top'] + 0.016]) * SCALE).tolist(),
                         'R': (to_raw([M['A']['breech_x'] + 0.01, 0, M['A']['breech_top']]) * SCALE).tolist()},
               'bmin': bmin.tolist(), 'bmax': bmax.tolist(), 'radius': rad}, open(os.path.join(L.BUILD, 'model.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
