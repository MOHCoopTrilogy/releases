"""[flguns] copy of docs/proposals/ironsights_2026-09-28/tools/gungeo.py for the converter bundle (the ROOT_APPLY
opt-in and its sights.json lookup are left out: the disc-gun fit uses the root-stripped frame). Weapon viewmodel geometry: TIK -> SKD + idle SKC -> skinned vertices in weapon model space.

Conventions (verified in skdlib.py against the engine source):
  vertex offset is bone-local, row-vector: p = offset * M3 + t ; world = local * parent
  POSROT bone local = QuatToMat("<bone> rot"), translation "<bone> pos" from the SKC frame
Model space is then multiplied by the TIK `scale` (0.52 for every retail weapon).
Weapon model space: +X = muzzle direction, +Z = up (checked per gun with tag_barrel).
"""
import os, re, math
import numpy as np
import flgunvfs as vfs, flgunskd as skdlib


def parse_tik(path, _depth=0):
    """Minimal TIK reader: scale, path, skelmodel, surface->shader, idle anim, name."""
    raw = vfs.read(path)
    if raw is None:
        raise FileNotFoundError(path)
    s = raw.decode('latin-1')
    s_nc = re.sub(r'//[^\n]*', '', s)
    t = {'tik': path, 'scale': 1.0, 'path': '', 'skel': [], 'surf': {}, 'anims': {}, 'name': None}
    for inc in re.findall(r'^\s*\$include\s+(\S+)', s_nc, re.M):
        if _depth < 4:
            try:
                sub = parse_tik(inc, _depth + 1)
                for k in ('scale', 'path', 'name'):
                    if sub[k]:
                        t[k] = sub[k]
                t['skel'] += sub['skel']; t['surf'].update(sub['surf']); t['anims'].update(sub['anims'])
            except FileNotFoundError:
                pass
    m = re.search(r'^\s*scale\s+([-\d.]+)', s_nc, re.M)
    if m:
        t['scale'] = float(m.group(1))
    m = re.search(r'^\s*path\s+(\S+)', s_nc, re.M)
    if m:
        t['path'] = m.group(1)
    t['skel'] += [x for x in re.findall(r'^\s*skelmodel\s+(\S+)', s_nc, re.M)]
    for a, b in re.findall(r'^\s*surface\s+(\S+)\s+shader\s+(\S+)', s_nc, re.M):
        t['surf'][a.lower()] = b
    m = re.search(r'\bname\s+"([^"]+)"', s_nc)
    if m:
        t['name'] = m.group(1)
    am = re.search(r'^animations\s*\{(.*)', s_nc, re.M | re.S)
    if am:
        for a, f in re.findall(r'^\s*([A-Za-z_][\w]*)\s+(\S+\.skc)', am.group(1), re.M):
            t['anims'].setdefault(a, f)
    return t


def _res(t, f):
    p = (t['path'] + '/' + f) if t['path'] and '/' not in f else f
    return p


def quat_mat(q):
    return np.array(skdlib.quat_to_mat3(q), dtype=float)


def bone_world(skd, skc, frame=0, keep_root=False):
    """name -> 4x3 row-vector matrix (rows 0..2 = rotation, row 3 = translation)."""
    chan = {}
    if skc is not None:
        for i, c in enumerate(skc.channels):
            chan[c] = skdlib.skc_channel(skc, min(frame, skc.numFrames - 1), i)
    # [from the pistolsB batch] multi-root skeletons: bone 0's pose is dropped (measured, bug-3228), which is the same as
    # expressing the pose RELATIVE TO bone 0. A second root (parent worldbone, e.g. the xW silenced Beretta's can
    # chain 'origin'/'colt45') must then carry the inverse bone-0 transform too, or it lands where the engine does not
    # draw it (the can hung 6u under the grip). Identity for every gun whose bone 0 is at rest (all retail AA guns).
    r0 = chan.get(skd.bones[0].name + ' rot') if skd.bones else None
    p0 = chan.get(skd.bones[0].name + ' pos') if skd.bones else None
    M0 = np.vstack([quat_mat(r0) if r0 else np.eye(3), np.array(p0[:3]) if p0 else np.zeros(3)])
    if keep_root:
        M0 = np.vstack([np.eye(3), np.zeros(3)])
    M0inv_R = M0[:3].T
    M0inv = np.vstack([M0inv_R, -M0[3] @ M0inv_R])
    world = {}
    out = []
    for bi, b in enumerate(skd.bones):
        rot = chan.get(b.name + ' rot')
        pos = chan.get(b.name + ' pos')
        if bi == 0 and not keep_root:
            # MEASURED IN-ENGINE 2026-09-28 (ironsights run s1080): the drawn first-person gun does NOT carry
            # the root bone's animation channel - the HRRTM Garand idle clip keys 'origin' at (0.006 1.506 0) /
            # -1.24 deg yaw, and only the Garand's cgame prediction disagreed with its screenshot (0.78u + 1.3 deg);
            # every gun with an identity root matched to ~1 px. Root motion is delta, not pose.
            rot, pos = None, None
        M3 = quat_mat(rot) if rot else np.eye(3)
        T = np.array(pos[:3]) if pos else np.zeros(3)
        loc = np.vstack([M3, T])
        par = world.get(b.parent)
        if par is not None:
            R = loc[:3] @ par[:3]
            tr = loc[3] @ par[:3] + par[3]
            w = np.vstack([R, tr])
        elif bi > 0:
            w = np.vstack([loc[:3] @ M0inv[:3], loc[3] @ M0inv[:3] + M0inv[3]])
        else:
            w = loc
        world[b.name] = w
        out.append(w)
    return out, world


