"""M1919 .30 cal portable: real sights (bug-3622: the aim was a black receiver wall - the cgame had no sight row for
this gun and the mesh no front sight). A STAGED copy of the mod's models/weapons/30calportable/30cal.skd + one new
surface -> assets/models/weapons/30calportable/coop_30cal_sights.skd, and the staged tik that names it. Nothing of
the retail / mod mesh is removed or moved (every vertex, UV, weight and the LOD maps stay byte-identical), the gun
clips (30cal.skc, coop_30cal_reload.skc) resolve as before (same model directory, same bones).

What the mesh has (tools/../parts scan; gun frame as gungeo loads it: x forward, y right, z down, tik-scaled u):
    receiver box x -2.2..17.0, top z -4.98; top cover x 4.9..16.6 (bone `cover`), front block x 15.95..17.52 top z -5.02
    barrel jacket x 16.7..45.2, top z -3.6 (1.4 u UNDER the receiver's top)
    a REAR LEAF: base block x -1.0..2.6 with two knobs, and an upright frame x -0.79..-0.31, z -8.95..-6.38 whose two
    posts (y -0.51..-0.24 and 0.23..0.50) leave a window 0.47 u wide - EMPTY: no slider, no notch
    NO front sight at all
Added, surface `coop_sight` on bone `origin` (shader coop_30cal_sight, dark steel; the M1919A4's own layout):
    REAR  a slider across the leaf's window with a square notch on the centre line, a worn band round the notch and
          along the slider's top on the eye's side
    FRONT on the trunnion block in front of the cover hinge: a foot, a tapered support and a blade, a worn-bright
          band across the blade's top on the eye's side
Sight line: blade tip -> the notch's shoulders, parallel to the bore, 2.9 u above the receiver's top: the eye looks
along the top cover, the jacket lies below the line.

    python m1919sights.py [--out <skd>]
"""
import sys, os, re, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hv
RT = os.path.normpath(os.path.join(hv.LANE, '..', 'rifles', 'tools'))
sys.path.insert(0, RT)
import staged
import g43irons as G
gungeo, vfs = G.gungeo, G.vfs
MODTIK = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod\models\weapons\30calportable.tik"
SRC_TIK = 'models/weapons/30calportable.tik'
SRC_SKD = 'models/weapons/30calportable/30cal.skd'
OUT = hv.staged('models/weapons/30calportable/coop_30cal_sights.skd')
E = lambda k, d: float(os.environ.get(k, d))
YC = -0.005                                    # the leaf window's centre (posts y -0.24 / 0.23)
ZS = E('M19_Z', -7.90)                         # the sight line's height (z down): the notch's shoulders = the blade's tip
REAR = dict(x0=-0.63, x1=-0.47, half=0.262, zb=ZS + E('M19_SH', 0.46), nw=E('M19_NW', 0.10), nd=E('M19_ND', 0.17), band=0.045)
FRONT = dict(xb0=16.72, xb1=17.46, zblk=-5.00, zfoot=-5.24, xs0=16.88, xs1=17.34, zs=-6.55, x0=17.02, x1=17.20,
             foot=0.17, mid=0.14, top=E('M19_BW', 0.125), band=0.16)
UD, UE = G.UV_DARK, G.UV_EDGE
SHADER = G.SHADER.replace('coop_g43_sight', 'coop_30cal_sight').replace('g43_sight.tga', '30cal_sight.tga').replace(
    '[rifle lane 2026-10-12] iron-sight G43 (tools/g43irons.py): the tangent sight\'s notch plate and the front',
    '[heavy lane 2026-10-13] M1919 .30 cal (tools/m1919sights.py): the rear leaf\'s notch slider and the front').replace(
    '// post, dark steel on every finish.', '// blade, dark steel.')


def box(m, x0, x1, y0, y1, z0, z1, u=UD):
    m.prism([(y0, z0), (y1, z0), (y1, z1), (y0, z1)], x0, x1, u)


