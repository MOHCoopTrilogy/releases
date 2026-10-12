"""SMG lane: put reloadbox.py results (reload_<run>.json: one entry per stance / case) into ../coverage_status.json
(shared schema: reload[stance] = run, ok, dev, edge, end, pmin) and ../centrebox.json (the shape of ..\\tools\\centrebox.json).

    python status_reload.py <tik> <gun key> <reload_run.json>
A stance passes on: pose >= 0.9 throughout, box beyond the aim <= 2 %, back on the aim <= 0.1 deg after the row ends.
Where a stance has both cases the EMPTY one (magazine + cock) is recorded; the rounds-left case goes to centrebox.json.
"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
tik, key, src = sys.argv[1].lower(), sys.argv[2], sys.argv[3]
d = json.load(open(src))
stp = os.path.join(HERE, '..', 'coverage_status.json')
st = json.load(open(stp)) if os.path.isfile(stp) else {}
cbp = os.path.join(HERE, '..', 'centrebox.json')
cb = json.load(open(cbp)) if os.path.isfile(cbp) else {}
for name, r in sorted(d.items()):
    stance, case = name.rsplit('_', 1)
    ok = r['pose_min'] >= 0.9 and r['extra_max'] <= 2.0 and r['back'] <= 0.1
    e = st.setdefault(tik, {}).setdefault('reload', {})
    if case == 'empty' or stance not in e:
        e[stance] = dict(run=r['run'], ok=bool(ok), dev=r['dev_max'], edge=r['dev_end'], end=r['back'], pmin=r['pose_min'],
                         box=r['extra_max'], case=case)
    if stance == 'stand':
        cb[key + ('_empty' if case == 'empty' else '')] = dict(xmax=r['extra_max'], xfr=0.0 if r['extra_frames_over'] == 0 else round(100.0 * r['extra_frames_over'] / r['frames'], 1),
                                                              run=r['run'], base=r['base'], max=r['extra_max'], over=0.0, dev=r['dev_max'], end=r['back'], frames=r['frames'])
    print('%-18s %s box %.1f %% dev %.2f back %.3f pose %.2f' % (name, 'ok ' if ok else 'NOT', r['extra_max'], r['dev_max'], r['back'], r['pose_min']))
json.dump(st, open(stp, 'w'), indent=1, sort_keys=True)
json.dump(cb, open(cbp, 'w'), indent=1, sort_keys=True)
