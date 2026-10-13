"""Give a thin sight LEAF a believable side profile (staged skd; the eye's picture from behind does not change).

Why (silenced MP40, 2026-10-13, coordinator's decision 1): after sightraise.py the pack mesh's rear leaf is a plate
0.1 u thick and 0.96 u tall - from the side (third person, world model) a spike. The retail MP40's leaf is 0.13-0.2 u
thick and 0.5 u tall on a 1.85 u base block. This tool spreads the leaf's vertices ALONG THE BARREL (gun x) about the
leaf's centre plane by a half-thickness that tapers from `base` at the leaf's foot to `top` at its tip: a wedge-shaped
notch block. Only x changes, so the notch, the height and the width the aiming eye sees are untouched.

Vertices are picked in GUN space (gungeo: x muzzle, y right, z DOWN, u). Run with IRONSIGHT_EXTRA_PAKS = an overlay
that holds the SAME skd as --skd (the gun-space fit is asserted).

    python sightshape.py <tik> <out.skd> --skd in.skd --surf metal3 --box x0,x1,y0,y1,ztip,zfoot --half base,top
        every vertex of the surface inside the box; a vertex on the muzzle side of the box's mid x goes to
        mid + h(z), one on the eye side to mid - h(z); h runs linearly from `base` at zfoot to `top` at ztip
    --scale base,top instead of --half: x is SCALED about the mid plane by a factor running from base to top
"""
import sys, os, struct, argparse
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V  # noqa: F401
import add_part as AP
os.chdir(_c)
G, SK, PR = AP.G, AP.SK, AP.PR


def displace(data, tik, sname, newpos, log=print):
    """newpos(P) -> (selected bool array, new gun-space positions for all vertices); returns the patched skd bytes"""
    t = G.parse_tik(tik)
    m = SK.read_skd(data)
    skc = SK.read_skc(PR.vfs.read(G._res(t, t['anims']['idle']))) if 'idle' in t['anims'] else None
    mats, _ = G.bone_world(m, skc, 0)
    g = G.load_gun(tik, anim='idle', frame=0)
    out = bytearray(data)
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
    A, res, _, _ = np.linalg.lstsq(np.hstack([Wd, np.ones((nvert, 1))]), gs['P'], rcond=None)
    err = float(np.abs(np.hstack([Wd, np.ones((nvert, 1))]) @ A - gs['P']).max())
    assert err < 0.02, 'affine fit off by %.3f u - is IRONSIGHT_EXTRA_PAKS the overlay with this very skd?' % err
    Linv = np.linalg.inv(A[:3])
    P = gs['P']
    sel, P2 = newpos(P)
    for i in np.where(sel)[0]:
        dskd = (P2[i] - P[i]) @ Linv
        for (q, bi, wt, o) in recs[i]:
            Mb = np.asarray(mats[bi])[0:3]
            struct.pack_into('<3f', out, q + 8, *(o + dskd @ Mb.T))
    log('   %s: %d of %d vertices moved, largest step %.3f u (fit %.4f u)' % (sname, int(sel.sum()), nvert, float(np.abs(P2 - P)[sel].max()) if sel.any() else 0, err))
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tik'); ap.add_argument('out'); ap.add_argument('--skd', required=True)
    ap.add_argument('--surf', required=True); ap.add_argument('--box', required=True); ap.add_argument('--half'); ap.add_argument('--scale')
    a = ap.parse_args()
    x0, x1, y0, y1, ztip, zfoot = [float(v) for v in a.box.split(',')]
    hb, ht = [float(v) for v in (a.half or a.scale).split(',')]
    mid = (x0 + x1) / 2.0

    def newpos(P):
        sel = (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] >= y0) & (P[:, 1] <= y1) & (P[:, 2] >= ztip - 0.02) & (P[:, 2] <= zfoot + 0.02)
        f = np.clip((zfoot - P[:, 2]) / (zfoot - ztip), 0, 1)          # 0 at the foot, 1 at the tip
        h = hb + (ht - hb) * f
        P2 = P.copy()
        if a.scale:                                    # a leaf with several layers along x: scaled about its mid plane
            P2[sel, 0] = mid + (P[sel, 0] - mid) * h[sel]
        else:
            P2[sel, 0] = np.where(P[sel, 0] >= mid, mid + h[sel], mid - h[sel])
        return sel, P2
    data = open(a.skd, 'rb').read()
    out = displace(data, a.tik, a.surf, newpos)
    open(a.out, 'wb').write(out)
    print(a.out, len(out), 'bytes (same size: %s)' % (len(out) == len(data)))


if __name__ == '__main__':
    main()
