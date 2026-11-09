"""measure TRIAL clips (files on disk) with the hand / near-plane surveys, as if they shipped under a row:
    python try_measure.py <row> <trial.skc> [<row> <trial.skc> ...]
prints hand_survey's score / covers / arm_min and clip_survey's cut counts for each pair."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clip_survey as CS   # noqa: E402
import hand_survey as HS   # noqa: E402
V, H, IS, R = CS.V, CS.H, CS.IS, CS.R

rows = H.fps_rows()
ctl = json.load(open(os.path.join(CS.BOLT, '..', 'assets', 'ctl_stand.json')))
_load = R.load
MAP = {}


def load(path):
    return _load(MAP.get(path, path))


R.load = load
a = sys.argv[1:]
for row, f in zip(a[0::2], a[1::2]):
    MAP[R.ANIM + rows[row]] = f
    pre = row.split('_')[0]
    key = IS.PREFIX.get(pre)
    if pre in ('cv', 'coopr'):
        rest = row.split('_', 1)[1]
        hits = [k for k in V.SIGHTS if rest == k or rest.startswith(k + '_')]
        key = max(hits, key=len)
        pre = '%s_%s' % (pre, key)
    corr = CS.aim_corr(pre, rows, key, ctl) if CS.is_ads(row) else None
    b = HS.measure(row, rows[row], key, ctl, corr)
    c, n, ads = CS.measure(row, rows[row], key, ctl, corr)
    print('%-44s %s  hand score %.3f near %.2f centre %.2f arm_min %.1f f%d | cut16 %d cut21 %d' % (
        row, os.path.basename(os.path.dirname(f)), b['score'], b['near'], b['centre'], b['amin'], b['f'], c['cut16'], c['cut21']))
