#!/usr/bin/env python3
"""European Assault PROP models (converter 0.7.33): the original's own visible models for the stock stand-ins on the
BYO missions - the Panzer IV (intact and destroyed) so far. Our own code, stdlib only; runs on the PLAYER's PC inside
the converter and its output (mesh, textures) goes only into the player's own converted pak. Nothing disc-derived is
shipped. Only the VISIBLE model is swapped: the stock gameplay entity (VehicleTank, its VehicleTurretGun, collision,
sounds, speeds) stays, read from the stock .tik in the player's install and re-pointed at the converted mesh.

Reverse-engineered 2026-11-15 on the user's own Xbox USA disc (1_11, level_a.str):
  - '__Model:::Panzer_IV_geo.mesh' is a rigged model ELF like the character bodies (eachar.read_model), in a chunk of
    type 0xe9548fd5; 12 sub-meshes. The tank's own skeleton is not in the stream (the one skeleton chunk is the human
    rig); its bones are known by the vertices they carry (bone 0 hull, 18 turret, 19 gun mantlet, 20 barrel, 1-8,
    13-17, 25-32, 37-41 wheels / tracks). The intact tank is sub-meshes 0-7 + 11, the DESTROYED one 0-3 + 8 (blown
    skirts), 9 (bent barrel), 10 (hull with the turret knocked askew, unweighted) - the same model, parts swapped.
  - its textures: the definition chunk that names the model chunk (id, type) lists (id, type) pairs of its SHPX texture
    chunks a few words around that reference (type 0x49ac1b7a on the Panzer). 006_ is the faded Balkenkreuz decal
    (black, alpha <= 0.35, blended).
Fitting: disc metres -> map units at the level's own scale (48 u/m, the world conversion's), MOHAA axes (x fwd = disc
+y, y left = disc -x). The hull is moved so the disc turret ring's centre lands on the stock 'turret0' tag (the turret
is its own entity, attached there, and turns about it); the turret and gun go into the cannon model with the gun on
the 'main_gun' bone (pitch controller) and the cannon's own SKAN (written here) puts 'pitch' at the disc trunnion and
'tag_barrel' (shell + muzzle flash) at the disc muzzle. The stock bone frames below were measured in the engine
(script gettagposition / gettagangles on the stock tiks, 2026-11-15), world units at the tik's scale.
"""
import math
import os
import re
import struct
import zipfile
import glob

import eachar
import easkin

VERSION = "0.7.33"
WORLD_SCALE = 48.0          # map units per disc metre (flconvert.convert default; the EA world)

# the props whose own models have passed the user's sheets; the map script uses one only when it is listed here
OWN = {"panzer"}   # 2026-11-15 user approved the converted winter Panzer ("I like the snow panzer", sheets SHEET_ea_panzer_ingame_near_v8 / v8b)

# stock bone frames, idle frame (and the cannon's 'open'), measured in game: name -> (world pos, (pitch, yaw, roll))
STOCK = {
    "vehicles/PanzerIV_w_base.tik": {"scale": 0.54, "bones": {
        "tank": ((0.0, 0.0, 0.0), (0.0, 90.0, 90.0)),
        "turret0": ((-4.21, 0.0, 103.92), (0.0, 0.0, 0.0)),
        "turret1": ((109.19, -35.41, 86.22), (0.0, 0.0, 0.0))}},
    "vehicles/PanzerIV_w_cannon.tik": {"scale": 0.54, "bones": {
        "connect": ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        "panzer_IV_turret": ((0.0, 0.0, 0.0), (0.0, 90.0, 90.0)),
        "pitch": ((42.01, 0.86, 18.35), (0.0, 0.0, 0.0)),
        "main_gun": ((42.01, 0.86, 18.35), (0.0, 90.0, 90.0)),
        "tag_barrel": ((202.81, 0.90, 18.35), (0.0, 0.0, 0.0)),
        "controller_hatch": ((-47.98, -0.42, 50.70), (0.0, 0.0, 90.0)),
        "hatch": ((-47.98, -0.42, 50.70), (0.0, 90.0, 90.0)),
        "eyebone": ((6.30, 0.0, 58.13), (0.0, 0.0, 90.0)),
        "client_view": ((6.30, 0.0, 58.13), (0.0, -90.0, 90.0)),
        "tag_start": ((-48.59, 0.0, -6.65), (0.0, 0.0, 0.0))},
        "open": {"controller_hatch": ((-47.98, -0.42, 50.70), (-44.25, 0.0, 90.0)),
                 "hatch": ((-47.98, -0.42, 50.70), (0.0, 90.0, 45.75)),
                 "tag_start": ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))}},
    "vehicles/PanzerIV_w_mg42.tik": {"scale": 0.52, "bones": {
        "connect": ((0.0, 0.0, 0.0), (0.0, 0.0, 90.0)),
        "panzer_IV_mg42": ((0.0, 0.0, 0.0), (0.0, 90.0, 90.0)),
        "tag_barrel": ((25.05, 0.0, 0.0), (0.0, 0.0, 0.0)),
        "eyebone": ((-1.47, 0.0, 15.28), (0.0, 0.0, 90.0)),
        "Camera01": ((-1.47, 0.0, 15.28), (0.0, -90.0, 90.0)),
        "pitch": ((0.0, 0.0, 0.0), (0.0, 0.0, 90.0))}},
    "statweapons/mg42_gun.tik": {"scale": 0.52, "bones": {
        "origin": ((0.0, 0.0, 0.0), (0.0, -0.32, -1.46)),
        "tag_barrel": ((9.99, -0.22, 1.72), (4.00, -0.37, 0.03)),
        "MG42": ((-0.25, -0.15, 0.38), (14.50, -0.37, 90.04)),
        "tag_eject": ((-31.21, -1.68, 3.42), (-5.46, -90.18, -89.00))},
        # the stock gunner's hands (eaanimconv: MG42_stand_idle_a FK at the stock seat): 39.7 behind, 8.6 right of
        # and 3.1 below the pivot. The fire animation is 0.25 s and moves no tag (measured)
        "grip": (-39.7, -8.6, -3.1), "fire_len": 0.25},
    "vehicles/PanzerIV_w_d_base.tik": {"scale": 0.52, "bones": {
        "panzeriv_base_d": ((0.0, 0.0, 0.0), (0.0, 90.0, 0.0)),
        "turret0": ((0.0, 0.0, 103.27), (0.0, 0.0, 0.0))}},
}

