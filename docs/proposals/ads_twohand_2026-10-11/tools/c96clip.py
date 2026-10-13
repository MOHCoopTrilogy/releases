"""Mauser C96: the STRIPPER CLIP that is seen, and a bolt with real travel (pistol lane, 2026-10-13).

Added to the staged coop_c96/c96.skd (after bonefit.split), every new part at its HIDDEN rest place so that a clip
without the new channels (idle, fire, the retail reload) shows nothing new:
  bone coop_rounds   eight cartridges (cases surface coop_c96_case, bullets coop_c96_bullet), rest = pushed down inside the
                     magazine box
  bone coop_clip     the brass strip (coop_c96_strip), rest = inside the magazine box
  bone coop_port     a dark patch = the open top of the action (coop_c96_port), rest = 0.12 u under the top face
  bone coop_slide    (the bolt end, from the split) gets the bolt BAR (coop_c96_boltbar): inside the barrel extension
                     when shut, it bridges the gap when the bolt end is back (2.0 u now, was 0.42)
Gun space as gungeo reports it: +x muzzle, +y right, +z down, tik-scaled units (1 u = about 18 mm on this mesh).

Channels: clip_channels() reads the BAKED hands clip (left hand in the gun's frame, per frame) - the clip is rigid to
the support hand from the pouch to the guides, stands in the guides while the thumb runs the rounds down, leaves with
the hand and is flicked away.
"""
import os, sys, struct, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bonefit as BF
import gunskc
R = gunskc.R
PR = BF.PR
G = PR.gungeo
SK = PR.skdlib

NR = 8                    # rounds on the clip (the gun's clipsize)
PITCH = 0.50              # u between rounds
RC = 0.25                 # case radius
CY = -0.74                # centre line of the action, y
TOPZ = -3.99              # top face of the barrel extension
X0 = 5.95                 # case heads (just ahead of the rear sight), bullets point to the muzzle
LCASE, LBUL = 1.38, 0.55
PRESS = NR * PITCH + 0.12 # how far the column goes down: all of it under the top face
CG = np.array([X0, CY, TOPZ - 0.05])          # the clip's reference point when it stands in the guides (column foot)
CREST = CG + np.array([0.0, 0.0, PRESS])      # ... at rest (hidden)
BOLT = 2.0
BAR = dict(x=(1.15, 1.15 + BOLT + 0.25), y=(-1.06, -0.48), z=(-3.66, -2.96))
SHADERS = dict(coop_c96_case=(184, 150, 72), coop_c96_bullet=(176, 104, 62), coop_c96_strip=(128, 104, 50),
               coop_c96_boltbar=(74, 84, 96), coop_c96_port=(7, 8, 10))


def _orient(verts, tris):
    """retail winding: cross(b-a, c-a) . n < 0 for the face normal n (mean of the three vertex normals)"""
    out = []
    for t in tris:
        pa, pb, pc = (verts[i][0] for i in t)
        n = verts[t[0]][1] + verts[t[1]][1] + verts[t[2]][1]
        if np.cross(pb - pa, pc - pa) @ n > 0:
            t = (t[0], t[2], t[1])
        out.append(tuple(t))
    return out


def frustum_x(x0, x1, cy, cz, r0, r1, n=8, cap0=True, cap1=True):
    """a round body along x; smooth side normals, flat caps"""
    V, T = [], []
    sl = math.atan2(r0 - r1, x1 - x0)
    for k in range(n):
        a = 2 * math.pi * k / n
        nr = np.array([math.sin(sl), math.cos(sl) * math.cos(a), math.cos(sl) * math.sin(a)])
        V.append((np.array([x0, cy + r0 * math.cos(a), cz + r0 * math.sin(a)]), nr, (0.5, 0.5)))
        V.append((np.array([x1, cy + r1 * math.cos(a), cz + r1 * math.sin(a)]), nr, (0.5, 0.5)))
    for k in range(n):
        a0, b0 = 2 * k, 2 * k + 1
        a1, b1 = 2 * ((k + 1) % n), 2 * ((k + 1) % n) + 1
        T += [(a0, b0, b1), (a0, b1, a1)]
    for cap, x, r, sg in ((cap0, x0, r0, -1.0), (cap1, x1, r1, 1.0)):
        if not cap:
            continue
        nrm = np.array([sg, 0.0, 0.0]); b = len(V)
        V.append((np.array([x, cy, cz]), nrm, (0.5, 0.5)))
        for k in range(n):
            a = 2 * math.pi * k / n
            V.append((np.array([x, cy + r * math.cos(a), cz + r * math.sin(a)]), nrm, (0.5, 0.5)))
        T += [(b, b + 1 + k, b + 1 + (k + 1) % n) for k in range(n)]
    return V, _orient(V, T)


