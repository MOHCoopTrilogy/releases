#!/usr/bin/env python3
"""gen_m3l3_rock_clips.py - true-shape collision for the rocks baked into maps/M3L3.scr::coop_baked_0816.

WHY (bug-3210, user 2026-09-28: "the rocks I placed down early on the map interferes with allied ai pathing ... it
appears they get stuck in invisible walls. I do not want them to be fully pass through"):

  coop_baked_0816 solidifies every placed prop with `setsize getmins*scale getmaxs*scale`. For a rock that is wrong
  three ways at once (every number below was measured in-engine, docs/proposals/m3l3_rocks_2026-09-28/ingame):
    1. getmins/getmaxs are the idle ANIMATION bounds (skc frame bounds x 0.52 x scale): one crate around a dome. It
       turns with the rock - a script_model is a ScriptSlave, whose constructor sets EF_LINKANGLES
       (scriptslave.cpp:768), so Entity::setAngles feeds r.currentAngles to CM_TransformedBoxTrace - but its corners
       and flat top stand off the stone. Thin traces toward the rocks stopped on average 32u (p95 69u) before the
       visible stone, player-sized ones 25u (p95 56u); 22 of 485 stopped where there is no stone at all.
    2. The box is asymmetric about the origin, and client prediction decodes entityState.solid as a SYMMETRIC box
       (IntegerToBoundingBox keeps only maxs x/y), so every client predicted a different shape, up to ~28u off.
    3. Nothing told the ACTOR path graph: the rocks are spawned by script after the pathnodes load, and two were
       dropped onto pathnodes (a rock_large on node 65, a rock_medium beside node 54). Friendlies were routed into
       the boxes, hit them, re-pathed through the same pathway and stood there: in a headless A/B only 11 of 26
       allied-actor runs through the field arrived, 77% of their samples stuck.

WHAT THIS GENERATES (maps/m3l3/rockclips.scr, no hand edits):
  * the VISIBLE rock: its render mesh (rock_winter_<kind>.skd posed by its .skc), turned and scaled exactly as placed,
    as ground-anchored 2u columns. (--target hull fits the retail stoneclip hull, models/static/rock_<kind>.map, instead:
    at the x2.8 the mediums are placed at, that hull sits up to ~20u INSIDE the visible stone, so you would walk into
    the rock by most of a body width - it is reported, not used);
  * a small set of ground-anchored AXIS-ALIGNED boxes fitted to it (greedy pillars on a symmetric-difference
    objective + face refinement; stop at <= 8u horizontal error at body height, cap 12), each written as an invisible
    models/fx/dummy.tik script_model CENTRED on its own origin with a symmetric setsize, so client prediction and the
    server agree (x/y half extents are integers; mins z is exactly -16, the encodable floor);
  * `disconnect_paths` on every box - the retail recipe for a solid thing dropped onto the path graph
    (global/autotank.scr, global/autotruck.scr): it sweeps an actor hull (-15 -15 0)(15 15 94) along every pathway
    and cuts the ones the box blocks.
The rock script_models themselves become visual-only (bsol 2 in coop_baked_0816).

USAGE
    python gen_m3l3_rock_clips.py            # full fit (~8 min): rewrite maps/m3l3/rockclips.scr + rock_clips.json
    python gen_m3l3_rock_clips.py --reemit   # rewrite the .scr from rock_clips.json (seconds)
    python gen_m3l3_rock_clips.py --check    # exit 1 if a rock moved since the fit, or the .scr is stale
Re-run whenever a rock in coop_baked_0816 is moved, rotated or rescaled.
"""
import argparse, io, itertools, json, math, os, re, struct, sys, zipfile
import numpy as np
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if not os.path.isdir(os.path.join(ROOT, 'hzm-mohaa-coop-mod')):
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # promoted to docs/tools
MOD = os.path.join(ROOT, 'hzm-mohaa-coop-mod')
SCR = os.path.join(MOD, 'maps', 'M3L3.scr')
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
PAK0 = os.path.join(GOG, 'main', 'Pak0.pk3')
LOAD_SCALE = 0.52      # rock_*.tik `scale 0.52`
VOX = 2.0              # voxel size (units)
SINK = 16.0            # boxes start this far below the hull floor (terrain is not flat under a rock)
TOL = 8.0              # stop adding boxes once horizontal error at body height is within this
MAX_BOXES = 12
BUG = 'bug-3210'       # buglog id of this fix
CUT_INSET = 15         # path cut uses each box shrunk by the sweep hull's half width (Entity::DisconnectPaths
                       # sweeps (-15 -15 0)(15 15 94)), so it cuts the pathways whose CENTRE LINE crosses the
                       # stone. Cutting with the full box also cut every pathway that merely grazed it, which
                       # isolated nodes the rocks sit beside: an actor next to one picked it as his start node,
                       # got 'Path not found' and stood still (headless A/B, 5 routes).
