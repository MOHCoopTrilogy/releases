"""OFFLINE: how near the rifle's own BOLT ASSEMBLY (verts weighted to the bolt bone or a bone under it) comes to the
eye in an aimed bolt clip, and how big it is on the screen - per clip frame. The balloon measure for `boltcap.py`.

    cd rifles/assets; python ../tools/boltnear.py <gun>[,<gun>] [--anim rechamber] [--clip <view clip>] [--all]
prints per gun: nearest bolt vertex depth (u in front of the eye) per frame, the bolt's screen bounding box as % of the
whole screen, and the bolt bone's travel (u, gun frame) against its first frame.
Set IRONSIGHT_EXTRA_PAKS=<overlay> to read a staged tik / gun clip (`--anim rechamber_ads`).
"""
import sys, os, json, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); sys.path.insert(0, HERE)
_c = os.getcwd(); os.chdir(T)
import vmcam as V
import anahip
os.chdir(_c)
R = V.R
gungeo, skdlib, vfs = anahip.gungeo, anahip.skdlib, anahip.vfs
CTL = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
# gun -> (sight gun, aim clip, staged view clip)
GUNS = {
    'kar98': ('kar98', 'viewmodel/kar_stand00.skc', 'viewmodel/rifle/kar98_rechamber_ads.skc'),
    'springfield': ('springfield_unscoped', 'viewmodel/sprng_stand00.skc', 'viewmodel/rifle/springfield_rechamber_ads.skc'),
    'mosin': ('mosin_nagant_rifle', 'viewmodel/kar_stand00.skc', 'viewmodel/mosin_nagant/mosin_rechamber_ads.skc'),
    'enfield': ('lee_enfield', 'viewmodel/kar_stand00.skc', 'viewmodel/enfield/enfield_rechamber_ads.skc'),
}


def bolt_verts(tik, bone=None):
    """per surface: indices of the verts carried (> 0.5) by the bolt bone or a bone under it"""
    t = gungeo.parse_tik(tik)
    skd = skdlib.read_skd(vfs.read(gungeo._res(t, t['skel'][0])))
    bone = bone or V.BOLT.get(os.path.basename(tik), 'chamber')
    names = [b.name for b in skd.bones]
    par = {b.name: b.parent for b in skd.bones}
    under = set()
    for n in names:
        p = n
        while p is not None and p in par:
            if p == bone:
                under.add(n); break
            p = par[p]
    idx = {names.index(n) for n in under}
    out = {}
    for s in skd.surfaces:
        sel = [vi for vi, (n, tc, wl, ml) in enumerate(s.verts) if sum(bw for bi, bw, off in wl if bi in idx) > 0.5]
        if sel:
            out[s.name] = np.array(sel)
    return out, sorted(under)


def measure(name, anim='rechamber', clip=None, root='.', quiet=False, offhand=None):
    gun, aimp, vclip = GUNS[name]
    sight = V.SIGHTS[gun]
    tik = sight['tik']
    aim = R.load(R.ANIM + aimp)
    corr = V.rig_target(V.evaluate_ctl(R.pose_dict(aim, aim.numFrames - 1), CTL), sight)
    p = clip or os.path.join(root, 'models', 'human', 'animation', vclip.replace('/', os.sep))
    c = R.load(p)
    bv, under = bolt_verts(tik)
    fov = V.weapon_fov(); W, H = 1280, 720
    rows = []
    for f in range(c.numFrames):
        t = f * c.frameTime
        surfs, E, Wb = V.scene2(R.pose_dict(c, f), gun, tik, anim, t, CTL, corr, (offhand[0] * c.frameTime, offhand[1] * c.frameTime) if offhand else None)
        pts = np.vstack([s['P'][bv[s['name']]] for s in surfs if s.get('gun') and s['name'] in bv])
        q = pts - E
        dep = q[:, 0]
        near = float(dep.min())
        vis = q[dep > 0.3]
        x, y, _ = V.project(vis + E, E, fov, W, H)[0:3] if len(vis) else (np.array([0.0]), np.array([0.0]), None)
        x = np.clip(x, 0, W); y = np.clip(y, 0, H)
        bb = 100.0 * float((x.max() - x.min()) * (y.max() - y.min())) / (W * H)
        rows.append(dict(f=f, near=round(near, 2), bbox=round(bb, 1), ymax=round(float(y.max()), 0), xmin=round(float(x.min())), xmax=round(float(x.max()))))
    if not quiet:
        print('%s  anim %s  bolt bones %s  (%d verts)' % (name, anim, under, sum(len(v) for v in bv.values())))
        print('  f: nearest u / screen bbox %')
        print('  ' + '  '.join('%d:%.1f/%.0f' % (r['f'], r['near'], r['bbox']) for r in rows))
    mn = min(rows, key=lambda r: r['near']); mb = max(rows, key=lambda r: r['bbox'])
    print('%s [%s]: nearest bolt vertex %.2f u in front of the eye (f%d; settled %.2f u), screen bbox max %.1f %% (f%d; settled %.1f %%)' % (
        name, anim, mn['near'], mn['f'], rows[0]['near'], mb['bbox'], mb['f'], rows[0]['bbox']))
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('guns'); ap.add_argument('--anim', default='rechamber'); ap.add_argument('--clip'); ap.add_argument('--quiet', action='store_true')
    ap.add_argument('--offhand', help='lo,hi view-clip frames the gun rides the off-hand tag (a reload)')
    a = ap.parse_args()
    for g in a.guns.split(','):
        measure(g, a.anim, a.clip, quiet=a.quiet, offhand=[float(x) for x in a.offhand.split(',')] if a.offhand else None)