PANZER = {
    "model": "Panzer_IV_geo", "chunk": 0xe9548fd5,
    "intact": (0, 1, 2, 3, 4, 5, 6, 7, 11), "wreck": (0, 1, 2, 3, 8, 9, 10),
    "turret_bones": (18, 19, 20), "gun_bones": (19, 20),
    # the hull's ball MG (sub-mesh 5, bone 0): the front face of its mount, disc metres; the stock hull-MG turret fires
    # from here (its tag_barrel is moved; the turret entity itself stays on the stock 'turret1' tag)
    "ball_mg": (0.582, 2.127, 1.453),
    # [QA 2026-11-15] at the converted SOLDIERS' scale (eachar: 52 u/m), not the world's 48: the original's tank-to-soldier
    # proportion (coordinator). The stock entity's own box (setsize 120 x 120 x 78) is smaller than either model and stays
    "scale": 52.0,
    # whitewash brightness: the original draws the tank near the snow's own brightness (emulator still
    # ref_xemu/atmo/medium_firec: tank / snow 0.77; ours under the stock tank's lightingSpherical: 0.42). A second
    # additive pass of the same texture at this weight lifts it (x1.8)
    "lift": 0.8,
}


MG42 = {
    # the mounted gun the original's crews man: a rigged model (chunk type 0x9f300526, 3 sub-meshes: gun body P051,
    # stock / grip P052, ammo belt P051 on its own chain of bones; 512 px textures), level, origin at the receiver.
    # The static mount: the smart object MG42Tripod (a 0.39 m pintle pole with a fork, its own mesh chunk)
    "model": "mmg_mg42_gun_geo", "chunk": 0x9f300526, "pole": "MG42Tripod_Art_0",
    "grip": (0.045, -0.169, -0.035),       # the pistol grip's centre (disc metres)
    "muzzle": (0.0, 0.64, 0.0), "eject": (0.0, 0.02, -0.036),
    # a hand-held gun: the CHARACTERS' scale (eachar: 0.52 x cm = 52 u/m), so the disc crews' hands fit it
    "scale": 52.0,
    # 'grip': on the stock seat (any engine); 'pole': the original's pintle mount, needs the seat moved in
    "variants": ("grip", "pole"),
    # the stock gunner's hands sit 22.7 ahead of and 68.7 over his seat (eaanimconv): seat back / down that put them
    # on the disc grip (52 u/m: 8.8 behind, 1.8 under the pole pivot)
    # (character agent 2026-11-15: centre-cell hands 23.0 ahead / 68.9 up -> 23.0 + 8.8, 68.9 + 1.8)
    "pole_seat": (31.8, 70.7),
}


# ---------------- small math ----------------
def axes(ang):
    """MOHAA AnglesToAxis: rows forward, left, up (pitch, yaw, roll in degrees)"""
    p, y, r = (math.radians(a) for a in ang)
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(r), math.cos(r)
    fwd = (cp * cy, cp * sy, -sp)
    right = (-sr * sp * cy + cr * sy, -sr * sp * sy - cr * cy, -sr * cp)
    up = (cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp)
    return [list(fwd), [-v for v in right], list(up)]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    n = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def to_map(p, s=WORLD_SCALE):
    return (p[1] * s, -p[0] * s, p[2] * s)


def to_map_n(n):
    return (n[1], -n[0], n[2])


# ---------------- disc reading ----------------
def read(stream, name, chunk_type):
    """eachar.read_model + easkin.skin_data for a prop model whose chunk type is not the characters'; textures from
    the definition chunk's (id, type) list"""
    old = eachar.CHUNK_MODEL
    eachar.CHUNK_MODEL = chunk_type
    try:
        m = eachar.read_model(stream, name)
        sd = easkin.skin_data(stream, name) if m else None
    finally:
        eachar.CHUNK_MODEL = old
    if not m:
        return None
    m["skin"] = sd
    if not m["textures"]:
        m["textures"] = textures_near(stream, name, chunk_type)
    return m


def textures_near(d, name, chunk_type):
    import shpx
    at = d.find(("__Model:::%s.mesh" % name).encode())
    mc = None
    chunks = list(eachar._chunks(d))
    for p, cid, typ, sz in chunks:
        if typ == chunk_type and p <= at < p + sz:
            mc = cid
            break
    if mc is None:
        return {}
    by_id = {cid: (p, typ, sz) for p, cid, typ, sz in chunks}
    ref = struct.pack("<II", mc, chunk_type)
    out = {}
    q = d.find(ref)
    while q >= 0:
        for o in range(max(0, q - 0x200), min(len(d) - 8, q + 0x200), 4):
            tid, tty = struct.unpack_from("<II", d, o)
            c = by_id.get(tid)
            if c and c[1] == tty and tty != chunk_type:
                s = d.find(b"SHPX", c[0], c[0] + c[2])
                if s >= 0:
                    try:
                        for im in shpx.decode(d, s):
                            if im.get("rgba") is not None:
                                out.setdefault(im["name"], im)
                    except (struct.error, IndexError, ValueError):
                        pass
        q = d.find(ref, q + 8)
    return out