def box(lo, hi):
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    c = (lo + hi) / 2; h = (hi - lo) / 2
    V, T = [], []
    for ax in range(3):
        for sg in (-1.0, 1.0):
            n = np.zeros(3); n[ax] = sg
            u = np.zeros(3); u[(ax + 1) % 3] = 1.0
            v = np.zeros(3); v[(ax + 2) % 3] = 1.0
            b = len(V)
            for a, bb in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                V.append((c + n * h + u * a * h + v * bb * h, n, (0.5, 0.5)))
            T += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
    return V, _orient(V, T)


def merge(parts):
    V, T = [], []
    for v, t in parts:
        b = len(V)
        V += v
        T += [(a + b, bb + b, c + b) for a, bb, c in t]
    return V, T


def geometry():
    """{surface: (bone, verts, tris)} at the REST (hidden) place"""
    cases, bullets = [], []
    for k in range(NR):
        cz = CREST[2] - RC - k * PITCH                          # round k above the foot (z up = negative)
        cases.append(frustum_x(X0, X0 + LCASE, CY, cz, RC, RC, cap1=False))
        cases.append(frustum_x(X0 - 0.05, X0, CY, cz, RC + 0.03, RC + 0.03))              # the rim
        bullets.append(frustum_x(X0 + LCASE, X0 + LCASE + LBUL * 0.6, CY, cz, RC * 0.82, RC * 0.6, cap0=False, cap1=False))
        bullets.append(frustum_x(X0 + LCASE + LBUL * 0.6, X0 + LCASE + LBUL, CY, cz, RC * 0.6, RC * 0.22, cap0=False))
    top = CREST[2] - NR * PITCH + 0.03          # at rest just under the top face
    strip = [box((X0 - 0.16, CY - 0.33, top), (X0 - 0.06, CY + 0.33, CREST[2] + 0.02)),                  # the back
             box((X0 - 0.16, CY - 0.33, top), (X0 + 0.10, CY - 0.27, CREST[2] + 0.02)),                  # two lips over the rims
             box((X0 - 0.16, CY + 0.27, top), (X0 + 0.10, CY + 0.33, CREST[2] + 0.02))]
    bar = [box((BAR['x'][0], BAR['y'][0], BAR['z'][0]), (BAR['x'][1], BAR['y'][1], BAR['z'][1]))]
    pz = TOPZ + 0.12
    port = [box((X0 - 0.12, CY - 0.36, pz - 0.02), (X0 + LCASE + LBUL + 0.1, CY + 0.36, pz))]
    return dict(coop_c96_case=('coop_rounds', ) + merge(cases), coop_c96_bullet=('coop_rounds', ) + merge(bullets),
                coop_c96_strip=('coop_clip', ) + merge(strip), coop_c96_boltbar=('coop_slide', ) + merge(bar),
                coop_c96_port=('coop_port', ) + merge(port))


def add_bone(data, newbone, parent):
    import add_part as AP
    m = SK.read_skd(data)
    assert newbone not in [b.name for b in m.bones], newbone
    bb = AP.bone_block(newbone, parent)
    ins = m.ofsSurfaces
    out = bytearray(data[:ins]) + bb + bytearray(data[ins:])
    end = m.ofsEnd + len(bb)
    struct.pack_into('<5i', out, 72, m.numSurfaces, m.numBones + 1, m.ofsBones, m.ofsSurfaces + len(bb), end)
    tail = list(struct.unpack_from('<4i', out, 132))
    struct.pack_into('<4i', out, 132, *[end if x == m.ofsEnd else x for x in tail])
    return bytes(out)