BODY_HEIGHTS = (6, 20, 36, 52, 68)


# ------------------------------------------------------------------------------------------------ assets
def _pak():
    return zipfile.ZipFile(PAK0)


def map_brushes(kind, z=None):
    z = z or _pak()
    txt = z.read('models/static/rock_%s.map' % kind).decode('latin1')
    brushes = []
    for blk in re.findall(r'// brush \d+\s*\{(.*?)\}', txt, re.S):
        planes = []
        for line in blk.strip().splitlines():
            pts = re.findall(r'\(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)', line)
            if len(pts) >= 3:
                p1, p2, p3 = (np.array([float(c) for c in p]) for p in pts[:3])
                n = np.cross(p3 - p1, p2 - p1)
                n /= np.linalg.norm(n)
                planes.append((n, float(n @ p1)))
        if len(brush_verts(planes)) < 4:
            planes = [(-n, -d) for n, d in planes]
        brushes.append(planes)
    return brushes


def brush_verts(planes):
    vs = []
    for a, b, c in itertools.combinations(planes, 3):
        M = np.array([a[0], b[0], c[0]])
        if abs(np.linalg.det(M)) < 1e-6:
            continue
        x = np.linalg.solve(M, np.array([a[1], b[1], c[1]]))
        if all(p[0] @ x <= p[1] + 1e-3 for p in planes):
            vs.append(x)
    return np.array(vs)


def skc_bounds(kind, z=None):
    """frame-0 bounds of the idle anim = what TIKI_CalculateBounds/getmins report (before load scale)."""
    z = z or _pak()
    b = z.read('models/static/natural/rock_winter_%s.skc' % kind)
    nch, ofsnames, nfr = struct.unpack_from('<iii', b, 36)
    vals = struct.unpack_from('<6f', b, 48)
    names = [b[ofsnames + c * 32: ofsnames + c * 32 + 32].split(b'\0')[0].decode() for c in range(nch)]
    ofs = struct.unpack_from('<i', b, 48 + 44)[0]
    ch = {names[c]: struct.unpack_from('<4f', b, ofs + c * 16) for c in range(nch)}
    return np.array(vals[:3]), np.array(vals[3:]), ch


def mesh_tris(kind, z=None):
    """render mesh (posed by the skc root channel), model units after load scale."""
    z = z or _pak()
    b = z.read('models/static/natural/rock_winter_%s.skd' % kind)
    h = struct.unpack_from('<4sI64siiiii', b, 0)
    nsurf, ofss = h[3], h[6]
    _, _, ch = skc_bounds(kind, z)
    q = list(ch['Box01 rot']); q[3] = -q[3]      # the engine applies the conjugate (checked against skc bounds)
    qv, qw = np.array(q[:3]), q[3]
    verts, tris, o = [], [], ofss
    for s in range(nsurf):
        _, _, ntri, nv, _, ofst, ofsv, _, ofse, _ = struct.unpack_from('<4s64s8i', b, o)
        base = len(verts)
        tris += [tuple(base + i for i in struct.unpack_from('<3i', b, o + ofst + t * 12)) for t in range(ntri)]
        p = o + ofsv
        for v in range(nv):
            nw, nm = struct.unpack_from('<ii', b, p + 20)
            p += 28 + 16 * nm
            acc = np.zeros(3)
            for w in range(nw):
                _, bw, x, y, zz = struct.unpack_from('<if3f', b, p)
                acc += bw * np.array([x, y, zz]); p += 20
            acc = acc + 2.0 * np.cross(qv, np.cross(qv, acc) + qw * acc)
            verts.append(acc * LOAD_SCALE)
        o += ofse
    return np.array(verts), tris