def dominant_bones(m):
    """per sub-mesh, per vertex: the bone carrying most of it (None when the sub-mesh has no weights)"""
    out = []
    for k, (pos, uv, tris, shape) in enumerate(m["meshes"]):
        s = m["skin"][k] if m["skin"] and k < len(m["skin"]) else None
        if not s or s["wts"] is None:
            out.append(None)
        else:
            out.append([max(w, key=lambda q: q[1])[0] for w in s["wts"]])
    return out


def panzer_fit(m):
    """the disc turret ring centre / height, gun trunnion and muzzle (disc metres)"""
    db = dominant_bones(m)
    P = {18: [], 19: [], 20: []}
    for k, (pos, uv, tris, shape) in enumerate(m["meshes"]):
        if db[k] is None:
            continue
        for j, p in enumerate(pos):
            if db[k][j] in P:
                P[db[k][j]].append(p)
    t = P[18]
    zmin = min(p[2] for p in t)
    ring = [p for p in t if p[2] < zmin + 0.02]
    cx = (min(p[0] for p in ring) + max(p[0] for p in ring)) / 2
    cy = (min(p[1] for p in ring) + max(p[1] for p in ring)) / 2
    g = P[19]
    tr = tuple((min(p[i] for p in g) + max(p[i] for p in g)) / 2 for i in range(3))
    b = P[20]
    ymax = max(p[1] for p in b)
    tip = [p for p in b if p[1] > ymax - 0.03]
    mz = tuple(sum(p[i] for p in tip) / len(tip) for i in range(3))
    return {"pivot": (cx, cy, zmin), "trunnion": tr, "muzzle": (mz[0], ymax, mz[2]), "db": db}


# ---------------- MOHAA writers ----------------
TIKI_MAX_VERTS = 999
TIKI_MAX_TRIS = 1999


def stock_file(mohaa_base, path):
    """a file from the player's STOCK paks (main, mainta, maintt pak*.pk3; the last copy wins, as the engine loads)"""
    got = None
    for game in ("main", "mainta", "maintt"):
        for pk in sorted(glob.glob(os.path.join(mohaa_base, game, "pak*.pk3")), key=str.lower):
            try:
                z = zipfile.ZipFile(pk)
            except (zipfile.BadZipFile, OSError):
                continue
            for n in z.namelist():
                if n.lower() == path.lower():
                    got = z.read(n)
    return got


def effective_file(mohaa_base, path):
    """the copy the engine loads: every pak in main, mainta, maintt (alphabetical, the last wins), the mod's paks
    included (the coop pak overrides some stock tiks, e.g. statweapons/mg42_gun.tik) - but never a converted BYO pak"""
    got = None
    for game in ("main", "mainta", "maintt"):
        for pk in sorted(glob.glob(os.path.join(mohaa_base, game, "*.pk3")), key=str.lower):
            b = os.path.basename(pk).lower()
            if b.startswith(("zzzz_coop_ea", "zzzz_coop_fl", "zzzz_ea_", "zzzz_fl_")):
                continue
            try:
                z = zipfile.ZipFile(pk)
            except (zipfile.BadZipFile, OSError):
                continue
            for n in z.namelist():
                if n.lower() == path.lower():
                    got = z.read(n)
    return got


def skd_bones(b):
    nsurf, nbones, ofsb = struct.unpack_from("<3i", b, 72)
    o, names = ofsb, []
    for _ in range(nbones):
        names.append(b[o:o + 32].split(b"\0")[0].decode("latin-1"))
        o += struct.unpack_from("<i", b, o + 80)[0]
    return b[ofsb:o], names


def write_skd(name, bone_block, nbones, surfaces):
    """SKMD v6 (scale 1). surfaces: [(surface name, [(pos, nrm, uv, [(bone index, weight, offset)])], tris)]"""
    blobs = []
    for sn, verts, tris in surfaces:
        vb = bytearray()
        for p, n, uv, ws in verts:
            vb += struct.pack("<3f2f2i", n[0], n[1], n[2], uv[0], uv[1], len(ws), 0)
            for bi, w, o in ws:
                vb += struct.pack("<if3f", bi, w, o[0], o[1], o[2])
        tb = b"".join(struct.pack("<3i", *t) for t in tris)
        nV, nT = len(verts), len(tris)
        ofsTri = 100
        ofsVerts = ofsTri + len(tb)
        ofsColl = ofsVerts + len(vb)
        ofsCollIdx = ofsColl + 4 * nV
        ofsEnd = ofsCollIdx + 4 * nV
        hdr = struct.pack("<4s64s8i", b"SKL ", sn.encode().ljust(64, b"\0"), nT, nV, 0, ofsTri, ofsVerts, ofsColl,
                          ofsEnd, ofsCollIdx)
        blobs.append(hdr + tb + bytes(vb) + struct.pack("<%di" % nV, *range(nV)) + bytes(4 * nV))
    body = b"".join(blobs)
    H = 152
    total = H + len(bone_block) + len(body)
    head = struct.pack("<4si64s5i10i4if", b"SKMD", 6, name.encode()[:63].ljust(64, b"\0"), len(blobs), nbones,
                       H, H + len(bone_block), total, *([0] * 10), 0, total, 0, total, 1.0)
    return head + bone_block + body