def append_surface(data, name, verts, tris, bone, M, sc):
    """a new skelSurface_t after the last one (m10face.append_surface). verts in GUN space; M = the bone's 4x3 world"""
    m = SK.read_skd(data)
    last = max(m.surfaces, key=lambda s: s.raw_off)
    off = last.raw_off
    ntri, nvert, static, oTri, oVerts, oColl, oEnd, oCI = struct.unpack_from('<8i', data, off + 68)
    assert off + oEnd == m.ofsEnd, (off + oEnd, m.ofsEnd, len(data))
    ci_max = max(max(struct.unpack_from('<%di' % s.numVerts, data, s.raw_off + struct.unpack_from('<8i', data, s.raw_off + 68)[7]))
                 for s in m.surfaces)
    head = bytearray(data[off: off + oTri])
    nb = name.encode('latin-1')
    head[4:68] = nb + b'\0' * (64 - len(nb))
    Rt = np.asarray(M)[0:3].T
    bt = b''.join(struct.pack('<3i', *t) for t in tris)
    bv = b''
    for p, n, uv in verts:
        o = (p / sc - np.asarray(M)[3]) @ Rt
        bv += struct.pack('<3f2f2i', *(n @ Rt), float(uv[0]), float(uv[1]), 1, 0) + struct.pack('<if3f', bone, 1.0, *o)
    bc = struct.pack('<%di' % len(verts), *([0] * len(verts)))
    bi = struct.pack('<%di' % len(verts), *([ci_max] * len(verts)))
    o1 = oTri; o2 = o1 + len(bt); o3 = o2 + len(bv); o4 = o3 + len(bc); o5 = o4 + len(bi)
    struct.pack_into('<8i', head, 68, len(tris), len(verts), static, o1, o2, o3, o5, o4)
    blk = bytes(head) + bt + bv + bc + bi
    out = bytearray(data[:m.ofsEnd]) + blk + bytearray(data[m.ofsEnd:])
    end = m.ofsEnd + len(blk)
    struct.pack_into('<5i', out, 72, m.numSurfaces + 1, m.numBones, m.ofsBones, m.ofsSurfaces, end)
    tail = list(struct.unpack_from('<4i', out, 132))
    struct.pack_into('<4i', out, 132, *[end if x == m.ofsEnd else x for x in tail])
    return bytes(out)


def add_to_skd(skd_file, tik):
    data = open(skd_file, 'rb').read()
    if any(s.name == 'coop_c96_case' for s in SK.read_skd(data).surfaces):
        print('c96 clip parts already in the skd'); return
    for b in ('coop_rounds', 'coop_clip', 'coop_port'):
        data = add_bone(data, b, 'origin')
    m = SK.read_skd(data)
    names = [b.name for b in m.bones]
    t = G.parse_tik(tik)
    sc = t['scale']
    skc = SK.read_skc(PR.vfs.read(G._res(t, t['anims']['idle'])))
    mats, _ = G.bone_world(m, skc, 0)
    Mo = mats[names.index('origin')]                    # the new bones sit at identity under `origin`
    nv = 0
    for sname, (bone, V, T) in geometry().items():
        data = append_surface(data, sname, V, T, names.index(bone), Mo, sc)
        nv += len(V)
    open(skd_file, 'wb').write(data)
    print('c96 clip parts ->', os.path.basename(skd_file), 'bones', names[-4:], 'new verts', nv, 'surfaces', [s.name for s in SK.read_skd(data).surfaces][-5:])


def textures(root):
    from PIL import Image
    d = os.path.join(root, 'textures', 'coop_c96'); os.makedirs(d, exist_ok=True)
    sh = ''
    for name, col in SHADERS.items():
        im = Image.new('RGB', (16, 16), col)
        px = im.load()
        for y in range(16):
            for x in range(16):
                k = 1.0 + 0.06 * math.sin(x * 1.7 + y * 0.9)
                px[x, y] = tuple(max(0, min(255, int(c * k))) for c in col)
        im.save(os.path.join(d, name + '.tga'))
        sh += '%s\n{\n\tqer_editorimage textures/coop_c96/%s.tga\n\t{\n\t\tmap textures/coop_c96/%s.tga\n\t\trgbGen lightingSpherical\n\t}\n}\n' % (name, name, name)
    os.makedirs(os.path.join(root, 'scripts'), exist_ok=True)
    open(os.path.join(root, 'scripts', 'coop_c96_clip.shader'), 'w', newline='\n').write(
        '// HZM coop: Mauser C96 stripper clip, rounds, bolt bar, open port (pistol lane 2026-10-13; c96clip.py)\n' + sh)


def tik_lines(s):
    """the five `surface <new> shader <new>` lines after the last surface line of the setup block"""
    import re
    if 'coop_c96_case' in s:
        return s
    ms = list(re.finditer(r'(?im)^([ \t]*)surface[ \t]+\S+[ \t]+shader[ \t]+\S+[^\n]*\n', s[:s.index('}')]))
    assert ms, 'no surface line in the setup block'
    ind = ms[-1].group(1)
    add = ind + '// HZM coop [pistol lane 2026-10-13]: stripper clip, its rounds, the bolt bar and the open port (hidden at rest)\n'
    add += ''.join('%ssurface %s shader %s\n' % (ind, n, n) for n in SHADERS)
    return s[:ms[-1].end()] + add + s[ms[-1].end():]