# ------------------------------------------------------------------------------------------------ placements
def rocks_from_script(path=SCR):
    txt = open(path, 'rb').read().decode('latin1')
    blk = txt[txt.index('\ncoop_baked_0816:'):]
    blk = blk[:blk.index('\n}end')]
    rx = re.compile(r'local\.e = spawn script_model\s*\n\s*local\.e model "models/static/rock_(medium|large)\.tik"\s*\n'
                    r'\s*local\.e\.origin = \(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)\s*\n'
                    r'\s*local\.e\.angles = \(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)\s*\n'
                    r'(?:\s*local\.e scale ([\d.]+)\s*\n)?')
    out = []
    for m in rx.finditer(blk):
        out.append({'kind': m.group(1), 'origin': [float(m.group(i)) for i in (2, 3, 4)],
                    'angles': [float(m.group(i)) for i in (5, 6, 7)],
                    'scale': float(m.group(8)) if m.group(8) else 1.0})
    n_all = len(re.findall(r'models/static/rock_(?:medium|large)\.tik', blk))
    assert len(out) == n_all, 'parsed %d of %d rock placements - the block layout changed' % (len(out), n_all)
    return out


def rot_matrix(pitch, yaw, roll):
    """rows = forward, left, up (Q3 AnglesToAxis); world = origin + scale * (local @ M)."""
    p, y, r = np.radians([pitch, yaw, roll])
    sp, cp, sy, cy, sr, cr = np.sin(p), np.cos(p), np.sin(y), np.cos(y), np.sin(r), np.cos(r)
    fwd = np.array([cp * cy, cp * sy, -sp])
    right = np.array([-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp])
    up = np.array([cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp])
    return np.array([fwd, -right, up])


def world_planes(rock, z=None):
    A = rot_matrix(*rock['angles'])
    o = np.array(rock['origin'])
    out = []
    for planes in map_brushes(rock['kind'], z):
        out.append([(n @ A, rock['scale'] * d + float((n @ A) @ o)) for n, d in planes])
    return out


def old_box(rock, z=None):
    """The collision coop_baked_0816 gave each rock: `setsize getmins*scale getmaxs*scale` = the idle anim's frame
    bounds x load scale x placement scale, ASYMMETRIC about the origin. A script_model is a ScriptSlave, whose
    constructor sets EF_LINKANGLES (scriptslave.cpp:768), so on the server this box TURNS with the rock
    (Entity::setAngles copies angles to r.currentAngles; SV_ClipMoveToEntities -> CM_TransformedBoxTrace). Client
    prediction turns it too, but decodes it as a SYMMETRIC box (IntegerToBoundingBox keeps only maxs x/y)."""
    mn, mx, _ = skc_bounds(rock['kind'], z)
    s = LOAD_SCALE * rock['scale']
    return {'origin': list(rock['origin']), 'angles': list(rock['angles']), 'mins': (mn * s).tolist(),
            'maxs': (mx * s).tolist()}


def obb_corners(ob, mins=None, maxs=None):
    mn = np.array(ob['mins'] if mins is None else mins); mx = np.array(ob['maxs'] if maxs is None else maxs)
    A = rot_matrix(*ob['angles'])
    c = np.array([[x, y, zz] for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for zz in (mn[2], mx[2])])
    return np.array(ob['origin']) + c @ A


def obb_mask(ob, grid, mins=None, maxs=None):
    xs, ys, zs = grid
    mn = np.array(ob['mins'] if mins is None else mins); mx = np.array(ob['maxs'] if maxs is None else maxs)
    A = rot_matrix(*ob['angles'])
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    P = np.stack([X, Y, Z], -1) - np.array(ob['origin'])
    L = P @ A.T                      # world -> the box's own frame
    return np.all((L >= mn) & (L <= mx), axis=-1)