def write_skc(frametime, channels, frames, bounds, radius):
    """SKAN v13 (uncompressed; the engine converts it at load) with real frame bounds (the renderer culls by them)"""
    nc, nf = len(channels), len(frames)
    ofs_data = 48 + 48 * nf
    ofs_names = ofs_data + 16 * nc * nf
    total = ofs_names + 32 * nc
    head, data = [], bytearray()
    for f, fr in enumerate(frames):
        head.append(struct.pack("<3f3ff3ffi", *bounds[0], *bounds[1], radius, 0.0, 0.0, 0.0, 0.0,
                                ofs_data + 16 * nc * f))
        for c in channels:
            data += struct.pack("<4f", *fr[c])
    names = b"".join(c.encode("latin-1").ljust(32, b"\0") for c in channels)
    hdr = struct.pack("<4s3if3ff3i", b"SKAN", 13, 0, total, frametime, 0.0, 0.0, 0.0, 0.0, nc, ofs_names, nf)
    return hdr + b"".join(head) + bytes(data) + names


def rows_to_quat(m):
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        q = ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = (0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s)
    n = math.sqrt(sum(v * v for v in q)) or 1.0
    q = tuple(v / n for v in q)
    return tuple(-v for v in q) if q[3] < 0 else q


def local_channels(bones, parents, world, scale):
    """{bone: (pos, axes)} model-space frames (world units / scale) -> SKAN channels, local to the parent
    (row vectors: world = local * parent)"""
    ch = {}
    for b in bones:
        pos, ax = world[b]
        pos = tuple(v / scale for v in pos)
        par = parents.get(b)
        if par in world:
            ppos, pax = world[par]
            ppos = tuple(v / scale for v in ppos)
            # local rows = ax * inv(pax) = ax * pax^T ; local origin = (pos - ppos) * pax^T
            lr = [[_dot(ax[i], pax[j]) for j in range(3)] for i in range(3)]
            lo = tuple(_dot(_sub(pos, ppos), pax[j]) for j in range(3))
        else:
            lr, lo = ax, pos
        # mohskel convention: a quaternion channel becomes the local ROWS by QuatToMat
        q = rows_to_quat(lr)
        ch[b + " pos"] = (lo[0], lo[1], lo[2], 0.0)
        ch[b + " rot"] = q
    return ch


def _tga(im):
    return eachar._tga(im)


def surfaces_for(m, sel, place, bone_of, label, keep=None):
    """rigid sub-meshes -> skd surfaces. place(k, j, p) -> map-space position (world units, entity space);
    bone_of(k, j) -> (bone index, (bone pos, bone axes), scale). Chunked at the engine's per-surface limits."""
    out = []
    for k in sel:
        pos, uv, tris, shape = m["meshes"][k]
        sk = m["skin"][k] if m["skin"] and k < len(m["skin"]) else None
        nrm = sk["nrm"] if sk and sk.get("nrm") else None
        V = [place(k, j, p) for j, p in enumerate(pos)]
        N = [to_map_n(nrm[j]) if nrm else (0.0, 0.0, 1.0) for j in range(len(pos))]
        tt = []
        for t in tris:
            fn = _cross(_sub(V[t[1]], V[t[0]]), _sub(V[t[2]], V[t[0]]))
            nn = _add(_add(N[t[0]], N[t[1]]), N[t[2]])
            if keep and not all(keep(k, x) for x in t):
                continue
            tt.append(t if _dot(fn, nn) >= 0 else (t[0], t[2], t[1]))
        chunks, cur, cmap = [], [], {}
        for t in tt:
            new = sum(1 for x in t if x not in cmap)
            if cur and (len(cmap) + new > TIKI_MAX_VERTS or len(cur) + 1 > TIKI_MAX_TRIS):
                chunks.append((cur, cmap))
                cur, cmap = [], {}
            for x in t:
                if x not in cmap:
                    cmap[x] = len(cmap)
            cur.append(t)
        if cur:
            chunks.append((cur, cmap))
        for c, (ct, cmap) in enumerate(chunks):
            order = sorted(cmap, key=cmap.get)
            verts = []
            for j in order:
                bi, (bp, bax), sc = bone_of(k, j)
                lp = tuple(v / sc for v in V[j])
                o = tuple(_dot(_sub(lp, tuple(v / sc for v in bp)), bax[i]) for i in range(3))
                n = tuple(_dot(N[j], bax[i]) for i in range(3))
                verts.append((V[j], n, uv[j], [(bi, 1.0, o)]))
            sn = "%s_%d" % (label, k) if len(chunks) == 1 else "%s_%d_%d" % (label, k, c)
            out.append((sn, verts, [tuple(cmap[x] for x in t) for t in ct], shape))
    return out


# ---------------- the Panzer ----------------
def _stock_tik(mohaa_base, tik):
    b = stock_file(mohaa_base, "models/" + tik)
    return b.decode("latin-1") if b else None


def _retarget_tik(text, mypath, skd, surf_lines, anim_path=None, replace=()):
    """the stock tik with its mesh swapped: path/skelmodel/surface lines replaced, everything else kept"""
    out, done = [], False
    for ln in text.splitlines():
        s = ln.strip().lower()
        if s.startswith("path ") and not done:
            out.append("\tpath %s" % mypath)
            out.append("\tskelmodel %s" % skd)
            out += surf_lines
            if anim_path:
                out.append("\tpath %s" % anim_path)
            done = True
            continue
        if s.startswith("skelmodel ") or (s.startswith("surface ") and " shader " in s):
            continue
        out.append(ln)
    t = "\n".join(out) + "\n"
    for a, b in replace:
        t = t.replace(a, b)
    return t