def hand_in_gun(hands_file):
    """[4x4 rows per frame]: the support hand in the gun's frame, translation in gun units"""
    a = R.load(hands_file)
    out = []
    for f in range(a.numFrames):
        W = R.evaluate(R.pose_dict(a, f))
        rel = (W['Bip01 L Hand'] @ R.inv(W['tag_weapon_right'])).copy()
        rel[3, 0:3] *= R.S
        out.append(rel)
    return out


def _tr(c):
    T = np.eye(4); T[3, 0:3] = c
    return T


def clip_channels(A, o, hands_file, K, n, bolt_state):
    """channels of coop_clip / coop_rounds / coop_port for an aimed reload of n frames.
    K: pouch=(p0,p1), at, press=(s0,s1), out=(o0,o1)"""
    H = hand_in_gun(hands_file)
    assert len(H) >= n, (len(H), n)
    p0 = K['pouch'][0]; at = K['at']; s0, s1 = K['press']; o0, o1 = K['out']
    Xin = _tr(CG) @ np.linalg.inv(H[at])            # clip local (origin = its foot) -> hand local, for the way in
    Xout = _tr(CG) @ np.linalg.inv(H[o0])
    fly0 = o1 + 1
    Xf = Xout @ H[fly0]
    v = (Xf[3, 0:3] - (Xout @ H[fly0 - 1])[3, 0:3])
    v = v * 0.5 + np.array([-0.25, -0.75, -0.12])          # flicked to the left (-y), a little up, per frame
    ch = {k: [] for k in ('coop_clip pos', 'coop_clip rot', 'coop_rounds pos', 'coop_rounds rot', 'coop_port pos', 'coop_port rot')}
    trace = []
    for f in range(n):
        if f < p0:
            Xc = None
        elif f < at:
            Xc = Xin @ H[f]
        elif f < o0:
            Xc = _tr(CG)
        elif f <= fly0:
            Xc = Xout @ H[f]
        elif f <= fly0 + 9:
            k = f - fly0
            Xc = Xf.copy()
            Xc[0:3, 0:3] = Xf[0:3, 0:3] @ BF.rot_rows((1, 0, 0), 38.0 * k)
            Xc[3, 0:3] = Xf[3, 0:3] + v * k + np.array([0.0, 0.0, 0.10 * k * k])
        else:
            Xc = None
        if f < p0:
            Xr = None
        elif f < at:
            Xr = Xin @ H[f]
        elif f < s1:
            u = 0.0 if f < s0 else (f - s0) / float(s1 - s0)
            u = u * u * (3 - 2 * u)
            Xr = _tr(CG + np.array([0.0, 0.0, PRESS * u]))
        else:
            Xr = None
        for nm, X in (('coop_clip', Xc), ('coop_rounds', Xr)):
            if X is None:
                p, q = BF.chan(A, o, np.eye(3), (0, 0, 0), (0, 0, 0))
            else:
                p, q = BF.chan(A, o, X[0:3, 0:3], CREST, X[3, 0:3] - CREST)
            ch[nm + ' pos'].append(p); ch[nm + ' rot'].append(q)
        p, q = BF.chan(A, o, np.eye(3), (0, 0, 0), (0.0, 0.0, -0.24 if bolt_state(f) > 0.5 else 0.0))
        ch['coop_port pos'].append(p); ch['coop_port rot'].append(q)
        trace.append(None if Xc is None else Xc[3, 0:3])
    return ch, trace


def port_only(A, o, n, state):
    ch = {}
    idp, idq = BF.chan(A, o, np.eye(3), (0, 0, 0), (0, 0, 0))
    for nm in ('coop_clip', 'coop_rounds'):
        ch[nm + ' pos'] = [idp] * n; ch[nm + ' rot'] = [idq] * n
    pq = [BF.chan(A, o, np.eye(3), (0, 0, 0), (0.0, 0.0, -0.24 if state(f) > 0.5 else 0.0)) for f in range(n)]
    ch['coop_port pos'] = [p for p, q in pq]; ch['coop_port rot'] = [q for p, q in pq]
    return ch