# ------------------------------------------------------------------------------------------------ voxels + fit
def voxelize(wplanes, pad=24.0, lo=None, hi=None):
    allv = np.vstack([brush_verts(p) for p in wplanes])
    lo = np.floor((allv.min(0) - pad) / VOX) * VOX if lo is None else lo
    hi = np.ceil((allv.max(0) + pad) / VOX) * VOX if hi is None else hi
    xs, ys, zs = (np.arange(lo[i], hi[i], VOX) + VOX / 2 for i in range(3))
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
    P = np.stack([X, Y, Z], -1)
    occ = np.zeros(X.shape, bool)
    for planes in wplanes:
        inside = np.ones(X.shape, bool)
        for n, d in planes:
            inside &= (P @ n) <= d + 1e-6
        occ |= inside
    return occ, (xs, ys, zs)


def mesh_world(rock, z=None):
    v, tris = mesh_tris(rock['kind'], z)
    return np.array(rock['origin']) + (v * rock['scale']) @ rot_matrix(*rock['angles']), tris


def mesh_occ(rock, grid, z=None):
    """The VISIBLE rock as ground-anchored columns: for every 2u cell under the render mesh, solid from the mesh's
    lowest point up to the highest triangle over that cell (a rock has no usable overhang)."""
    xs, ys, zs = grid
    w, tris = mesh_world(rock, z)
    top = np.full((len(xs), len(ys)), -1e9)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    for t in tris:
        a, b, c = w[list(t)]
        lo = np.minimum(np.minimum(a, b), c); hi = np.maximum(np.maximum(a, b), c)
        ix = np.where((xs >= lo[0]) & (xs <= hi[0]))[0]; iy = np.where((ys >= lo[1]) & (ys <= hi[1]))[0]
        if not ix.size or not iy.size:
            continue
        px, py = X[np.ix_(ix, iy)], Y[np.ix_(ix, iy)]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        l1 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / d
        l2 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / d
        l3 = 1 - l1 - l2
        inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        zz = l1 * a[2] + l2 * b[2] + l3 * c[2]
        sub = top[np.ix_(ix, iy)]
        top[np.ix_(ix, iy)] = np.where(inside, np.maximum(sub, zz), sub)
    zb = w[:, 2].min()
    return (zs[None, None, :] >= zb) & (zs[None, None, :] <= top[:, :, None])


def boxes_mask(boxes, grid):
    xs, ys, zs = grid
    m = np.zeros((len(xs), len(ys), len(zs)), bool)
    for mn, mx in boxes:
        m[np.ix_((xs >= mn[0]) & (xs <= mx[0]), (ys >= mn[1]) & (ys <= mx[1]), (zs >= mn[2]) & (zs <= mx[2]))] = True
    return m


def hmetrics(occ, bm, zfloor, grid):
    """HORIZONTAL error in body-height slices - what a walking player / actor hull meets.
    prot = how far a box sticks out past the rock (invisible wall); pen = how far the rock sticks out past the boxes."""
    xs, ys, zs = grid
    prot, pen, lprot, lpen = [], [], [0.0], [0.0]
    for h in BODY_HEIGHTS:
        iz = int(np.argmin(abs(zs - (zfloor + h))))
        o, b = occ[:, :, iz], bm[:, :, iz]
        if not o.any() and not b.any():
            continue
        dh = ndimage.distance_transform_edt(~o) * VOX if o.any() else np.full(o.shape, 999.0)
        db = ndimage.distance_transform_edt(~b) * VOX if b.any() else np.full(o.shape, 999.0)
        prot += dh[b & ~o].tolist(); pen += db[o & ~b].tolist()
        if h <= 36:   # the band a walking body / actor hull actually meets (below the rock's shoulder)
            lprot += dh[b & ~o].tolist(); lpen += db[o & ~b].tolist()
    prot, pen = np.array(prot or [0.0]), np.array(pen or [0.0])
    above = zs >= zfloor
    inter = (occ[:, :, above] & bm[:, :, above]).sum(); union = (occ[:, :, above] | bm[:, :, above]).sum()
    return {'low_out': float(max(lprot)), 'low_in': float(max(lpen)),
            'hprot_max': float(prot.max()), 'hpen_max': float(pen.max()), 'hprot_p95': float(np.percentile(prot, 95)),
            'hpen_p95': float(np.percentile(pen, 95)), 'iou': float(inter / max(union, 1)),
            'extra_vol': float((bm[:, :, above] & ~occ[:, :, above]).sum() * VOX ** 3),
            'hull_vol': float(occ[:, :, above].sum() * VOX ** 3)}


