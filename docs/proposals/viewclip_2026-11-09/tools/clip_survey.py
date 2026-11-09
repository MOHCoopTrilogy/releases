"""viewclip step 1 - the OFFLINE near-plane pass over every first-person clip (user 2026-11-09: "some guns clip into the camera and
you end up seeing inside of them or through them").

For every fps_anims row (models/player/base/fps_anims_*.txt: idle / fire / reload / rechamber / pullout / putaway and their
_ads / _charge aim rows), every sampled frame is posed with the engine-calibrated rig of ads_bolt_2026-10-04 (vmcam.scene2: arms
with the drawn bone controllers, the gun's own matching animation on the tag the server uses, the held ADS correction for aim
rows) and measured in the camera frame (x forward, y left, z up):
  arm_min / gun_min   the closest arm (hands, sleeves) / gun vertex to the eye, u
  cut16 / cut21       vertices INSIDE the view frustum (16:9 1920x1080 / 21:9 3440x1440, Hor+ from cg_fov 80 at 4:3) that are
                      nearer than the plane the engine draws that row with - the geometry the camera slices through
  cut_fixed16/21      the same with the weapon near plane (r_weaponznear 1) at the hip too = what is left after the global fix
Near planes (renderergl2 tr_main.c): a HIP row is drawn with the WORLD projection (r_weaponfovx == the world fov, so the weapon
projection is skipped) -> r_znear 4; an AIM row has the weapon projection -> r_weaponznear 1.
Rows whose prefix has no gun mapping (ads_bolt idle_survey.PREFIX) are listed with no numbers.

    python clip_survey.py [row ...]     -> ../assets/clip_survey.tsv (GENERATED), prints the worst rows
"""
import os, sys, json, math, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BOLT = os.path.join(HERE, '..', '..', 'ads_bolt_2026-10-04', 'tools')
sys.path.insert(0, BOLT)
import vmcam as V          # noqa: E402
import hold_bake as H      # noqa: E402
import idle_survey as IS   # noqa: E402
R = V.R

ZNEAR_WORLD, ZNEAR_WEAPON = 4.0, 1.0
TV = math.tan(math.radians(32.2))          # cg_fov 80 at 4:3 -> vertical half-angle tan(40)*0.75 = 0.629 (Hor+ keeps it)
ASPECTS = {'16': 1920 / 1080.0, '21': 3440 / 1440.0}
ADS_KEYS = ('_charge', '_ads', 'adsfire', '_adsb')
SAMPLES = 24


def is_ads(row):
    return any(k in row for k in ADS_KEYS)


def gun_anim(row):
    r = row.lower()
    for k in ('rechamber', 'reload_empty', 'reload', 'fire', 'pullout', 'putaway'):
        if k in r:
            return k
    return 'idle'


def aim_corr(prefix, rows, key, ctl):
    cr = rows.get(prefix + '_charge')
    if not cr:
        return None
    clip = R.load(R.ANIM + cr)
    return V.rig_target(V.evaluate_ctl(R.pose_dict(clip, clip.numFrames - 1), ctl), V.SIGHTS[key])


