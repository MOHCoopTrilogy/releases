"""SMG lane: put settled-aim results of guns the shared scanner cannot name (run_smg's own gun keys - the variants)
into ../coverage_status.json, in the shared schema. Source: `aimpair.py numbers <sess> --json f.json`.

    python status_merge.py <sess> <numbers.json>
"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__))
ST = os.path.join(HERE, '..', 'coverage_status.json')
src = open(os.path.join(HERE, 'takeover.py')).read() + open(r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools\run_adsbolt.py").read()
keymap = {k: v.lower() for k, v in re.findall(r"(\w+)='(models/weapons/[^']+)'", src)}
keymap.update({k: v.lower() for k, v in re.findall(r'"(\w+)": "(models/weapons/[^"]+)"', src)})
sess, f = sys.argv[1:3]
st = json.load(open(ST)) if os.path.isfile(ST) else {}
n = 0
for gun, d in json.load(open(f)).items():
    tik = keymap[gun]
    for stance, v in d.items():
        st.setdefault(tik, {}).setdefault('aim', {})[stance] = dict(run=sess, ok=bool(v['pose'] is not None and v['pose'] > 0.9 and v['dev'] <= 1.5),
                                                                    dev=0.0, edge=0.0, end=0.0, pmin=v['pose'], sight_abs=v['dev'], box=v['box'])
        n += 1
json.dump(st, open(ST, 'w'), indent=1, sort_keys=True)
print('merged', n, 'stance results ->', ST, len(st), 'weapons')