def fit_pillars(occ, grid, max_boxes=MAX_BOXES, tol=TOL, step=2):
    xs, ys, zs = grid
    st = np.zeros((5, 5, 1), bool); st[:, :, 0] = True
    O = ndimage.binary_closing(occ, structure=st) | occ   # seal the hairline seams between the three brushes
    izb = np.where(O.any(axis=(0, 1)))[0].min()
    z0 = zs[izb] - VOX / 2
    Ov = O[:, :, izb:]
    nx, ny, nz = Ov.shape
    lx, ly = np.arange(0, nx + 1, step), np.arange(0, ny + 1, step)
    valid = (np.arange(len(lx))[:, None] < np.arange(len(lx))[None, :])[:, :, None, None] & \
            (np.arange(len(ly))[:, None] < np.arange(len(ly))[None, :])[None, None, :, :]

    def umask(bl):
        m = np.zeros_like(Ov)
        for a, b, c, d, e in bl:
            m[a:b, c:d, :e] = True
        return m

    def to_world(bl):
        return [((xs[0] - VOX / 2 + a * VOX, ys[0] - VOX / 2 + c * VOX, z0 - SINK),
                 (xs[0] - VOX / 2 + b * VOX, ys[0] - VOX / 2 + d * VOX, z0 + e * VOX)) for a, b, c, d, e in bl]

    bl, covered, history = [], np.zeros_like(Ov), []
    for _ in range(max_boxes):
        V = np.where(covered, 0.0, np.where(Ov, 1.0, -1.0))
        P = np.zeros((nx + 1, ny + 1, nz + 1))
        P[1:, 1:, 1:] = V.cumsum(0).cumsum(1).cumsum(2)
        best = (0.0, None)
        for e in range(1, nz + 1):
            Q = P[:, :, e][lx][:, ly]
            S = Q[None, :, None, :] - Q[:, None, None, :] - Q[None, :, :, None] + Q[:, None, :, None]
            S = np.where(valid, S, -1e18)
            k = int(np.argmax(S))
            if S.flat[k] > best[0]:
                i0, i1, j0, j1 = np.unravel_index(k, S.shape)
                best = (float(S.flat[k]), [lx[i0], lx[i1], ly[j0], ly[j1], e])
        if best[1] is None:
            break
        bl.append(best[1])
        cur, improved = int((umask(bl) ^ Ov).sum()), True
        while improved:
            improved = False
            for bi in range(len(bl)):
                for f in range(5):
                    for dv in (-1, 1):
                        t = [list(x) for x in bl]
                        t[bi][f] += dv
                        a, b, c, d, e = t[bi]
                        if not (0 <= a < b <= nx and 0 <= c < d <= ny and 1 <= e <= nz):
                            continue
                        s = int((umask(t) ^ Ov).sum())
                        if s < cur:
                            cur, bl, improved = s, t, True
        covered = umask(bl)
        boxes = to_world(bl)
        m = hmetrics(occ, boxes_mask(boxes, grid), z0, grid)
        history.append((boxes, m))
        if m['hprot_max'] <= tol and m['hpen_max'] <= tol:
            break
    ok = [h for h in history if h[1]['hprot_max'] <= tol and h[1]['hpen_max'] <= tol]
    return (ok[0] if ok else min(history, key=lambda h: max(h[1]['hprot_max'], h[1]['hpen_max'])
                                 + 0.5 * max(h[1]['hprot_p95'], h[1]['hpen_p95']))), z0