def build(stream, level, mohaa_base, files, lines, log=print):
    """write the props' models into the converted pak; the data script names their tiks (level.ea_prop_tik)"""
    if not mohaa_base:
        return 0
    made = 0
    for nm, fn in (("Panzer", _build_panzer), ("MG42", _build_mg42)):
        try:
            made += fn(stream, level, mohaa_base, files, lines, log)
        except Exception as e:      # never fail the conversion: that prop keeps the stock model
            log("eaprops: %s skipped (%s)" % (nm, e))
    return made


def _build_panzer(stream, level, mohaa_base, files, lines, log):
    m = read(stream, PANZER["model"], PANZER["chunk"])
    if not m or len(m["meshes"]) != 12 or not m["skin"] or len(m["skin"]) != 12:
        log("eaprops: Panzer IV model not found in the level stream; the tank keeps the stock model")
        return 0
    F = panzer_fit(m)
    PS = PANZER["scale"]
    db = F["db"]
    base_tik = _stock_tik(mohaa_base, "vehicles/PanzerIV_w_base.tik")
    can_tik = _stock_tik(mohaa_base, "vehicles/PanzerIV_w_cannon.tik")
    mg_tik = _stock_tik(mohaa_base, "vehicles/PanzerIV_w_mg42.tik")
    wr_tik = _stock_tik(mohaa_base, "vehicles/PanzerIV_w_d_base.tik")
    sk = {k: stock_file(mohaa_base, "models/vehicles/%s.skd" % k) for k in
          ("PanzerIV_w/PanzerIV_w_base", "PanzerIV_w/PanzerIV_w_cannon", "PanzerIV_w/PanzerIV_w_mg42",
           "PanzerIV_w_d/PanzerIV_w_d_base")}
    if not all((base_tik, can_tik, mg_tik, wr_tik)) or not all(sk.values()):
        log("eaprops: stock Panzer IV (winter) files not found in the install; the tank keeps the stock model")
        return 0
    mdir = "models/vehicles/ea_%s" % level
    tdir = "textures/ea_%s_props" % level   # not under textures/ea_<level>/: eacharup upscales that tree
    pre = "ea_%s_pz" % level
    SB, SC, SD = (STOCK["vehicles/PanzerIV_w_base.tik"], STOCK["vehicles/PanzerIV_w_cannon.tik"],
                  STOCK["vehicles/PanzerIV_w_d_base.tik"])
    piv = to_map(F["pivot"], PS)
    t0 = SB["bones"]["turret0"][0]
    shift = (t0[0] - piv[0], t0[1] - piv[1], 0.0)        # the hull moves so the disc ring centre is on turret0

    def frame(spec, b):
        p, a = spec["bones"][b]
        return p, axes(a)

    turret_set = set(PANZER["turret_bones"])
    gun_set = set(PANZER["gun_bones"])

    # textures and shaders (one per texture; the cross decal blended as on the disc). rgbGen lightingSpherical is the
    # STOCK tank's own (mainta pak1 scripts/Tanks.shader, turret_eu_wntr ...). Tried and rejected 2026-11-15: lightingGrid
    # (gl2: the whole hull orange from the fire-tinted grid) and implicit shaders (gl2: black). Beside a fire the
    # whitewash takes the fire colour more than the stock tank's dark grey - same lighting, brighter albedo
    sh = []
    used = {(m["meshes"][k][3] or "").split("#")[0] for k in set(PANZER["intact"]) | set(PANZER["wreck"])}
    for key, im in sorted(m["textures"].items()):
        if key not in used:
            continue
        tname = "%s/panzer_%s.tga" % (tdir, key.strip("_").lower())
        files[tname] = _tga(im)
        blended = min(im["rgba"][3::4]) < 250
        lift = "" if blended or not PANZER.get("lift") else (
            "\t{\n\t\tmap %s\n\t\tblendFunc GL_SRC_ALPHA GL_ONE\n\t\trgbGen lightingSpherical\n\t\talphaGen const %.2f\n"
            "\t}\n" % (tname, PANZER["lift"]))
        sh.append("%s_%s\n{\n\tcull none\n%s\t{\n\t\tmap %s\n%s\t\trgbGen lightingSpherical\n\t}\n%s}\n" % (
            pre, key.strip("_").lower(), "\tpolygonOffset\n" if blended else "", tname,
            "\t\tblendFunc GL_SRC_ALPHA GL_ONE_MINUS_SRC_ALPHA\n" if blended else "", lift))
    files["scripts/ea_%s_props.shader" % level] = "\n".join(sh).encode()

    def shader_of(shape):
        return "%s_%s" % (pre, (shape or "").split("#")[0].strip("_").lower())

    # 1. hull (base): every intact vertex that is not on the turret, on the 'tank' bone
    bb, bnames = skd_bones(sk["PanzerIV_w/PanzerIV_w_base"])
    ib = bnames.index("tank")
    hull_k = [k for k in PANZER["intact"]]
    sel_hull = {}
    for k in hull_k:
        if db[k] is not None and all(b in turret_set for b in db[k]):
            continue
        sel_hull[k] = 1
    # a sub-mesh carrying both hull and turret vertices (5: hull + turret + gun) is split by vertex
    hull_surfs = surfaces_for(
        m, list(sel_hull), lambda k, j, p: _add(to_map(p, PS), shift),
        lambda k, j: (ib, frame(SB, "tank"), SB["scale"]), "pz_hull",
        keep=lambda k, j: db[k] is None or db[k][j] not in turret_set)
    files["%s/panzer_base.skd" % mdir] = write_skd("ea_panzer_base", bb, len(bnames),
                                                    [(s[0], s[1], s[2]) for s in hull_surfs])
    # 2. turret + gun (cannon): turret body on panzer_IV_turret, gun on main_gun (pitch); its own frames below
    cb, cnames = skd_bones(sk["PanzerIV_w/PanzerIV_w_cannon"])
    off = (shift[0] - t0[0], shift[1] - t0[1], -t0[2])      # disc map space -> the cannon entity's space
    trn = _add(to_map(F["trunnion"], PS), off)
    muz = _add(to_map(F["muzzle"], PS), off)
    cw = {b: frame(SC, b) for b in SC["bones"]}
    cw["pitch"] = (trn, cw["pitch"][1])
    cw["main_gun"] = (trn, cw["main_gun"][1])
    cw["tag_barrel"] = (muz, cw["tag_barrel"][1])
    tur_k = [k for k in PANZER["intact"] if db[k] is not None and any(b in turret_set for b in db[k])]

    def can_bone(k, j):
        b = "main_gun" if db[k][j] in gun_set else "panzer_IV_turret"
        return cnames.index(b), cw[b], SC["scale"]
    can_surfs = surfaces_for(m, tur_k, lambda k, j, p: _add(to_map(p, PS), off), can_bone, "pz_turret",
                             keep=lambda k, j: db[k] is not None and db[k][j] in turret_set)
    files["%s/panzer_cannon.skd" % mdir] = write_skd("ea_panzer_cannon", cb, len(cnames),
                                                      [(s[0], s[1], s[2]) for s in can_surfs])
    parents = {"connect": None, "panzer_IV_turret": "connect", "pitch": "panzer_IV_turret", "main_gun": "pitch",
               "tag_barrel": "main_gun", "controller_hatch": "panzer_IV_turret", "hatch": "controller_hatch",
               "eyebone": "connect", "client_view": "eyebone", "tag_start": None}
    allv = [v[0] for s in can_surfs for v in s[1]]
    lo = tuple(min(v[i] for v in allv) / SC["scale"] for i in range(3))
    hi = tuple(max(v[i] for v in allv) / SC["scale"] for i in range(3))
    rad = math.sqrt(max(_dot(lo, lo), _dot(hi, hi)))
    names = list(SC["bones"])
    chans = [c for b in names for c in (b + " pos", b + " rot")]
    idle = local_channels(names, parents, cw, SC["scale"])
    ow = dict(cw)
    for b, (p, a) in SC["open"].items():
        ow[b] = (p, axes(a))
    opn = local_channels(names, parents, ow, SC["scale"])
    files["%s/panzer_cannon.skc" % mdir] = write_skc(0.05, chans, [idle], (lo, hi), rad)
    files["%s/panzer_cannon_open.skc" % mdir] = write_skc(0.05, chans, [opn], (lo, hi), rad)
    # 3. the hull MG turret: the stock gun entity stays (it fires from the stock tag), its own mesh is not drawn - the
    #    disc hull carries its ball mount
    mb, mnames = skd_bones(sk["PanzerIV_w/PanzerIV_w_mg42"])
    # (the engine refuses an skd with no surfaces: one zero-area triangle on the root bone)
    z3 = [((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0), [(0, 1.0, (0.0, 0.0, 0.0))])] * 3
    files["%s/panzer_mg.skd" % mdir] = write_skd("ea_panzer_mg", mb, len(mnames), [("pz_mg_none", z3, [(0, 1, 2)])])
    SM = STOCK["vehicles/PanzerIV_w_mg42.tik"]
    t1 = SB["bones"]["turret1"][0]
    mgw = {b: frame(SM, b) for b in SM["bones"]}
    mgw["tag_barrel"] = (_sub(_add(to_map(PANZER["ball_mg"], PS), shift), t1), mgw["tag_barrel"][1])
    mpar = {"connect": None, "panzer_IV_mg42": "connect", "tag_barrel": "panzer_IV_mg42", "eyebone": None,
            "Camera01": "eyebone", "pitch": None}
    mn = list(SM["bones"])
    files["%s/panzer_mg.skc" % mdir] = write_skc(0.05, [c for b in mn for c in (b + " pos", b + " rot")],
                                                 [local_channels(mn, mpar, mgw, SM["scale"])],
                                                 ((-40.0, -40.0, -40.0), (40.0, 40.0, 40.0)), 70.0)
    # 4. the wreck: the disc's destroyed set on panzeriv_base_d, the same shift as the hull (the turret is in it)
    wb, wnames = skd_bones(sk["PanzerIV_w_d/PanzerIV_w_d_base"])
    iw = wnames.index("panzeriv_base_d")
    wr_surfs = surfaces_for(m, list(PANZER["wreck"]), lambda k, j, p: _add(to_map(p, PS), shift),
                            lambda k, j: (iw, frame(SD, "panzeriv_base_d"), SD["scale"]), "pz_wreck")
    files["%s/panzer_wreck.skd" % mdir] = write_skd("ea_panzer_wreck", wb, len(wnames),
                                                     [(s[0], s[1], s[2]) for s in wr_surfs])

    def surf_lines(ss):
        seen, out = set(), []
        for s in ss:
            if s[0] not in seen:
                seen.add(s[0])
                out.append("\tsurface %s shader %s" % (s[0], shader_of(s[3])))
        return out
    tik = {}
    tik["base"] = _retarget_tik(base_tik, mdir, "panzer_base.skd", surf_lines(hull_surfs), "models/vehicles/PanzerIV_w",
                                replace=(("vehicles/PanzerIV_w_cannon.tik", "vehicles/ea_%s_panzer_cannon.tik" % level),
                                         ("vehicles/PanzerIV_w_mg42.tik", "vehicles/ea_%s_panzer_mg.tik" % level)))
    ct = _retarget_tik(can_tik, mdir, "panzer_cannon.skd", surf_lines(can_surfs))
    ct = re.sub(r"(?im)^(\s*(?:idle|fire)\s+)PanzerIV_w_cannon\.skc", r"\1panzer_cannon.skc", ct)
    ct = re.sub(r"(?im)^(\s*open\s+)PanzerIV_W_cannon_open\.skc", r"\1panzer_cannon_open.skc", ct)
    tik["cannon"] = ct
    mt = _retarget_tik(mg_tik, mdir, "panzer_mg.skd", ["	surface pz_mg_none shader %s_002" % pre])
    tik["mg"] = re.sub(r"(?im)^(\s*(?:idle|fire)\s+)PanzerIV_w_mg42\.skc", r"\1panzer_mg.skc", mt)
    tik["wreck"] = _retarget_tik(wr_tik, mdir, "panzer_wreck.skd", surf_lines(wr_surfs), "models/vehicles/PanzerIV_w_d")
    for k, t in tik.items():
        files["models/vehicles/ea_%s_panzer%s.tik" % (level, "" if k == "base" else "_" + k)] = t.encode("latin-1")
    lines.append('\tlevel.ea_prop_tik["panzer"] = "models/vehicles/ea_%s_panzer.tik"' % level)
    lines.append('\tlevel.ea_prop_tik["panzer_wreck"] = "models/vehicles/ea_%s_panzer_wreck.tik"' % level)
    if "panzer" in OWN:
        lines.append('\tlevel.ea_prop_own["panzer"] = 1')
    log("eaprops: Panzer_IV_geo -> vehicles/ea_%s_panzer.tik (hull %d / turret %d / wreck %d surfaces; textures %s; "
        "ring shift %.1f %.1f; trunnion %s muzzle %s)" % (level, len(hull_surfs), len(can_surfs), len(wr_surfs),
                                                           sorted(m["textures"]), shift[0], shift[1],
                                                           tuple(round(v, 1) for v in trn),
                                                           tuple(round(v, 1) for v in muz)))
    return 1