def measure(row, clip_path, key, ctl, corr):
    tik = V.SIGHTS[key]['tik']
    clip = R.load(R.ANIM + clip_path)
    ads = corr is not None
    zn = ZNEAR_WEAPON if ads else ZNEAR_WORLD
    anim = gun_anim(row)
    res = dict(arm=1e9, gun=1e9, worst_f=-1, worst_d=1e9)
    for a in ASPECTS:
        res['cut' + a] = 0
        res['fix' + a] = 0
    frames = sorted(set(list(range(0, clip.numFrames, max(1, clip.numFrames // SAMPLES))) + [clip.numFrames - 1]))
    for f in frames:
        t = f * clip.frameTime
        try:
            surfs, E, Wb = V.scene2(R.pose_dict(clip, f), key, tik, anim, t, ctl, corr, None, None)
        except Exception:
            surfs, E, Wb = V.scene2(R.pose_dict(clip, f), key, tik, 'idle', t, ctl, corr, None, None)
        for s in surfs:
            c = s['P'] - E
            far = np.abs(c).max(1) > 5000           # surfaces parked far away (hidden props)
            c = c[~far]
            if not len(c):
                continue
            d = np.linalg.norm(c, axis=1)
            k = 'gun' if s.get('gun') else 'arm'
            res[k] = min(res[k], float(d.min()))
            fwd = c[:, 0]
            for a, asp in ASPECTS.items():
                th = TV * asp
                inf = (fwd > 0.01) & (np.abs(c[:, 1]) < fwd * th) & (np.abs(c[:, 2]) < fwd * TV)
                n = int((inf & (fwd < zn)).sum())
                res['cut' + a] += n
                res['fix' + a] += int((inf & (fwd < ZNEAR_WEAPON)).sum())
                if n and fwd[inf & (fwd < zn)].min() < res['worst_d']:
                    res['worst_d'] = float(fwd[inf & (fwd < zn)].min())
                    res['worst_f'] = f
    return res, len(frames), ads


def main():
    rows = H.fps_rows()
    want = sys.argv[1:] or [k for k in rows if '_' in k and not k.endswith('_disabled') and not k.startswith('$')]
    ctl = json.load(open(os.path.join(BOLT, '..', 'assets', 'ctl_stand.json')))
    corrs = {}
    out = []
    t0 = time.time()
    for row in want:
        pre = row.split('_')[0]
        key = IS.PREFIX.get(pre)
        if pre in ('cv', 'coopr'):
            # the coop's own per-gun rows: cv_<sights key>_<action> / coopr_<sights key>_<action> - the longest sights.json key
            rest = row.split('_', 1)[1]
            hits = [k for k in V.SIGHTS if rest == k or rest.startswith(k + '_')]
            key = max(hits, key=len) if hits else None
            pre = '%s_%s' % (pre, key) if key else pre
        if key is None or key not in V.SIGHTS:
            out.append([row, rows.get(row, ''), '-', 'no gun mapping'] + [''] * 9)
            continue
        corr = None
        if is_ads(row):
            if pre not in corrs:
                try:
                    corrs[pre] = aim_corr(pre, rows, key, ctl)
                except Exception:
                    corrs[pre] = None
            corr = corrs[pre]
            if corr is None:
                out.append([row, rows[row], key, 'ADS (no aim pose)'] + [''] * 9)
                continue
        try:
            r, n, ads = measure(row, rows[row], key, ctl, corr)
        except Exception as e:
            out.append([row, rows[row], key, 'ERROR %s' % repr(e)[:60]] + [''] * 9)
            continue
        bad = r['cut16'] or r['cut21']
        out.append([row, rows[row], key, 'ADS' if ads else 'hip', '%.1f' % r['arm'], '%.1f' % r['gun'], str(r['cut16']),
                    str(r['cut21']), str(r['fix16']), str(r['fix21']),
                    '%.2f' % r['worst_d'] if bad else '', str(r['worst_f']) if bad else '', 'CUT' if bad else 'OK'])
        if bad:
            print('%-28s %-4s arm %5.1f gun %5.1f cut16 %5d cut21 %5d -> fixed %d/%d  nearest %.2f u f%d' % (
                row, out[-1][3], r['arm'], r['gun'], r['cut16'], r['cut21'], r['fix16'], r['fix21'], r['worst_d'],
                r['worst_f']), flush=True)
    os.makedirs(os.path.join(HERE, '..', 'assets'), exist_ok=True)
    p = os.path.join(HERE, '..', 'assets', 'clip_survey.tsv')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# GENERATED by tools/clip_survey.py - do not edit. cut = frustum vertices nearer than the plane the row is drawn '
                'with (hip: r_znear %.0f, aim: r_weaponznear %.0f); fixed = with the weapon near plane at the hip too\n'
                % (ZNEAR_WORLD, ZNEAR_WEAPON))
        f.write('row\tclip\tgun\tcamera\tarm_min\tgun_min\tcut16\tcut21\tfixed16\tfixed21\tnearest\tworst_frame\tverdict\n')
        for o in out:
            f.write('\t'.join(o) + '\n')
    nc = sum(1 for o in out if o[-1] == 'CUT')
    print('wrote %s: %d rows, %d CUT, %d unmapped, %.0f s' % (p, len(out), nc, sum(1 for o in out if o[3] == 'no gun mapping'),
                                                        time.time() - t0))


if __name__ == '__main__':
    main()
