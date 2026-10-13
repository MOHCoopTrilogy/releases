"""FG 42, both guns: a CHARGING HANDLE on its own bone. The mesh (DaRKaNGeL's re-rig, models/weapons/fg42/fg42.skd)
has only the handle's SLOT painted on the right of the receiver (x -3.26..2.77, z -2.37, face y -0.08; gun frame as
gungeo loads it: x forward, y right, z down, tik-scaled u) - nothing to pull.

Added, surface `coop_handle` (shader coop_fg42_sight = the irons' dark steel, the same on every finish), weighted to
a NEW bone `coop_chg` (child of the bone the receiver hangs on, at identity: every clip without a `coop_chg pos`
channel leaves the handle at rest, forward):
    a stem out of the slot's front end and an upright grip bar on it (a worn outer face so it reads on the dark
    receiver); rest = FORWARD (bolt closed), pulled back TRAVEL u along the slot.

  * assets/models/weapons/fg42/coop_fg42_irons.skd = fg42irons.py's mesh (run again into scratch) + the handle
  * assets/models/weapons/fg42/coop_fg42.skd       = the RETAIL mesh + the handle, nothing else changed (the scoped
    FG 42's staged tiks point to it - coordinator 2026-10-13: both guns work their handle)
  * ../fg42handle.json: the bone channel per u of rearward travel, the knob point, the travel (fg42bake.py reads it)

    python fg42handle.py
"""
import sys, os, json, struct, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hv
import fg42irons as FI
G = FI.G
BONE = 'coop_chg'
SURF = 'coop_handle'
SLOT_Z = -2.37
FACE_Y = -0.08
X0 = 2.05                         # the stem's rear face at rest
TRAVEL = 5.0                      # u back along the slot (its rear end is at x -3.26)
STEM = dict(x0=X0, x1=X0 + 0.45, y0=FACE_Y - 0.04, y1=FACE_Y + 0.60, z0=SLOT_Z - 0.15, z1=SLOT_Z + 0.15)
GRIP = dict(x0=X0 - 0.07, x1=X0 + 0.52, y0=FACE_Y + 0.46, y1=FACE_Y + 0.80, z0=SLOT_Z - 0.68, z1=SLOT_Z + 0.57)
KNOB = [X0 + 0.22, FACE_Y + 0.63, SLOT_Z - 0.05]     # where the fingers hook (gun frame, u)
UD, UE = G.UV_DARK, G.UV_EDGE
# the handle's worn faces: the texture's dark | edge seam (u 0.5 = half way between the two columns). The full edge column
# read as a WHITE bar on the dark receiver in the engine (run hj33 crops)
UW = 0.5


def handle_mesh():
    m = G.Mesh()
    s, g = STEM, GRIP
    FI.box(m, s['x0'], s['x1'], s['y0'], s['y1'], s['z0'], s['z1'])
    FI.box(m, g['x0'], g['x1'], g['y0'], g['y1'], g['z0'], g['z1'])
    # the grip bar's outer face and its rear face (the side the fingers pull on): worn steel, a hair proud
    e = 0.006
    m.face([(g['x0'], g['y1'] + e, g['z0']), (g['x1'], g['y1'] + e, g['z0']), (g['x1'], g['y1'] + e, g['z1']), (g['x0'], g['y1'] + e, g['z1'])],
           (0, 1, 0), UW, [0.3, 0.3, 0.7, 0.7])
    m.face([(g['x0'] - e, g['y0'], g['z0']), (g['x0'] - e, g['y1'], g['z0']), (g['x0'] - e, g['y1'], g['z1']), (g['x0'] - e, g['y0'], g['z1'])],
           (-1, 0, 0), UW, [0.3, 0.3, 0.7, 0.7])
    return m


def with_handle(data, tag):
    _c = os.getcwd(); os.chdir(hv.BOLT)
    sys.path.insert(0, hv.BOLT)
    import add_bead as AB
    import split_bone as SB
    import skdlib
    os.chdir(_c)
    blocks, (numS, numB, ofsB, ofsS, ofsE) = G.surf_blocks(data)
    if len(data) > ofsE:
        data = data[:ofsE]
    m0 = skdlib.read_skd(data)
    base = [s for s in m0.surfaces if s.name.lower() == 'fg42base'][0]
    bs = {w[0] for v in base.verts for w in v[2]}
    assert len(bs) == 1, bs
    bone = bs.pop()
    hm = handle_mesh()
    res = AB.add_surface(data, FI.SRC_TIK, SURF, hm.v, hm.t, bone)
    res, parent, nsel = SB.split(res, BONE, lambda sf, vi, pt: sf.name == SURF)
    assert nsel == len(hm.v), (nsel, len(hm.v))
    m = skdlib.read_skd(res)
    assert [b.name for b in m.bones][-1] == BONE and m.surfaces[-1].name == SURF
    # the bone channel (skd units, the parent's frame) for 1 u of travel toward the butt (gun -x)
    t = AB.G.parse_tik(FI.SRC_TIK)
    skc = AB.SK.read_skc(AB.PR.vfs.read(AB.G._res(t, t['anims']['idle'])))
    mats, _ = AB.G.bone_world(m0, skc, 0)
    Rm = np.asarray(mats[bone])[0:3]
    per_u = (np.array([-1.0, 0.0, 0.0]) / t['scale']) @ Rm.T
    print('%s: surface %s %d verts %d tris on new bone %s (child of %s, bone %d); %d -> %d bytes; channel per u back %s' % (
        tag, SURF, len(hm.v), len(hm.t), BONE, parent, bone, len(data), len(res), np.round(per_u, 4)))
    return res, per_u


def main():
    FI.staged.off()
    tmp = os.path.join(hv.SCR, 'fg42_irons_nohandle.skd')
    subprocess.check_call([sys.executable, os.path.join(HERE, 'fg42irons.py'), '--out', tmp], stdout=subprocess.DEVNULL)
    out = {}
    for tag, src, dst in (('irons', open(tmp, 'rb').read(), 'models/weapons/fg42/coop_fg42_irons.skd'),
                          ('scoped', G.vfs.read(FI.SRC_SKD), 'models/weapons/fg42/coop_fg42.skd')):
        res, per_u = with_handle(src, tag)
        p = hv.staged(dst)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(res)
        out[tag] = dst
    json.dump(dict(bone=BONE, surface=SURF, chan=BONE + ' pos', per_u=[round(float(v), 6) for v in per_u], knob=KNOB, travel=TRAVEL, files=out),
              open(os.path.join(hv.LANE, 'fg42handle.json'), 'w', newline='\n'), indent=1, sort_keys=True)
    print('wrote', out, 'and fg42handle.json')


if __name__ == '__main__':
    main()