# ---------------- the MG42 ----------------
def _sob_store(stream):
    """easob.Store plus the smart objects whose mesh chunk keeps its ELF at another offset than 0x120 (the MG42
    tripod's chunk: ELF at 0x1a0, part ids from 0x50 up to it)"""
    import easob
    S = easob.Store(stream)
    for p, typ, c in easob.chunks(stream):
        e = c.find(b"\x7fELF", 0, 0x1000)
        if e < 0x60 or e == 0x120:
            continue
        ids = [h for h in struct.unpack_from("<%dI" % ((e - 0x50) // 4), c, 0x50) if h in S.objs]
        for ee, h in zip([mm.start() for mm in re.finditer(b"\x7fELF", c)], ids):
            try:
                syms, rel = S._object(c, ee, h)
            except (struct.error, IndexError, ValueError):
                continue
            part = next((x[0][10:] for x in syms or () if x[0].startswith("__Model:::")), None)
            if part and part not in S.models:
                S.models[part] = (c, ee, syms, rel)
    return S


def _shapes(stream, want):
    """texture shapes by name from the stream's SHPX blocks"""
    import shpx
    tex = {}
    for mm in re.finditer(b"SHPX", stream):
        if len(tex) == len(want):
            break
        try:
            size, count = struct.unpack_from("<II", stream, mm.start() + 4)
            if not (16 < size < 16 << 20 and 0 < count < 64):
                continue
            for im in shpx.decode(stream, mm.start()):
                if im.get("rgba") is not None and im["name"] in want:
                    tex.setdefault(im["name"], im)
        except (struct.error, IndexError, ValueError):
            continue
    return tex


def _pole_mesh(stream):
    """the static mount (smart object MG42Tripod_Art_0): [(pos, uv, tris, texture shape)] in disc metres, textures"""
    S = _sob_store(stream)
    if MG42["pole"] not in S.models:
        return [], {}
    ms = S.mesh(MG42["pole"]) or []
    want = {(x["tex"] or "").split("+")[0] for x in ms}
    return [(x["pos"], x["uv"], x["tris"], (x["tex"] or "").split("+")[0]) for x in ms], _shapes(stream, want)


def _build_mg42(stream, level, mohaa_base, files, lines, log):
    m = read(stream, MG42["model"], MG42["chunk"])
    if not m or len(m["meshes"]) != 3:
        log("eaprops: MG42 model not found in the level stream; the guns keep the stock model")
        return 0
    tik_txt = effective_file(mohaa_base, "models/statweapons/mg42_gun.tik")
    skd = effective_file(mohaa_base, "models/statweapons/mg42/mg42.skd")
    if not tik_txt or not skd:
        log("eaprops: stock MG42 turret files not found; the guns keep the stock model")
        return 0
    tik_txt = tik_txt.decode("latin-1")
    SG = STOCK["statweapons/mg42_gun.tik"]
    mdir = "models/statweapons/ea_%s" % level
    tdir = "textures/ea_%s_props" % level
    pre = "ea_%s_mg" % level
    bb, bnames = skd_bones(skd)

    def frame(b):
        p, a = SG["bones"][b]
        return p, axes(a)
    pole, ptex = _pole_mesh(stream)
    texs = dict(m["textures"])
    texs.update(ptex)
    gs = MG42["scale"]
    grip = to_map(MG42["grip"], gs)
    done = 0
    for variant in MG42["variants"]:
        if variant == "pole" and not pole:
            continue
        if variant == "grip":
            # the gun on the stock gunner's hands: its pistol grip where the stock gun's is (39.7 behind, 3.1 under the
            # pivot), on the stock gun's centreline. The stock seat and clips fit it unchanged; the pivot is then near
            # the muzzle (as the stock gun's), so the pintle pole would swing round it and is left out
            off = (SG["grip"][0] - grip[0], 0.0, SG["grip"][2] - grip[2])
        else:
            # the original's mount: the gun turns on its pintle pole (pivot = the gun's own origin, the pole under it).
            # The gunner then stands closer: seat back / down in MG42["pole_seat"] (game.dll turretseat)
            off = (0.0, 0.0, 0.0)
        ib = bnames.index("MG42")
        surfs = surfaces_for(m, (0, 1, 2), lambda k, j, p: _add(to_map(p, gs), off),
                             lambda k, j: (ib, frame("MG42"), SG["scale"]), "mg_gun")
        if variant == "pole":
            ztop = max(p[2] for pos, uv, tris, sh in pole for p in pos)
            pm = {"meshes": [(pos, uv, tris, sh) for pos, uv, tris, sh in pole], "skin": None}
            io = bnames.index("origin")
            surfs += surfaces_for(pm, range(len(pole)),
                                  lambda k, j, p: _add(to_map((p[0], p[1], p[2] - ztop - 0.02), gs), off),
                                  lambda k, j: (io, frame("origin"), SG["scale"]), "mg_pole")
        suf = "" if variant == "grip" else "_pole"
        files["%s/mg42%s.skd" % (mdir, suf)] = write_skd("ea_mg42" + suf, bb, len(bnames),
                                                         [(x[0], x[1], x[2]) for x in surfs])
        w = {b: frame(b) for b in SG["bones"]}
        w["tag_barrel"] = (_add(to_map(MG42["muzzle"], gs), off), w["tag_barrel"][1])
        w["tag_eject"] = (_add(to_map(MG42["eject"], gs), off), w["tag_eject"][1])
        par = {"origin": None, "tag_barrel": "origin", "MG42": "origin", "tag_eject": "origin"}
        names = list(SG["bones"])
        ch = local_channels(names, par, w, SG["scale"])
        allv = [v[0] for x in surfs for v in x[1]]
        lo = tuple(min(v[i] for v in allv) / SG["scale"] for i in range(3))
        hi = tuple(max(v[i] for v in allv) / SG["scale"] for i in range(3))
        rad = math.sqrt(max(_dot(lo, lo), _dot(hi, hi)))
        chans = [c for b in names for c in (b + " pos", b + " rot")]
        files["%s/mg42%s.skc" % (mdir, suf)] = write_skc(0.05, chans, [ch], (lo, hi), rad)
        nf = max(1, int(round(SG["fire_len"] / 0.05)))
        files["%s/mg42fire%s.skc" % (mdir, suf)] = write_skc(0.05, chans, [ch] * nf, (lo, hi), rad)
        keys = []
        for x in surfs:
            key = (x[3] or "").split("#")[0]
            if key and key in texs and key not in keys:
                keys.append(key)
        shtxt = []
        sp = "scripts/ea_%s_props.shader" % level
        for key in keys:
            sname = "%s_%s" % (pre, key.lower())
            if sname.encode() in files.get(sp, b""):
                continue
            im = texs[key]
            tname = "%s/mg42_%s.tga" % (tdir, key.lower())
            files[tname] = _tga(im)
            cut = min(im["rgba"][3::4]) < 250
            shtxt.append("%s\n{\n\tcull none\n\t{\n\t\tmap %s\n%s\t\trgbGen lightingSpherical\n\t}\n}\n" % (
                sname, tname, "\t\talphaFunc GE128\n" if cut else ""))
        if shtxt:
            files[sp] = files.get(sp, b"") + ("\n" + "\n".join(shtxt)).encode()
        sl, seen = [], set()
        for x in surfs:
            key = (x[3] or "").split("#")[0]
            if x[0] not in seen and key in keys:
                seen.add(x[0])
                sl.append("\tsurface %s shader %s_%s" % (x[0], pre, key.lower()))
        t = _retarget_tik(tik_txt, mdir, "mg42%s.skd" % suf, sl)
        if suf:
            t = re.sub(r"(?im)^(\s*idle\s+)mg42\.skc", r"\1mg42%s.skc" % suf, t)
            t = re.sub(r"(?im)^(\s*fire\s+)mg42fire\.skc", r"\1mg42fire%s.skc" % suf, t)
        files["models/statweapons/ea_%s_mg42%s.tik" % (level, suf)] = t.encode("latin-1")
        lines.append('\tlevel.ea_prop_tik["mg42%s"] = "models/statweapons/ea_%s_mg42%s.tik"' % (suf, level, suf))
        log("eaprops: %s -> statweapons/ea_%s_mg42%s.tik (%d surfaces; offset %s)" % (
            MG42["model"], level, suf, len(surfs), tuple(round(v, 1) for v in off)))
        done = 1
    if done and "mg42" in OWN:
        lines.append('\tlevel.ea_prop_own["mg42"] = 1')
    if done and pole:
        bk, dn = MG42["pole_seat"]
        lines.append('\tlevel.ea_prop_mgseat = ( %.1f %.1f 0 )' % (bk, dn))
        # the pole gun's pivot over the MMG point: the disc pole's own height (base -0.004 m .. fork top 0.391 m) plus
        # the 2 cm the gun's origin sits over the fork, at the gun's scale (0.415 m = 21.6u). The original's smart-object
        # gun on the same point has its receiver 0.43-0.45 m up: the same height
        zlo = min(p[2] for pos, uv, tris, sh in pole for p in pos)
        zhi = max(p[2] for pos, uv, tris, sh in pole for p in pos)
        lines.append('\tlevel.ea_poleH = %.1f' % ((zhi - zlo + 0.02) * MG42["scale"]))
    return done