def surf_shader(t, name):
    """TIKI `surface <prefix>* shader X` WILDCARD (retail MP40 `gun*`, Type 100 `Skin*`, the Pacific Garand...: 17 live
    TIKIs). Exact name first, then the longest matching wildcard, then `all`. [found by the smgs + variants batches]"""
    n = name.lower()
    if n in t['surf']:
        return t['surf'][n]
    wild = sorted((k for k in t['surf'] if k.endswith('*') and n.startswith(k[:-1])), key=len, reverse=True)
    if wild:
        return t['surf'][wild[0]]
    return t['surf'].get('all', name)


def load_gun(tikpath, anim='idle', frame=0):
    t = parse_tik(tikpath)
    skdp = _res(t, t['skel'][0])
    skd = skdlib.read_skd(vfs.read(skdp))
    skc = None
    if anim in t['anims']:
        cp = _res(t, t['anims'][anim])
        d = vfs.read(cp)
        if d is not None:
            skc = skdlib.read_skc(d)
            t['skc'] = cp
    keep = False
    mats, world = bone_world(skd, skc, frame, keep_root=keep)
    surfs = []
    for s in skd.surfaces:
        P = np.zeros((s.numVerts, 3)); UV = np.zeros((s.numVerts, 2))
        for vi, (normal, texc, wl, ml) in enumerate(s.verts):
            acc = np.zeros(3)
            for bi, bw, off in wl:
                M = mats[bi]
                acc += bw * (np.array(off) @ M[:3] + M[3])
            P[vi] = acc
            UV[vi] = texc
        tri = np.frombuffer(bytes(s.tri_bytes), dtype='<i4').reshape(-1, 3)
        shader = surf_shader(t, s.name)
        surfs.append({'name': s.name, 'P': P * t['scale'], 'UV': UV, 'tri': tri, 'shader': shader})
    tags = {k: (v[3] * t['scale'], v[:3]) for k, v in world.items() if k.lower().startswith('tag_')}
    return {'tik': t, 'skd': skdp, 'skdpak': vfs.pakname(vfs.winner(skdp)[0]), 'surfs': surfs, 'tags': tags}


def all_points(g):
    return np.vstack([s['P'] for s in g['surfs']])


def root_transform(tikpath, anim='idle', frame=0):
    """(R3, t) of bone 0 from the idle clip, t in TIKI-scaled units: the transform a point in gungeo's root-stripped
    frame gets if the engine DOES draw the root channel (p_applied = p @ R3 + t). None when the root is at rest."""
    t = parse_tik(tikpath)
    skd = skdlib.read_skd(vfs.read(_res(t, t['skel'][0])))
    if anim not in t['anims']:
        return None
    d = vfs.read(_res(t, t['anims'][anim]))
    if d is None:
        return None
    skc = skdlib.read_skc(d)
    chan = {c: skdlib.skc_channel(skc, min(frame, skc.numFrames - 1), i) for i, c in enumerate(skc.channels)}
    r = chan.get(skd.bones[0].name + ' rot'); p = chan.get(skd.bones[0].name + ' pos')
    R3 = quat_mat(r) if r else np.eye(3)
    tr = (np.array(p[:3]) if p else np.zeros(3)) * t['scale']
    ang = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(R3) - 1) / 2))))
    if ang < 0.5 and np.linalg.norm(tr) < 0.05:
        return None
    return R3, tr, ang

