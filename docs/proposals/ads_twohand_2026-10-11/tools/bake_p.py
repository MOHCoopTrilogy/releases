"""pistol aimed reload bake on a given aim pose (hold_bake auto recipe + fixed_right, as shipped 2026-10-06 bug-3467).

    python bake_p.py <row e.g. colt45_reload> <out.skc> [--charge <relative clip under models/human/animation/ or file>]
                     [--set key=json ...]
Run from the staging dir: a charge clip given as viewmodel/... is looked up as a file under ./models/human/animation/
first (so a new aim pose can be baked before it is in any pak), then in the game's files.
"""
import sys, os, json, argparse, hashlib
import numpy as np
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T)
_c = os.getcwd(); os.chdir(T)
import hold_bake as H
os.chdir(_c)
R = H.R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('row'); ap.add_argument('out'); ap.add_argument('--charge'); ap.add_argument('--set', action='append', default=[])
    a = ap.parse_args()
    kw = dict(fixed_right=True)
    for s in a.set:
        k, v = s.split('=', 1)
        kw[k] = json.loads(v)
    rc = H.auto_recipe(a.row, **kw)
    if a.charge:
        rc['charge'] = a.charge
    H.RECIPES[a.row] = rc
    print('recipe', {k: v for k, v in rc.items()})
    ctl = json.load(open(os.path.join(T, '..', 'assets', 'ctl_stand.json')))
    sk, rep = H.bake(a.row, ctl)
    b = R.skc_io.write(sk)
    open(a.out, 'wb').write(b)
    print('wrote', a.out, len(b), hashlib.md5(b).hexdigest())


if __name__ == '__main__':
    main()
