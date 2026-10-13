"""One gun of one run_smg session: reloadbox.py on every aimed `sdemo` capture it has (rounds-left + EMPTY per stance),
the results into reload_<session>.json (merged per gun) and, with --status <tik> <centrebox key>, into
../coverage_status.json / ../centrebox.json (status_reload.py's pass rule).

    python measure_run.py <session> <harness gun key> [--status models/weapons/<x>.tik <key>] [--dump]
"""
import sys, os, re, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reloadbox as RBX

sess, gun = sys.argv[1], sys.argv[2]
tags = []
for ln in open(RBX.RUNS + sess + '/qconsole.log', encoding='latin-1', errors='replace'):
    m = re.search(r'ABSCEN end (ab__%s__%s__(\w*?)ads([LE])__demo__after)' % (re.escape(sess), re.escape(gun)), ln)
    if m and 'echo' not in ln:
        tags.append((m.group(2) or 'stand', m.group(3), m.group(1)))
out = {}
for stance, case, tag in tags:
    try:
        r = RBX.measure(sess, '%s__%sads%s__' % (gun, '' if stance == 'stand' else stance, case), 8 if case == 'E' else 0, '--dump' in sys.argv,
                        dry=(case == 'E' and '--nodry' not in sys.argv))
        if r.get('dry_ref'):
            print('      (dry-gun reference: its own parts add %.1f %% of the box to the aim mask)' % r['dry_ref'])
    except ValueError as e:                  # no reload in the capture (the gun did not run dry / did not fire): say so, go on
        print('%s %s %s: NO RELOAD FOUND in this capture (%s) - run it again' % (gun, stance, case, e))
        continue
    if r['frames'] < 100:
        print('%s %s %s: only %d reload frames found - not recorded, run it again' % (gun, stance, case, r['frames']))
        continue
    out['%s_%s' % (stance, 'empty' if case == 'E' else 'loaded')] = r
p = os.path.join(HERE, 'reload_%s_%s.json' % (sess, gun))
json.dump(out, open(p, 'w'), indent=1, sort_keys=True)
if '--status' in sys.argv:
    k = sys.argv.index('--status')
    subprocess.check_call([sys.executable, os.path.join(HERE, 'status_reload.py'), sys.argv[k + 1], sys.argv[k + 2], p])
