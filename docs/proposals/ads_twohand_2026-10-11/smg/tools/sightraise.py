"""Raise the SIGHTS of a gun mesh over its receiver (staged skd, nothing else on the mesh changes).

Why (silenced MP40, 2026-10-13): on `mp40silenced.skd` the rear leaf stands 0.3 u over the receiver's rear (the retail
MP40: 0.7 u) and the receiver is 3.2 u wide (retail 2.1): from the aiming eye the receiver's top is INSIDE the centre
box (3.5-4.9 deg under the sight line, box edge 7.2 deg) at 5-7 u from the eye, where the game's aim sway + breath
(a translation of the whole rig, +-0.175 u up/down, +-0.14 u sideways) moves it 15-20 px. Taller sights put the same
receiver further under the sight line: the engine's rig solve keeps the sights on the view axis, so the gun sits lower.

Vertices are picked in GUN space (gungeo: x muzzle, y right, z DOWN, u) by boxes and moved by -dz (up). Offsets are
stored per weight in the bone's frame: the gun-space step is mapped back through the surface's own affine fit.

    python sightraise.py <tik> <out.skd> <raise u> --box surf:x0,x1,zmax [--box ...] [--sights key] [--skd in.skd]
        box: every vertex of `surf` with x0 <= x <= x1 and z <= zmax (z is down: zmax = the LOWEST level that moves)
        --sights key   also print the sights.json hunk (F / R z minus the raise) for that key
"""
import sys, os, struct, json, argparse
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V  # noqa: F401
import add_part as AP
os.chdir(_c)
G, SK, PR = AP.G, AP.SK, AP.PR


def raise_sights(data, tik, up, boxes, log=print):
    t = G.parse_tik(tik)
    m = SK.read_skd(data)
    skc = SK.read_skc(PR.vfs.read(G._res(t, t['anims']['idle']))) if 'idle' in t['anims'] else None
    mats, _ = G.bone_world(m, skc, 0)
    g = G.load_gun(tik, anim='idle', frame=0)
    out = bytearray(data)
    moved = {}
    for sname in sorted(set(b[0] for b in boxes)):
        surf = [s for s in m.surfaces if s.name == sname][0]
        gs = [x for x in g['surfs'] if x['name'] == sname][0]
        off = surf.raw_off
        ntri, nvert, static, oTri, oVerts, oColl, oEnd, oCI = struct.unpack_from('<8i', data, off + 68)
        assert nvert == len(gs['P']), (nvert, len(gs['P']))
        p = off + oVerts
        recs, world = [], []
        for i in range(nvert):
            nw, nm = struct.unpack_from('<2i', data, p + 20)
            assert nm == 0, 'morph targets not handled'
            ws = []
            q = p + 28
            for k in range(nw):
                bi, wt, ox, oy, oz = struct.unpack_from('<if3f', data, q)
                ws.append((q, bi, wt, np.array([ox, oy, oz])))
                q += 20
            world.append(sum(w[2] * (w[3] @ np.asarray(mats[w[1]])[0:3] + np.asarray(mats[w[1]])[3]) for w in ws))
            recs.append(ws)
            p = q
        assert p == off + oColl, (p, off + oColl)
        Wd = np.array(world)
        # gun space = affine(skd space): least squares over the surface's own vertices
        A, res, _, _ = np.linalg.lstsq(np.hstack([Wd, np.ones((nvert, 1))]), gs['P'], rcond=None)
        err = float(np.abs(np.hstack([Wd, np.ones((nvert, 1))]) @ A - gs['P']).max())
        assert err < 0.02, 'affine fit off by %.3f u' % err
        L = A[:3]                                             # gun = skd @ L + A[3]
        dskd = np.array([0.0, 0.0, -up]) @ np.linalg.inv(L)   # the skd-space step that is `up` u upward in gun space
        P = gs['P']
        sel = np.zeros(nvert, bool)
        for b in boxes:
            if b[0] == sname:
                sel |= (P[:, 0] >= b[1]) & (P[:, 0] <= b[2]) & (P[:, 2] <= b[3])
        for i in np.where(sel)[0]:
            for (q, bi, wt, o) in recs[i]:
                Mb = np.asarray(mats[bi])[0:3]
                o2 = o + dskd @ Mb.T
                struct.pack_into('<3f', out, q + 8, *o2)
        moved[sname] = int(sel.sum())
        log('   %s: %d of %d vertices raised %.2f u (fit %.4f u)' % (sname, moved[sname], nvert, up, err))
    return bytes(out), moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tik'); ap.add_argument('out'); ap.add_argument('up', type=float)
    ap.add_argument('--box', action='append', default=[]); ap.add_argument('--sights'); ap.add_argument('--skd')
    a = ap.parse_args()
    boxes = []
    for b in a.box:
        s, r = b.split(':')
        x0, x1, zm = [float(v) for v in r.split(',')]
        boxes.append((s, x0, x1, zm))
    t = G.parse_tik(a.tik)
    data = open(a.skd, 'rb').read() if a.skd else PR.vfs.read(G._res(t, t['skel'][0]))
    out, moved = raise_sights(data, a.tik, a.up, boxes)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, 'wb').write(out)
    print(a.out, len(out), 'bytes (same size as the source: %s)' % (len(out) == len(data)))
    if a.sights:
        sj = json.load(open(r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\sights.json'))[a.sights]
        F = list(sj['F']); R = list(sj['R'])
        print('sights.json hunk for %s: F %s -> %s, R %s -> %s' % (a.sights, F, [F[0], F[1], round(F[2] - a.up, 4)], R, [R[0], R[1], round(R[2] - a.up, 4)]))


if __name__ == '__main__':
    main()
