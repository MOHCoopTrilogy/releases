r"""Stage the shotgun's SIGHTS (user 2026-10-12: "that shotgun needs some kind of sights, don't think vanilla really has
one"). Supersedes stage_bead.py (bug-3681: its bead was 6 px and dark, the receiver a blurred hump). The retail M1897
mesh (ONE skd for all 14 shotgun tiks) has no bead, no rear sight and a peaked receiver roof. Staged here:

  1. BEAD   own surface `coop_bead`: a brass ball on the barrel's top ridge at the sight point F (sights.json), a third
            of it sunk into the barrel (add_bead.py's sphere / surface writer, finer mesh). Own texture with the light
            painted in (a warm glint toward the shooter, a dark foot) and a shader that never goes black.
  2. GROOVE the receiver's roof ridge (stations -32.3 .. -22.8 u behind F) is opened into the M1897's matted sighting
            groove: the ridge vertices - the mesh already carries one copy per roof side - slide down their own roof
            edge to the two rails (position, UV: on the edge, the roof keeps its shape), and a NEW surface
            `coop_groove` (rails, chamfers, floor, the front end plate) closes the gap with its own crisp texture:
            bright worn rails that run to the bead, a dark cross-matted floor. Zero width at the rear station.
            No triangle of the old surface is re-indexed; at lower detail the new surface degenerates.
  3. shader + textures -> assets/scripts/coop_shotgun_sight.shader, assets/textures/coop_wpn/shotgun_{bead,groove}.tga
  4. every weapon tik of the mod tree that loads that skd gets the two `surface ... shader ...` lines
     (the mod tree is never written).

    cd heavy/assets; python ../tools/stage_sgsight.py [--r 0.27] [--lift 0.35] [--rail 0.20] [--floor 0.11] [--depth 0.10]
NOTE: patch_tik_h.py rebuilds a staged tik from the mod tree - a later reload set for the shotgun must keep the lines
(patch_tik_h reads KEEP_LINES from here).
"""
import sys, os, re, glob, struct, json, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
SJ = json.load(open(r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\sights.json'))['shotgun']
KEEP_LINES = ['surface coop_bead shader coop_shotgun_bead', 'surface coop_groove shader coop_shotgun_groove']
TAG = '// HZM coop [heavy lane] shotgun sights (stage_sgsight.py)'
# receiver roof stations, rear to front: (right ridge copy, its eave neighbour, left ridge copy, its eave neighbour, width 0..1)
STATIONS = [(225, None, 227, None, 0.0), (224, 220, 228, 226, 1.0), (166, 162, 169, 168, 1.0), (165, 161, 170, 167, 1.0),
            (187, 185, 189, 259, 1.0), (219, 218, 265, 264, 1.0)]
CAP_EAVE = 217          # the front face's left eave vertex (same place as 264): the end plate hangs on it

SHADER = """// HZM coop [heavy lane 2026-10-13] M1897 shotgun sights (tools/stage_sgsight.py): brass front bead + the receiver's
// matted sighting groove. rgbGen const takes three bare numbers - NO parentheses (bug-1913: "(" parses as 0).
// rgbGen lightingSpherical is what every model shader of the mod uses; lightingDiffuse draws BLACK on a model in this
// engine (bug-3681's dark bead, run hj3's black groove).
// The bead: an unlit floor so it never goes black in a dark room, the lit part on top, a glint from the shared
// finish sphere map (textures/coop_skins/env_sheen.tga, coop tex pak).
coop_shotgun_bead
{
	{
		map textures/coop_wpn/shotgun_bead.tga
		rgbGen const 0.28 0.28 0.28
	}
	{
		map textures/coop_wpn/shotgun_bead.tga
		blendFunc add
		rgbGen lightingSpherical
	}
	{
		map textures/coop_skins/env_sheen.tga
		blendFunc add
		tcGen environment
		rgbGen const 0.22 0.17 0.07
	}
}

coop_shotgun_groove
{
	{
		map textures/coop_wpn/shotgun_groove.tga
		rgbGen lightingSpherical
	}
}
"""


def write_tga(path, a):
    a = np.asarray(a, np.uint8)
    h, w = a.shape[:2]
    hd = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, w, h, 24, 0x20)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(hd + a[:, :, ::-1].tobytes())


def bead_tex(n=64):
    """planar UV from above: the pole (top of the ball) is the centre, the equator the rim; u < 0.5 = the half toward
    the shooter. Brass with the light painted in."""
    y, x = np.mgrid[0:n, 0:n]
    u = (x + 0.5) / n; v = (y + 0.5) / n
    r = np.hypot(u - 0.5, v - 0.5) / 0.5                        # 0 pole .. 1 equator
    rng = np.random.RandomState(7)
    base = np.array([206.0, 150.0, 60.0])                       # polished brass
    img = np.ones((n, n, 3)) * base
    img *= (1.0 - 0.42 * np.clip((r - 0.45) / 0.55, 0, 1) ** 1.5)[:, :, None]      # the foot darkens (sits in the barrel)
    img *= (0.95 + 0.10 * rng.rand(n, n))[:, :, None]
    g = np.exp(-(((u - 0.24) / 0.13) ** 2 + ((v - 0.5) / 0.17) ** 2))               # glint on the shooter's side, high
    img = img + g[:, :, None] * np.array([70.0, 80.0, 110.0])
    g2 = np.exp(-(((u - 0.5) / 0.10) ** 2 + ((v - 0.5) / 0.10) ** 2))               # the crown catches the sky
    img = img + g2[:, :, None] * np.array([28.0, 30.0, 34.0])
    return np.clip(img, 0, 255)


def groove_tex(w=64, h=64):
    """u across the groove: 0 / 1 = the rails (worn bright), 0.25 / 0.75 = the floor's edges; v along, 8 matting lines"""
    y, x = np.mgrid[0:h, 0:w]
    u = (x + 0.5) / w
    rng = np.random.RandomState(3)
    d = np.minimum(u, 1 - u)                                    # 0 at a rail .. 0.5 mid floor
    rail = np.clip(1 - d / 0.07, 0, 1)                          # the worn edge
    cham = np.clip(1 - np.abs(d - 0.16) / 0.10, 0, 1)
    line = 0.5 + 0.5 * np.cos(2 * np.pi * (y + 0.5) / h * 8)    # cross matting
    floor = 58 + 22 * line + 6 * rng.rand(h, w)
    val = floor * (1 - cham * 0.25)                             # chamfer in shade
    val = val * (1 - rail) + (170 + 20 * rng.rand(h, w)) * rail
    img = np.stack([val * 0.97, val * 0.99, val * 1.04], -1)   # cold blued steel
    return np.clip(img, 0, 255)


def vert_offsets(data, s):
    """byte offset of every vertex of surface s (skd: normal 3f, uv 2f, numWeights, numMorphs, morphs, weights)"""
    h = struct.unpack_from('<8i', data, s.raw_off + 68)
    o = s.raw_off + h[4]
    out = []
    for _ in range(h[1]):
        nw, nm = struct.unpack_from('<2i', data, o + 20)
        out.append((o, nw, nm))
        o += 28 + nm * 16 + nw * 20
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--r', type=float, default=0.27); ap.add_argument('--lift', type=float, default=0.35)
    ap.add_argument('--along', type=float, default=0.0)
    ap.add_argument('--rail', type=float, default=0.20); ap.add_argument('--floor', type=float, default=0.11)
    ap.add_argument('--depth', type=float, default=0.10); ap.add_argument('--vrep', type=float, default=1.0)
    ap.add_argument('--nogroove', action='store_true'); ap.add_argument('--out')
    a = ap.parse_args()
    _c = os.getcwd(); os.chdir(hv.BOLT)
    sys.path.insert(0, hv.BOLT)
    import add_bead as AB
    os.chdir(_c)
    G, SK, PR = AB.G, AB.SK, AB.PR
    tik = SJ['tik']
    t = G.parse_tik(tik); sc = t['scale']
    data = PR.vfs.read(G._res(t, t['skel'][0]))                 # the retail skd (run WITHOUT the overlay in IRONSIGHT_EXTRA_PAKS)
    m = SK.read_skd(data)
    assert [s.name for s in m.surfaces] == ['shotgun'], [s.name for s in m.surfaces]
    s0 = m.surfaces[0]
    skc = SK.read_skc(PR.vfs.read(G._res(t, t['anims']['idle'])))
    mats, _ = G.bone_world(m, skc, 0)
    F, Rr, up = (np.asarray(SJ[k], float) for k in ('F', 'R', 'up'))
    up /= np.linalg.norm(up)
    fwd = F - Rr; fwd -= (fwd @ up) * up; fwd /= np.linalg.norm(fwd)

    # ---- 2. groove: slide the ridge copies down their roof edge (bone-local, every vertex here is 1 weight on one bone)
    buf = bytearray(data)
    gverts, gtris = [], []
    if not a.nogroove:
        vo = vert_offsets(data, s0)

        def rd(i):
            o, nw, nm = vo[i]
            assert nw == 1 and nm == 0, (i, nw, nm)
            uv = np.array(struct.unpack_from('<2f', data, o + 12))
            b, w = struct.unpack_from('<if', data, o + 28)
            off = np.array(struct.unpack_from("<3f", data, o + 36)); assert np.allclose(uv, s0.verts[i][1], atol=1e-6), i
            return o, b, uv, off
        bone = rd(STATIONS[1][0])[1]
        M = np.asarray(mats[bone])

        def world(off):                                         # bone-local -> drawn model space
            return (np.asarray(off) @ M[0:3] + M[3]) * sc
        upl = (up @ M[0:3].T); upl /= np.linalg.norm(upl)       # 'up' in bone-local
        prof = []                                               # per station: Lrail, Lfloor, Rfloor, Rrail (bone-local), along
        for (rc, re_, lc, le, wd) in STATIONS:
            o_r, b_r, uv_r, p_r = rd(rc); o_l, b_l, uv_l, p_l = rd(lc)
            assert b_r == bone and b_l == bone and np.allclose(p_r, p_l, atol=1e-3), (rc, lc)
            if wd <= 0:
                prof.append([p_r, p_r, p_r, p_r]); continue
            row = {}
            for side, (ci, ei, o_c, uv_c, p_c) in (('R', (rc, re_, o_r, uv_r, p_r)), ('L', (lc, le, o_l, uv_l, p_l))):
                _, b_e, uv_e, p_e = rd(ei)
                assert b_e == bone
                span = np.linalg.norm((world(p_e) - world(p_c)) - ((world(p_e) - world(p_c)) @ fwd) * fwd)   # across, drawn u
                k = a.rail * wd / span; kf = a.floor * wd / span
                rail = p_c + k * (p_e - p_c); uvn = uv_c + k * (uv_e - uv_c)
                floor = p_c + kf * (p_e - p_c)
                floor = floor - upl * (((floor - rail) @ upl) + a.depth * wd / sc)       # depth below the rail, along up
                struct.pack_into('<2f', buf, o_c + 12, *uvn)
                struct.pack_into('<3f', buf, o_c + 36, *rail)
                row[side] = (rail, floor)
            prof.append([row['L'][0], row['L'][1], row['R'][1], row['R'][0]])
        along = [float((world(p[1]) - F) @ fwd) for p in prof]
        ucol = [0.0, 0.25, 0.75, 1.0]
        base = 0
        for i, p in enumerate(prof):
            for j in range(4):
                n = upl.copy()
                if j in (0, 3) and i > 0:                        # rails lean a little outward so the chamfer shades
                    out_dir = (p[j] - p[1 if j == 0 else 2]); out_dir -= (out_dir @ upl) * upl
                    if np.linalg.norm(out_dir) > 1e-6:
                        n = upl + 0.5 * out_dir / np.linalg.norm(out_dir); n /= np.linalg.norm(n)
                gverts.append((world(p[j]), n @ M[0:3], (ucol[j], -along[i] / a.vrep)))
        for i in range(len(prof) - 1):
            for j in range(3):
                q = [i * 4 + j, i * 4 + j + 1, (i + 1) * 4 + j, (i + 1) * 4 + j + 1]
                for tr in ((q[0], q[2], q[1]), (q[1], q[2], q[3])):
                    P3 = [np.asarray(gverts[k][0]) for k in tr]
                    if np.linalg.norm(np.cross(P3[1] - P3[0], P3[2] - P3[0])) > 1e-7:
                        gtris.append((tr, upl @ M[0:3]))
        # the front end plate: the receiver's front face between the rails (faces the muzzle)
        cap = world(rd(CAP_EAVE)[3]); last = prof[-1]
        b0 = len(gverts)
        for pt, uvx in ((cap, (0.5, 0.0)), (world(last[0]), (0.45, 0.0)), (world(last[3]), (0.55, 0.0))):
            gverts.append((pt, fwd, uvx))
        gtris.append(((b0, b0 + 1, b0 + 2), fwd))
        # wind like the retail meshes: cross(b - a, c - a) . outward normal < 0 (add_bead.sphere)
        tris = []
        for tr, n in gtris:
            pa, pb, pc = (np.asarray(gverts[k][0]) for k in tr)
            tris.append(tr if np.cross(pb - pa, pc - pa) @ n < 0 else (tr[0], tr[2], tr[1]))
        gtris = tris
        print('groove: %d stations %s u behind F, rails +-%.2f, floor +-%.2f, %.2f u deep; %d verts, %d tris'
              % (len(prof), ' '.join('%.1f' % x for x in along), a.rail, a.floor, a.depth, len(gverts), len(gtris)))
    data2 = bytes(buf)

    # ---- 1. bead (finer than add_bead's default sphere)
    g = G.load_gun(tik)
    best = None
    for gs, s in zip(g['surfs'], m.surfaces):
        d = np.linalg.norm(gs['P'] - F, axis=1); i = int(d.argmin())
        if best is None or d[i] < best[0]:
            best = (d[i], s.verts[i][2][0][0])
    c = F + a.along * fwd + a.lift * a.r * up
    bverts, btris = AB.sphere(c, a.r, up, fwd, seg=14, rings=8)
    out = AB.add_surface(data2, tik, 'coop_bead', bverts, btris, best[1])
    if gverts:
        out = AB.add_surface(out, tik, 'coop_groove', gverts, gtris, bone)
    chk = SK.read_skd(out)
    assert [s.name for s in chk.surfaces] == ['shotgun', 'coop_bead'] + (['coop_groove'] if gverts else [])
    assert chk.surfaces[0].tri_bytes == s0.tri_bytes and len(chk.surfaces[0].vert_bytes) == len(s0.vert_bytes)
    dst = a.out or hv.staged(SJ['skd'])
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(out)
    print('bead: r %.2f (%.0f %% proud), centre %s; skd %d -> %d bytes -> %s' % (a.r, 50 * (1 + a.lift), c.round(2), len(data), len(out), dst))
    if a.out:
        return
    # ---- 3. shader + textures (the superseded bead shader file goes)
    old = hv.staged('scripts/coop_shotgun_bead.shader')
    if os.path.isfile(old):
        os.remove(old)
    p = hv.staged('scripts/coop_shotgun_sight.shader'); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', newline='\n').write(SHADER)
    write_tga(hv.staged('textures/coop_wpn/shotgun_bead.tga'), bead_tex())
    write_tga(hv.staged('textures/coop_wpn/shotgun_groove.tga'), groove_tex())
    # ---- 4. tiks
    mesh_path, skd_name = os.path.dirname(SJ['skd']).lower(), os.path.basename(SJ['skd']).lower()
    n, other = 0, []
    for pth in sorted(glob.glob(os.path.join(MOD, 'models', 'weapons', 'shotgun*.tik'))):
        out_t = hv.staged('models/weapons/' + os.path.basename(pth))
        src = out_t if os.path.isfile(out_t) else pth          # a staged tik (reload rows) keeps its other edits
        tx = open(src, 'rb').read().decode('latin-1')
        mp = re.search(r'(?mi)^\s*path\s+(\S+)', tx); ms = re.search(r'(?mi)^\s*skelmodel\s+(\S+)', tx)
        if not mp or not ms or mp.group(1).lower().rstrip('/') != mesh_path or ms.group(1).lower() != skd_name:
            other.append(os.path.basename(pth)); continue
        tx = re.sub(r'(?m)^[ \t]*surface coop_(bead|groove)[^\r\n]*\r?\n', '', tx)
        nl = '\r\n' if '\r\n' in tx else '\n'
        last = [mm for mm in re.finditer(r'(?mi)^[ \t]*surface[^\r\n]*', tx[:tx.lower().index('init')])][-1]
        add = ''.join(nl + '\t' + ln + '\t' + TAG for ln in KEEP_LINES)
        tx = tx[:last.end()] + add + tx[last.end():]
        open(out_t, 'wb').write(tx.encode('latin-1'))
        n += 1
    print(n, 'tiks on', mesh_path + '/' + skd_name, '| NOT on this mesh:', '; '.join(other) or '-')


if __name__ == '__main__':
    main()
