"""Offline search: how much taller do a gun's sights have to be for the SETTLED AIM to pass with aim sway on?
For each raise: sightraise.py on the gun's skd (pak's own, or --skd a staged one) -> a one-file pk3 -> a trial sight
override (F / R z minus the raise, optional relief) -> swayoff.py (worst pair of sway states, bar about 2 %).
Nothing is staged: the trial files live in --tmp. The chosen raise is then staged by hand (sightraise.py into
../assets, the hunk into ../sights_override.json, patch_sights_row.py for the header row).

    cd smg/assets; python ../tools/sighttry.py <gun key> <skd game path> --box surf:x0,x1,zmax [--box ...]
                   --raise 0,0.3,0.45 [--relief 12.3] [--bias 0] [--base overlay.pk3] [--skd staged.skd] --tmp <dir> [--sheet]
"""
import sys, os, json, argparse, subprocess, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
SJ = r'C:\mohaa-coop-dev\docs\proposals\ironsights_2026-09-28\sights.json'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('gun'); ap.add_argument('skd'); ap.add_argument('--box', action='append', default=[])
    ap.add_argument('--raise', dest='ups', default='0,0.3,0.45'); ap.add_argument('--relief', type=float, default=None)
    ap.add_argument('--bias', default='0'); ap.add_argument('--base'); ap.add_argument('--skdfile'); ap.add_argument('--tmp', required=True)
    ap.add_argument('--sheet', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.tmp, exist_ok=True)
    sj = json.load(open(SJ))[a.gun]
    ovp = os.path.join(HERE, '..', 'sights_override.json')
    ov0 = json.load(open(ovp)) if os.path.isfile(ovp) else {}
    cur = dict(sj); cur.update(ov0.get(a.gun, {}))
    for up in [float(x) for x in a.ups.split(',')]:
        env = dict(os.environ)
        paks = [a.base] if a.base else []
        if up > 0:
            skd = os.path.join(a.tmp, 'try_%s_%.2f.skd' % (a.gun, up))
            cmd = [sys.executable, os.path.join(HERE, 'sightraise.py'), sj['tik'], skd, str(up)] + sum([['--box', b] for b in a.box], [])
            if a.skdfile:
                cmd += ['--skd', a.skdfile]
            e2 = dict(os.environ)
            if a.base:
                e2['IRONSIGHT_EXTRA_PAKS'] = a.base
            else:
                e2.pop('IRONSIGHT_EXTRA_PAKS', None)
            r = subprocess.run(cmd, env=e2, capture_output=True, text=True)
            assert r.returncode == 0, r.stdout + r.stderr
            print('   '.join(l.strip() for l in r.stdout.splitlines() if 'raised' in l))
            pk = os.path.join(a.tmp, 'try_%s_%.2f.pk3' % (a.gun, up))
            with zipfile.ZipFile(pk, 'w') as z:
                z.write(skd, a.skd)
            paks.append(pk)
        ov = dict(ov0)
        ent = dict(ov0.get(a.gun, {}))
        ent['F'] = [cur['F'][0], cur['F'][1], round(cur['F'][2] - up, 4)]
        ent['R'] = [cur['R'][0], cur['R'][1], round(cur['R'][2] - up, 4)]
        if cur.get('frame_used') == 'root':          # the rig solve reads F_root / R_root for such a gun
            ent['F_root'] = [cur['F_root'][0], cur['F_root'][1], round(cur['F_root'][2] - up, 4)]
            ent['R_root'] = [cur['R_root'][0], cur['R_root'][1], round(cur['R_root'][2] - up, 4)]
        if a.relief is not None:
            ent['relief'] = a.relief
        ov[a.gun] = ent
        op = os.path.join(a.tmp, 'try_override_%s_%.2f.json' % (a.gun, up))
        json.dump(ov, open(op, 'w'), indent=1)
        env['SMG_SIGHT_OVERRIDE_FILE'] = op
        if paks:
            env['IRONSIGHT_EXTRA_PAKS'] = ';'.join(paks)
        else:
            env.pop('IRONSIGHT_EXTRA_PAKS', None)
        cmd = [sys.executable, os.path.join(HERE, 'swayoff.py'), a.gun, a.bias]
        if a.sheet:
            cmd += ['--sheet', os.path.join(a.tmp, 'try_%s_%.2f.jpg' % (a.gun, up))]
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        for l in r.stdout.splitlines():
            if 'relief' in l or l.endswith('.jpg'):
                print('raise %.2f u%s: %s' % (up, '' if a.relief is None else ' relief %.2f' % a.relief, l.strip()))


if __name__ == '__main__':
    main()