def entity_form(box):
    """(origin, mins, maxs) with origin at the box centre, integer x/y half extents and mins z == -16, so the
    encoded entityState.solid (symmetric x/y, zd >= -16) reproduces the server box exactly."""
    (x0, y0, z0), (x1, y1, z1) = box
    X0, X1, Y0, Y1 = math.floor(x0), math.ceil(x1), math.floor(y0), math.ceil(y1)
    if (X1 - X0) % 2:
        X1 += 1
    if (Y1 - Y0) % 2:
        Y1 += 1
    Z0 = math.floor(z0)
    oz = Z0 + 16
    top = max(math.ceil(z1) - oz, 1)
    return (int((X0 + X1) // 2), int((Y0 + Y1) // 2), int(oz)), ((X1 - X0) // 2, (Y1 - Y0) // 2, -16), \
        ((X1 - X0) // 2, (Y1 - Y0) // 2, int(top))


# ------------------------------------------------------------------------------------------------ emit
HEADER = """// HZM coop [2026-09-28, %s] M3L3 ROCK CLIPS - collision shaped like the rocks you see.
// GENERATED by docs/tools/gen_m3l3_rock_clips.py from the rock placements in maps/M3L3.scr::coop_baked_0816 and
// the rocks' own model files. DO NOT HAND-EDIT - after moving, turning or rescaling a rock, re-run the generator.
//
// Why: coop_baked_0816 gave each rock `setsize getmins*scale getmaxs*scale` - its idle animation's bounds, one crate
// around a dome. The crate turns with the rock (a script_model sets EF_LINKANGLES), but its corners and flat top stood
// off the stone: in-engine traces stopped on average 32u (p95 69u) short of the visible rock - the invisible walls.
// Clients predicted it as a symmetric box, a different shape again. And two rocks sit on actor pathnodes, so
// friendlies were routed straight into them (headless A/B: 11 of 26 allied runs through the field arrived).
//
// Each rock is now a handful of invisible, ground-anchored models/fx/dummy.tik boxes fitted to the VISIBLE rock (its
// render mesh, posed, turned and scaled as placed): within ~12u of the stone from knee to chest height. Each box has
// angles 0 and is CENTRED on its own origin, so client prediction (which decodes a symmetric box) matches the server
// exactly. disconnect_paths (the retail recipe from global/autotank.scr / autotruck.scr) then cuts every actor pathway
// whose centre line crosses the stone: each box is shrunk by 15u, the half width of the actor hull the cut sweeps,
// for the cut, then set to its full size. A full-size cut also removed pathways that merely graze a rock and isolated
// the nodes beside it - an actor there picked such a node, got 'Path not found' and stood still. With this: 24 of 26
// runs arrived. The rock models stay, visual only (bsol 2).
//=========================================================================
"""


def emit(rocks, fits):
    L = [HEADER % BUG, 'spawn:{', '//=========================================================================',
         '\tlocal.n = 0']
    total = 0
    for i, (r, (boxes, m)) in enumerate(zip(rocks, fits)):
        L.append('\t//rock %d of %d: rock_%s ( %.3f %.3f %.3f ) yaw %g scale %g - %d boxes, knee-chest error out %.0fu '
                 'in %.0fu' % (i + 1, len(rocks), r['kind'], *r['origin'], r['angles'][1], r['scale'], len(boxes),
                               m['low_out'], m['low_in']))
        for b in boxes:
            o, mn, mx = entity_form(b)
            ix, iy = max(mx[0] - CUT_INSET, 1), max(mx[1] - CUT_INSET, 1)
            L += ['\tlocal.c = spawn script_model',
                  '\tlocal.c model "models/fx/dummy.tik"',
                  '\tlocal.c.origin = ( %d %d %d )' % o,
                  '\tlocal.c setsize ( %d %d %d ) ( %d %d %d )' % (-ix, -iy, mn[2], ix, iy, mx[2]),
                  '\tlocal.c solid',
                  '\tlocal.c disconnect_paths',
                  '\tlocal.c setsize ( %d %d %d ) ( %d %d %d )' % (-mn[0], -mn[1], mn[2], *mx),
                  '\tlevel.coop_rockClip[local.n] = local.c',
                  '\tlocal.n++']
            total += 1
    L += ['\tlevel.coop_rockClipN = local.n',
          '\tprintln( "^~^~^ ROCKCLIP m3l3 rocks=%d clips=" + local.n + " paths cut" )' % len(rocks),
          '}end', '']
    txt = '\n'.join(L).replace('( -0 ', '( 0 ').replace('\r\n', '\n').replace('\n', '\r\n')
    return txt.encode('ascii'), total


def fit_all(rocks, target):
    z = _pak()
    fits, rep = [], []
    for i, r in enumerate(rocks):
        wp = world_planes(r, z)
        mw, _ = mesh_world(r, z)
        lo = np.floor((np.minimum(mw.min(0), np.vstack([brush_verts(p) for p in wp]).min(0)) - 24) / VOX) * VOX
        hi = np.ceil((np.maximum(mw.max(0), np.vstack([brush_verts(p) for p in wp]).max(0)) + 24) / VOX) * VOX
        hocc, grid = voxelize(wp, lo=lo, hi=hi)
        occ = mesh_occ(r, grid, z) if target == 'mesh' else hocc
        (boxes, m), z0 = fit_pillars(occ, grid)
        ob = old_box(r, z)
        big = (lo - 100, hi + 100)
        hocc2, grid2 = voxelize(wp, lo=big[0], hi=big[1])
        occ2 = mesh_occ(r, grid2, z) if target == 'mesh' else hocc2
        mo = hmetrics(occ2, obb_mask(ob, grid2), z0, grid2)
        cmin = [-ob['maxs'][0], -ob['maxs'][1], ob['mins'][2]]      # what client prediction decoded
        moc = hmetrics(occ2, obb_mask(ob, grid2, mins=cmin), z0, grid2)
        mh = hmetrics(hocc, boxes_mask(boxes, grid), z0, grid)     # the same boxes judged against the retail hull
        mhull = hmetrics(occ, hocc, z0, grid)                       # how far the retail hull itself is off the mesh
        fits.append((boxes, m))
        rep.append({'rock': r, 'old_box': ob, 'old_corners': obb_corners(ob).tolist(),
                    'old_client_corners': obb_corners(ob, mins=cmin).tolist(), 'old': mo, 'old_client': moc,
                    'new': m, 'new_vs_hull': mh,
                    'hull_vs_mesh': mhull, 'target': target,
                    'boxes': [[list(b[0]), list(b[1])] for b in boxes],
                    'entities': [entity_form(b) for b in boxes],
                    'hull_verts': [brush_verts(p).tolist() for p in wp]})
        print('rock %2d %-6s yaw %5.0f s %.1f | %2d boxes | knee-chest (6-36u): OLD out %2.0fu in %2.0fu -> NEW out %2.0fu '
              'in %2.0fu | all heights: OLD out %3.0fu -> NEW out %2.0fu in %2.0fu | iou %.2f | retail hull vs mesh: in %.0fu' % (
                  i + 1, r['kind'], r['angles'][1], r['scale'], len(boxes), mo['low_out'], mo['low_in'], m['low_out'],
                  m['low_in'], mo['hprot_max'], m['hprot_max'], m['hpen_max'], m['iou'], mhull['hpen_max']))
    return fits, rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='cheap: exit 1 if the placements moved since the last fit, '
                                                         'or the .scr no longer matches rock_clips.json')
    ap.add_argument('--reemit', action='store_true', help='rewrite the .scr from rock_clips.json without refitting')
    ap.add_argument('--out', default=os.path.join(MOD, 'maps', 'm3l3', 'rockclips.scr'))
    ap.add_argument('--json', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rock_clips.json'))
    ap.add_argument('--scr', default=SCR)
    ap.add_argument('--target', choices=('mesh', 'hull'), default='mesh',
                    help='fit to the VISIBLE render mesh (default) or to the retail stoneclip hull')
    a = ap.parse_args()
    rocks = rocks_from_script(a.scr)
    if a.check or a.reemit:
        rep = json.load(open(a.json))
        if [x['rock'] for x in rep] != rocks:
            print('rock placements in %s differ from %s - run the generator (full fit)' % (a.scr, a.json))
            sys.exit(1)
        fits = [([tuple(map(tuple, b)) for b in x['boxes']], x['new']) for x in rep]
        data, total = emit(rocks, fits)
        if a.check:
            cur = open(a.out, 'rb').read() if os.path.exists(a.out) else b''
            print(os.path.basename(a.out), 'CURRENT' if cur == data else 'STALE', '(%d clips)' % total)
            sys.exit(0 if cur == data else 1)
    else:
        fits, rep = fit_all(rocks, a.target)
        data, total = emit(rocks, fits)
        json.dump(rep, open(a.json, 'w'), indent=1)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, 'wb').write(data)
    print('wrote', a.out, '(%d clips for %d rocks)' % (total, len(rocks)))


if __name__ == '__main__':
    main()