def sight_mesh():
    m = G.Mesh()
    r = REAR
    zt, zb, h, nw, nd = ZS, r['zb'], r['half'], r['nw'], r['nd']
    # the slider = three boxes (left cheek, right cheek, the web under the notch)
    box(m, r['x0'], r['x1'], YC - h, YC - nw, zt, zb)
    box(m, r['x0'], r['x1'], YC + nw, YC + h, zt, zb)
    box(m, r['x0'], r['x1'], YC - nw, YC + nw, zt + nd, zb)
    xe = r['x0'] - 0.006; b = r['band']                    # worn band on the eye's side: along the top and round the notch
    V = [0.3, 0.3, 0.7, 0.7]
    for sg in (-1, 1):
        ya, yb = YC + sg * h, YC + sg * nw
        m.face([(xe, ya, zt), (xe, yb, zt), (xe, yb, zt + b), (xe, ya, zt + b)], (-1, 0, 0), UE, V)
        m.face([(xe, yb, zt + b), (xe, yb - sg * b, zt + b), (xe, yb - sg * b, zt + nd + b), (xe, yb, zt + nd + b)], (-1, 0, 0), UE, V)
    m.face([(xe, YC - nw, zt + nd), (xe, YC + nw, zt + nd), (xe, YC + nw, zt + nd + b), (xe, YC - nw, zt + nd + b)], (-1, 0, 0), UE, V)
    # front: foot on the trunnion block, a support, the blade
    f = FRONT
    box(m, f['xb0'], f['xb1'], YC - 0.24, YC + 0.24, f['zfoot'], f['zblk'])
    m.prism([(YC - 0.20, f['zfoot']), (YC - f['mid'], f['zs']), (YC + f['mid'], f['zs']), (YC + 0.20, f['zfoot'])], f['xs0'], f['xs1'], UD)
    m.prism([(YC - f['mid'], f['zs']), (YC - f['top'], ZS), (YC + f['top'], ZS), (YC + f['mid'], f['zs'])], f['x0'], f['x1'], UD, top_u=UE)
    zb_ = ZS + f['band']; wb = f['top'] + (f['mid'] - f['top']) * f['band'] / (f['zs'] - ZS)
    xe = f['x0'] - 0.012
    m.face([(xe, YC - f['top'], ZS), (xe, YC + f['top'], ZS), (xe, YC + wb, zb_), (xe, YC - wb, zb_)], (-1, 0, 0), UE, V)
    return m


def tik():
    """the staged tik = the mod tree's 30calportable.tik with the new skelmodel + the surface row; nothing else"""
    raw = open(MODTIK, 'rb').read().decode('latin-1')
    nl = '\r\n' if '\r\n' in raw else '\n'
    t, n = re.subn(r'skelmodel\s+30cal\.skd', 'skelmodel coop_30cal_sights.skd', raw); assert n == 1
    k = t.index('surface belt shader shellbelt'); e = t.index('\n', k)
    t = t[:e].rstrip('\r') + nl + '\t//HZM coop [ads heavy 2026-10-13] real sights (tools/m1919sights.py): notch slider in the rear leaf, front blade' + nl \
        + '\tsurface coop_sight shader coop_30cal_sight' + t[e:]
    dst = hv.staged(SRC_TIK)
    open(dst, 'wb').write(t.encode('latin-1'))
    return dst


def main():
    staged.off()
    data = vfs.read(SRC_SKD)
    sys.path.insert(0, hv.BOLT)
    _c = os.getcwd(); os.chdir(hv.BOLT)
    import add_bead as AB
    import skdlib
    os.chdir(_c)
    blocks, (numS, numB, ofsB, ofsS, ofsE) = G.surf_blocks(data)
    if len(data) > ofsE:                     # the coop re-export carries stray bytes after the last surface (as the FG 42's, bug-3770)
        print('dropping %d trailing bytes after ofsEnd' % (len(data) - ofsE)); data = data[:ofsE]
    m0 = skdlib.read_skd(data)
    bone =[i for i, b in enumerate(m0.bones) if b.name == 'origin'][0]
    sm = sight_mesh()
    res = AB.add_surface(bytes(data), SRC_TIK, 'coop_sight', sm.v, sm.t, bone)
    dst = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else OUT
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(res)
    m = skdlib.read_skd(res)
    print('coop_sight: %d verts, %d tris on bone %d (%s)' % (len(sm.v), len(sm.t), bone, m.bones[bone].name))
    print('wrote %s  %d bytes (was %d): surfaces %s' % (dst, len(res), len(data), [(s.name, s.numTriangles, s.numVerts) for s in m.surfaces]))
    if '--out' not in sys.argv:
        p = hv.staged('scripts/coop_30cal_sight.shader'); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'w', newline='\n').write(SHADER)
        tex = G.sight_tex().astype(float)
        n = tex.shape[1]
        tex[:, :n // 2] *= E('M19_TD', 0.52); tex[:, n // 2:] *= E('M19_TE', 0.66)
        G.write_tga(hv.staged('textures/coop_wpn/30cal_sight.tga'), tex)
        print('wrote', p, 'and textures/coop_wpn/30cal_sight.tga;', tik())
    F = [round((FRONT['x0'] + FRONT['x1']) / 2, 4), YC, ZS]; R = [round((REAR['x0'] + REAR['x1']) / 2, 4), YC, ZS]
    print('sight row: F %s  R %s  (sight radius %.1f u)' % (F, R, F[0] - R[0]))


if __name__ == '__main__':
    main()
